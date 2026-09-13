"""Kokoro TTS servisi: kendi sürecinde, HTTP arkasında (Kural 2, §3).

**Neden ayrı bir süreç.** Legacy'de (`mayen-legacy/orchestrator/services/tts.py`) Kokoro
orchestrator'ın içine yükleniyordu; Kural 2 bunu yasaklıyor. Uygulama süreci model
yüklemez — `llama-server` neyse bu da o: model burada yaşar, `mayen` tarafında yalnızca
`adapters/kokoro.py` adında ince bir HTTP istemcisi durur. Bunun bedeli bir süreç ve bir
port; karşılığı, torch'un ve GPU belleğinin uygulamanın ömrüne bağlanmaması.

**Ayrı bir uv projesi.** `torch` + `kokoro` birkaç gigabayt ve `mayen`'in dört kapısının
(`ruff`, `mypy`, `pytest`, `uv sync`) hiçbirinin onlara ihtiyacı yok. Depo kökündeki
`.venv` temiz kalıyor; bu dizinin kendi `pyproject.toml`'u var.

Çalıştırma:

    uv run --project services/kokoro python services/kokoro/main.py

**Akışlı, çünkü ilk ses ölçülen bir hedef (§6).** Legacy bütün sesi üretip tek parça WAV
döndürüyordu; o arayüz ilk-ses bütçesini baştan harcar. Kokoro zaten segment segment
üretiyor ve buradaki uç ürettiğini üretir üretmez gönderiyor.

**ffmpeg istek başına tek ve kalıcı bir süreç.** Parça parça çağırmak `aecho`'yu her
segmentin başında sıfırlar, yani yankı segment sınırlarında duyulur biçimde kesilirdi.
PCM stdin'e akıtılıyor, filtrelenmişi stdout'tan okunuyor; diske hiçbir şey yazılmıyor.

**Çıkış 16 kHz ve bu sayı yapılandırılabilir değil.** Kokoro 24 kHz üretir; yerelin biçimi
tek bir yerde yazılı (`client/audio.py`: 16 kHz, tek kanal, PCM16) ve mikrofon da o hızda.
Dönüştürme zincirin sonunda ffmpeg'e bedelsiz yaptırılıyor. Ayar yapılabilir olsaydı
servisin ürettiği hız ile adaptörün bildirdiği hız sessizce ayrışabilirdi — sonucu
"ses tiz/pes çıkıyor" diye anlaşılan bir arıza. `/health` hızı da bildiriyor ve adaptör
bekleneni doğruluyor.

**Aynı anda tek sentez.** `KPipeline` model durumunu tutuyor ve eşzamanlı ileri geçişler
için güvenli değil. §13'ün TTS kuyruğunda zaten paralellik yok; kilit o sözü burada da
tutuyor.

Ses karakteri (§19.10) legacy'den birebir taşındı: `bf_emma`, hız 0.85, ve metalik yankı +
telsiz bandı + kazanç zinciri. Ortam değişkenleriyle değiştirilebilir; hangi değerlerle
koştuğu açılışta yazılıyor.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

KOKORO_RATE = 24_000
"""Kokoro'nun kendi çıkış hızı. Modelin özelliği, ayar değil."""

OUTPUT_RATE = 16_000
"""Servisin bildirdiği hız. `client/audio.py`'nin `FORMAT`'ı ile aynı sayı olmak zorunda;
gerekçesi modül başlığında."""

DEVICE = os.environ.get("MAYEN_KOKORO_DEVICE", "cpu")
"""**Varsayılan CPU, ve bu bir tercih değil ölçülmüş bir kısıt.** Legacy `cuda` diyordu;
burada denendiğinde `llama-server` kartın 16 GB'ının 15.6'sını tutuyordu ve Kokoro 20 MB
ayıramadan öldü. Model 82M parametre — CPU'da koşması makul. Kart boşaltılırsa (daha küçük
LLM, daha az katman) `cuda` yazılıp ilk-ses süresi yeniden ölçülür."""

VOICE = os.environ.get("MAYEN_KOKORO_VOICE", "bf_emma")
SPEED = float(os.environ.get("MAYEN_KOKORO_SPEED", "0.85"))
EFFECTS = os.environ.get("MAYEN_KOKORO_EFFECTS", "1") != "0"
HOST = os.environ.get("MAYEN_KOKORO_HOST", "127.0.0.1")
PORT = int(os.environ.get("MAYEN_KOKORO_PORT", "8081"))

EFFECT_CHAIN = os.environ.get(
    "MAYEN_KOKORO_EFFECT_CHAIN",
    "aecho=0.8:0.88:40:0.4,"  # metalik yankı: 40 ms gecikme, 0.4 geri besleme
    "highpass=f=400,"  # 400 Hz altını kes — telsiz hissi
    "lowpass=f=3000,"  # 3 kHz üstünü kes — telsiz bandı
    "volume=1.5",  # filtrelerin yediği kazancı geri ver
)

READ_SIZE = 4096
"""ffmpeg çıkışından bir okumada alınan bayt. 16 kHz PCM16'da ~128 ms: istemciye anlamlı
bir parça, ilk sesi geciktirmeyecek kadar küçük."""

_lock = asyncio.Lock()
_pipeline: Any = None


def _load() -> Any:  # noqa: ANN401  # KPipeline tip bilgisi yollamıyor
    """Kokoro'yu yükler. `lang_code` ses kimliğinin ilk harfinden: `b` İngiliz, `a` Amerikan."""
    from kokoro import KPipeline

    return KPipeline(
        lang_code="b" if VOICE.startswith("b") else "a",
        repo_id="hexgrad/Kokoro-82M",
        device=DEVICE,
    )


def _segments(text: str) -> Iterator[bytes]:
    """Kokoro'nun ürettiği her segmenti int16 PCM baytı olarak verir."""
    for _, _, audio in _pipeline(text, voice=VOICE, speed=SPEED):
        samples = audio.numpy()
        yield (samples * 32767).clip(-32768, 32767).astype(np.int16).tobytes()


def _ffmpeg_command() -> list[str]:
    """Ham PCM girer, filtrelenmiş ve 16 kHz'e indirilmiş ham PCM çıkar.

    Efektler kapalıyken de ffmpeg'den geçiliyor: dönüştürme yine gerekiyor ve iki ayrı
    kod yolu, yalnızca birinin denendiği bir servis demek olurdu.
    """
    filters = ["-af", EFFECT_CHAIN] if EFFECTS else []
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-ar",
        str(KOKORO_RATE),
        "-ac",
        "1",
        "-i",
        "pipe:0",
        *filters,
        "-f",
        "s16le",
        "-ar",
        str(OUTPUT_RATE),
        "-ac",
        "1",
        "pipe:1",
    ]


async def _stream(text: str) -> AsyncIterator[bytes]:
    """Sentezi başlatır ve filtrelenmiş PCM'i parça parça verir.

    Üretim bloklayan ve GPU'ya giden bir iş; her segment ayrı bir iş parçacığında alınıyor
    (`next` ile, üreteci bir kere kurup adım adım tüketerek). Çağıran akışı yarıda
    bırakırsa (söz kesme, Kural 12) `finally` hem besleyici görevi hem ffmpeg'i kapatır.
    """
    async with _lock:
        process = await asyncio.create_subprocess_exec(
            *_ffmpeg_command(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdin is not None and process.stdout is not None

        async def feed() -> None:
            segments = _segments(text)
            while True:
                chunk = await asyncio.to_thread(next, segments, None)
                if chunk is None:
                    break
                process.stdin.write(chunk)
                await process.stdin.drain()
            process.stdin.close()

        feeder = asyncio.create_task(feed())
        try:
            while True:
                data = await process.stdout.read(READ_SIZE)
                if not data:
                    break
                yield data
            await feeder
            if await process.wait() != 0:
                stderr = await process.stderr.read() if process.stderr else b""
                raise RuntimeError(f"ffmpeg başarısız: {stderr.decode(errors='replace')[:300]}")
        finally:
            feeder.cancel()
            if process.returncode is None:
                process.kill()
            await process.wait()


class SynthesizeRequest(BaseModel):
    text: str


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Model açılışta yükleniyor: ilk isteğin faturasına yazılsaydı ilk turun ilk sesi
    modelin yüklenmesini de beklerdi."""
    global _pipeline
    _pipeline = await asyncio.to_thread(_load)
    print(
        f"kokoro yüklendi: ses={VOICE} hız={SPEED} cihaz={DEVICE} efekt={EFFECTS} "
        f"çıkış={OUTPUT_RATE} Hz mono pcm16",
        flush=True,
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, object]:
    """§14: yoklayıcının gördüğü yüz. Biçimi de bildiriyor — adaptör beklediğiyle
    karşılaştırıp ayrışmayı sese değil kayda düşürsün diye."""
    return {
        "ok": _pipeline is not None,
        "voice": VOICE,
        "codec": "pcm16",
        "sample_rate": OUTPUT_RATE,
        "channels": 1,
        "effects": EFFECTS,
        "device": DEVICE,
    }


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest) -> StreamingResponse:
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="model henüz yüklenmedi")
    text = request.text.replace("\n", " ").strip()
    if not text:
        raise HTTPException(status_code=400, detail="metin boş")
    return StreamingResponse(_stream(text), media_type="application/octet-stream")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
