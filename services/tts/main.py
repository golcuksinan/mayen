"""Mayen'in TTS servisi: Kokoro ve Piper, kendi sürecinde, HTTP arkasında.

Çekirdek model yüklemez; sesler burada yaşar, çekirdekte yalnızca ince bir istemci durur.
Sözleşme çekirdeğin `ports/speech.py` modülündedir; bu servis onu import etmez, burada aynen
kurar. Her yanıt `schema_version` taşır.

**Akışlı.** İlk ses üretilir üretilmez gönderilir; bütün cümleyi bekleyen bir uç ilk sesin
süresini baştan harcar.

**Dil işareti (sesin dilinde olmayan parça).** İstek parçalar hâlinde gelir; dili verilmeyen
parça sesin kendi diliyle, dili verilen parça o dilin okunuşuyla (espeak) ses birimine
çevrilir ve ikisi aynı sese ses birimi olarak verilir. Ses biriminin seste karşılığı yoksa en
yakınına çevrilir; atılan bir birim sesi sessizce bozar.

**Çıkış hızı sabittir** (`sample_rate`) ve `/health` onu bildirir; istemci bekleneni doğrular.
Ayarlanabilir bir hız ile istemcinin bildiği hız sessizce ayrışabilirdi: sonucu "ses tiz/pes"
diye duyulur.

**Aynı anda tek sentez.** Model durumları eşzamanlı ileri geçişler için güvenli sayılmaz;
çerçeve cümleleri zaten sırayla seslendirir.

Çalıştırma:

    uv run --project services/tts python services/tts/main.py <config.yaml>
"""

import asyncio
import sys
import unicodedata
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Literal

import numpy as np
import soxr
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from scipy.signal import butter, sosfilt, sosfilt_zi

SCHEMA_VERSION = 1


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Echo(_Strict):
    input: float
    output: float
    delay_ms: float
    decay: float


class Pre(_Strict):
    """Telsizden önce sesin kendisine: bant süzgeci ve kalın uçta raf yükseltmesi."""

    highpass_hz: float
    lowpass_hz: float
    low_shelf_hz: float
    low_shelf_db: float


class Effect(_Strict):
    """ffmpeg'in `aecho` + `highpass` + `lowpass` + `volume` zincirinin karşılığı.

    `pre` verilirse telsiz onun çıkışına uygulanır; `dry`, telsizin yanına karışan bu sesin
    payıdır. İkisi yoksa ses bütünüyle telsizden geçer."""

    pre: Pre | None = None
    dry: float = 0.0
    echo: Echo
    highpass_hz: float
    lowpass_hz: float
    gain: float


class Voice(_Strict):
    engine: Literal["kokoro", "piper"]
    voice: str | None = None  # Kokoro: ses dosyasındaki ad
    language: str | None = None  # Kokoro: sesin kendi dili (ör. en-gb)
    model: Path | None = None  # Piper: .onnx (yanında .onnx.json)
    speed: float = 1.0
    effect: str | None = None


class KokoroFiles(_Strict):
    model: Path
    voices: Path


class Settings(_Strict):
    host: str = "127.0.0.1"
    port: int = 8771
    sample_rate: int = 24_000
    kokoro: KokoroFiles | None = None
    voices: dict[str, Voice]
    effects: dict[str, Effect] = {}


class PartIn(BaseModel):
    language: str | None
    text: str


class SpeakIn(BaseModel):
    schema_version: int
    voice: str
    parts: list[PartIn]


# Kokoro'nun ses birimi listesinde olmayan espeak birimleri en yakınına çevrilir.
# ɫ (kalın l) sessizce düşüyordu; ɟ (ince g) "c" gibi okunuyordu.
KOKORO_NEAREST = {"ɫ": "l", "ɟ": "ɡ"}


class Radio:
    """Bir cevabın efekti; yankı kuyruğu ve süzgeç durumu parçalar arasında taşınır."""

    def __init__(self, effect: Effect, rate: int) -> None:
        self._e = effect
        self._delay = np.zeros(int(rate * effect.echo.delay_ms / 1000), np.float32)
        self._sos = np.vstack(
            [
                butter(2, effect.highpass_hz, "highpass", fs=rate, output="sos"),
                butter(2, effect.lowpass_hz, "lowpass", fs=rate, output="sos"),
            ]
        )
        self._zi = sosfilt_zi(self._sos) * 0.0
        pre = effect.pre
        if pre is not None:
            self._pre_sos = np.vstack(
                [
                    butter(2, pre.highpass_hz, "highpass", fs=rate, output="sos"),
                    butter(2, pre.lowpass_hz, "lowpass", fs=rate, output="sos"),
                ]
            )
            self._pre_zi = sosfilt_zi(self._pre_sos) * 0.0
            self._shelf_sos = butter(2, pre.low_shelf_hz, "lowpass", fs=rate, output="sos")
            self._shelf_zi = sosfilt_zi(self._shelf_sos) * 0.0
            self._shelf_gain = 10 ** (pre.low_shelf_db / 20) - 1

    def __call__(self, x: np.ndarray) -> np.ndarray:
        if self._e.pre is not None:
            x, self._pre_zi = sosfilt(self._pre_sos, x, zi=self._pre_zi)
            low, self._shelf_zi = sosfilt(self._shelf_sos, x, zi=self._shelf_zi)
            x = x + low * self._shelf_gain
        echo = self._e.echo
        # Gecikmiş giriş, önceki parçanın kuyruğu ile bu parçanın başından oluşur.
        longer = np.concatenate([self._delay, x])
        delayed = longer[: len(x)]
        self._delay = longer[len(x) :]
        y = (x * echo.input + delayed * echo.decay) * echo.output
        out, self._zi = sosfilt(self._sos, y, zi=self._zi)
        return (out + x * self._e.dry) * self._e.gain


def _pcm(x: np.ndarray) -> bytes:
    return (np.clip(x, -1.0, 1.0) * 32767).astype(np.int16).tobytes()


type Engine = Callable[[Voice, list[PartIn]], AsyncIterator[np.ndarray]]


def kokoro_engine(files: KokoroFiles, rate: int) -> tuple[Engine, set[str]]:
    import phonemizer
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(str(files.model.expanduser()), str(files.voices.expanduser()))

    def phonemes(voice: Voice, part: PartIn) -> str:
        if part.language is None:
            return kokoro.tokenizer.phonemize(part.text, voice.language or "en-us")
        raw = phonemizer.phonemize(
            part.text,
            language=part.language,
            backend="espeak",
            preserve_punctuation=True,
            with_stress=True,
        ).strip()
        return "".join(KOKORO_NEAREST.get(c, c) for c in raw)

    async def speak(voice: Voice, parts: list[PartIn]) -> AsyncIterator[np.ndarray]:
        text = " ".join(phonemes(voice, p) for p in parts)
        stream = kokoro.create_stream(
            text,
            voice=voice.voice or "",
            lang=voice.language or "en-us",
            speed=voice.speed,
            is_phonemes=True,
        )
        async for samples, sample_rate in stream:
            yield samples if sample_rate == rate else soxr.resample(samples, sample_rate, rate)

    return speak, set(kokoro.get_voices())


def piper_engine(voices: dict[str, Voice], rate: int) -> Engine:
    from piper import PiperVoice, SynthesisConfig
    from piper.phonemize_espeak import EspeakPhonemizer

    loaded = {
        str(v.model): PiperVoice.load(str(v.model.expanduser()))
        for v in voices.values()
        if v.engine == "piper" and v.model is not None
    }
    espeak = EspeakPhonemizer()

    def ids(model: Any, voice: Voice, parts: list[PartIn]) -> list[int]:  # noqa: ANN401
        units: list[str] = []
        for part in parts:
            sentences = (
                model.phonemize(part.text)
                if part.language is None
                else espeak.phonemize(part.language, part.text)
            )
            for sentence in sentences:
                units.extend([*sentence, " "])
        id_map = model.config.phoneme_id_map
        # Karşılığı olmayan birim, işaretsiz temel harfine çevrilir.
        near = [u if u in id_map else unicodedata.normalize("NFD", u)[0] for u in units]
        return model.phonemes_to_ids(near)

    async def speak(voice: Voice, parts: list[PartIn]) -> AsyncIterator[np.ndarray]:
        model = loaded[str(voice.model)]
        config = SynthesisConfig(length_scale=1.0 / voice.speed)
        audio = await asyncio.to_thread(
            model.phoneme_ids_to_audio, ids(model, voice, parts), config
        )
        native = model.config.sample_rate
        yield audio if native == rate else soxr.resample(audio, native, rate)

    return speak


def build(settings: Settings) -> FastAPI:
    rate = settings.sample_rate
    engines: dict[str, Engine] = {}
    kokoro_voices: set[str] = set()
    if any(v.engine == "kokoro" for v in settings.voices.values()):
        if settings.kokoro is None:
            raise ValueError("a kokoro voice needs the kokoro files")
        engines["kokoro"], kokoro_voices = kokoro_engine(settings.kokoro, rate)
    if any(v.engine == "piper" for v in settings.voices.values()):
        engines["piper"] = piper_engine(settings.voices, rate)
    for name, v in settings.voices.items():
        # Açılışta bulunmayan ses, ilk cümlede sessizlik olurdu.
        if v.engine == "kokoro" and v.voice not in kokoro_voices:
            raise ValueError(f"voice {name}: kokoro has no {v.voice!r}")
        if v.engine == "piper" and v.model is None:
            raise ValueError(f"voice {name}: piper needs a model")
        if v.effect is not None and v.effect not in settings.effects:
            raise ValueError(f"voice {name}: no effect {v.effect!r}")

    lock = asyncio.Lock()
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "sample_rate": rate,
            "voices": sorted(settings.voices),
        }

    @app.post("/speak")
    async def speak(body: SpeakIn) -> StreamingResponse:
        if body.schema_version != SCHEMA_VERSION:
            raise HTTPException(400, f"schema_version {body.schema_version}")
        voice = settings.voices.get(body.voice)
        if voice is None:
            raise HTTPException(404, f"no voice {body.voice!r}")
        effect = None if voice.effect is None else Radio(settings.effects[voice.effect], rate)
        engine = engines[voice.engine]

        async def audio() -> AsyncIterator[bytes]:
            async with lock:
                async for samples in engine(voice, body.parts):
                    yield _pcm(samples if effect is None else effect(samples))

        return StreamingResponse(
            audio(),
            media_type="application/octet-stream",
            headers={"X-Schema-Version": str(SCHEMA_VERSION), "X-Sample-Rate": str(rate)},
        )

    return app


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: main.py <config.yaml>")
    settings = Settings.model_validate(yaml.safe_load(Path(sys.argv[1]).read_text()))
    print(f"tts: voices {sorted(settings.voices)} at {settings.sample_rate} Hz", flush=True)
    uvicorn.run(build(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
