"""Mayen'in konuşmacı servisi: SpeechBrain ECAPA-TDNN, kendi sürecinde, HTTP arkasında (§3, §6).

Servis yalnızca izi çıkarır: kimseyi tanımaz, iz tutmaz. Kayıtlı izle karşılaştırıp puanı bulan
ve eşikle karar veren çekirdektir; ses izleri çekirdeğin kişi deposundadır (§11.1).

Sözleşme çekirdeğin `ports/speech.py` modülündedir; bu servis onu import etmez, burada aynen
kurar. Her yanıt `schema_version` taşır. `model` alanı izi çıkaran modelin adıdır: çekirdek
başka modelin iziyle karşılaştırmaz.

Çalıştırma:

    uv run --project services/speaker python services/speaker/main.py <config.yaml>
"""

import asyncio
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
"""ECAPA'nın eğitildiği hız: modelin özelliği, ayar değil. `/health` bildirir."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = "127.0.0.1"
    port: int = 8772
    model: str  # Hugging Face kimliği ya da indirilmiş klasör
    savedir: Path
    device: str = "cpu"


class Encoder:
    """Sözün sesinden birim uzunlukta iz."""

    def __init__(self, settings: Settings) -> None:
        from speechbrain.inference.speaker import EncoderClassifier

        self._model = EncoderClassifier.from_hparams(
            source=settings.model,
            savedir=str(settings.savedir.expanduser()),
            run_opts={"device": settings.device},
        )

    def __call__(self, pcm: bytes) -> list[float]:
        import torch

        audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
        with torch.no_grad():
            vector = self._model.encode_batch(torch.from_numpy(audio)[None]).squeeze().cpu()
        norm = float(torch.linalg.vector_norm(vector))
        if norm == 0:
            raise ValueError("zero embedding")
        return [float(x) / norm for x in vector]


def build(settings: Settings) -> FastAPI:
    encoder = Encoder(settings)
    # Model durumu eşzamanlı çağrılar için güvenli sayılmaz; sözler sırayla işlenir.
    lock = asyncio.Lock()
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "sample_rate": SAMPLE_RATE, "voices": []}

    @app.post("/embed")
    async def embed(request: Request) -> dict[str, Any]:
        body = await request.body()
        if not body or len(body) % 2:
            raise HTTPException(400, "body is not 16-bit PCM")
        async with lock:
            try:
                vector = await asyncio.to_thread(encoder, body)
            except (ValueError, RuntimeError) as e:  # RuntimeError: modele göre çok kısa ses
                raise HTTPException(422, str(e)) from e
        return {"schema_version": SCHEMA_VERSION, "model": settings.model, "vector": vector}

    return app


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: main.py <config.yaml>")
    settings = Settings.model_validate(yaml.safe_load(Path(sys.argv[1]).read_text()))
    print(f"speaker: {settings.model} on {settings.device}", flush=True)
    uvicorn.run(build(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
