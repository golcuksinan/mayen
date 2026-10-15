"""Mayen'in STT servisi: Whisper (faster-whisper), kendi sürecinde, HTTP arkasında.

Çekirdek model yüklemez; model burada yaşar, çekirdekte yalnızca ince bir istemci durur.
Model çökerse ya da belleği taşarsa çekirdek ayakta kalır, model değiştirmek çekirdeği yeniden
başlatmaz, başka makineye taşımak bir adres değişikliğidir.

Sözleşme çekirdeğin `ports/speech.py` modülündedir; bu servis onu import etmez, burada aynen
kurar. Her yanıt `schema_version` taşır.

Sözün başı ve sonu çekirdeğin işidir (VAD); buraya bitmiş bir söz gelir. Sessizlik elemesi
Whisper'ın kendi kuralıdır (faster-whisper'ın varsayılanı: `no_speech_prob` 0.6'nın üstünde
**ve** `avg_logprob` -1'in altında olan parça atılır); tek sinyalle eleme cümle başlarını
yutar.

Çalıştırma:

    uv run --project services/stt python services/stt/main.py <config.yaml>
"""

import asyncio
import ctypes
import sys
from pathlib import Path
from typing import Any

import numpy as np
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = 1

SAMPLE_RATE = 16_000
"""Whisper'ın girdi hızı: modelin özelliği, ayar değil. `/health` bildirir; istemci sesi bu
hıza kendisi çevirir."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = "127.0.0.1"
    port: int = 8770
    model: str  # faster-whisper model klasörü ya da adı
    device: str = "cuda"
    compute_type: str = "float16"


def preload_cuda() -> None:
    """Pip'ten gelen cuBLAS/cuDNN'i önceden yükler; CTranslate2 onları sistem yolunda arar."""
    import nvidia.cublas
    import nvidia.cudnn

    left = [
        so
        for package in (nvidia.cublas, nvidia.cudnn)
        for so in (Path(package.__path__[0]) / "lib").glob("*.so.*")
    ]
    # Kütüphaneler birbirine bağlı; sıra bilinmediği için ilerleme durana kadar tekrar denenir.
    while left:
        failed = []
        for so in left:
            try:
                ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                failed.append(so)
        if len(failed) == len(left):
            raise OSError(f"cannot load {[p.name for p in failed]}")
        left = failed


def build(settings: Settings) -> FastAPI:
    if settings.device == "cuda":
        preload_cuda()
    from faster_whisper import WhisperModel

    model = WhisperModel(
        settings.model, device=settings.device, compute_type=settings.compute_type
    )
    # Model durumu eşzamanlı çağrılar için güvenli sayılmaz; sözler sırayla çözülür.
    lock = asyncio.Lock()
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "sample_rate": SAMPLE_RATE, "voices": []}

    def transcribe_sync(audio: np.ndarray, language: str | None) -> dict[str, Any]:
        segments, info = model.transcribe(audio, language=language, vad_filter=False)
        kept = [
            {
                "text": s.text,
                "no_speech_prob": s.no_speech_prob,
                "avg_logprob": s.avg_logprob,
            }
            for s in segments
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "text": "".join(s["text"] for s in kept),
            "language": info.language,
            "segments": kept,
        }

    @app.post("/transcribe")
    async def transcribe(request: Request, language: str | None = None) -> dict[str, Any]:
        body = await request.body()
        if len(body) % 2:
            raise HTTPException(400, "body is not 16-bit PCM")
        audio = np.frombuffer(body, np.int16).astype(np.float32) / 32768.0
        async with lock:
            return await asyncio.to_thread(transcribe_sync, audio, language)

    return app


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: main.py <config.yaml>")
    settings = Settings.model_validate(yaml.safe_load(Path(sys.argv[1]).read_text()))
    print(f"stt: {settings.model} on {settings.device} ({settings.compute_type})", flush=True)
    uvicorn.run(build(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
