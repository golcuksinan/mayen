"""Mayen'in STT servisi: Whisper (faster-whisper), kendi sürecinde, HTTP arkasında.

Çekirdek model yüklemez; model burada yaşar, çekirdekte yalnızca ince bir istemci durur.
Model çökerse ya da belleği taşarsa çekirdek ayakta kalır, model değiştirmek çekirdeği yeniden
başlatmaz, başka makineye taşımak bir adres değişikliğidir.

Sözleşme çekirdeğin `ports/speech.py` modülündedir; bu servis onu import etmez, burada aynen
kurar. Her yanıt `schema_version` taşır.

VAD modeli (Silero, faster-whisper'ın içindeki) da burada yaşar: `/vad` akan sesin her parçasına
bir konuşma olasılığı döner. Sözün başı ve sonu olasılıktan çekirdekte çıkar; `/transcribe`'a
bitmiş bir söz gelir. Sözün bitip bitmediğini bulan model (Pipecat'in Smart Turn'ü) da burada:
`/turn` sözün o ana kadarki sesine bir "bitti" olasılığı döner; eşik çekirdektedir. Sessizlik
elemesi
Whisper'ın kendi kuralıdır (faster-whisper'ın varsayılanı: `no_speech_prob` 0.6'nın üstünde
**ve** `avg_logprob` -1'in altında olan parça atılır); tek sinyalle eleme cümle başlarını
yutar.

Çalıştırma:

    uv run --project services/stt python services/stt/main.py <config.yaml>
"""

import asyncio
import ctypes
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = 1

SAMPLE_RATE = 16_000
"""Whisper'ın girdi hızı: modelin özelliği, ayar değil. `/health` bildirir; istemci sesi bu
hıza kendisi çevirir."""

VAD_FRAME = 512
"""Silero'nun 16 kHz'de bir seferde baktığı örnek sayısı; bağlamı önceki parçanın son 64'ü."""
VAD_CONTEXT = 64
VAD_RESET_FRAMES = 5 * SAMPLE_RATE // VAD_FRAME
"""Model durumu bu kadar parçada bir sıfırlanır (Pipecat'in Silero'suyla aynı, ~5 sn): durum
uzun akışta sürüklenir, söz için birkaç saniyeden eskisi gerekmez."""


class Silero:
    """Tek bir ses akışının VAD durumu; parçaları sırayla alır."""

    def __init__(self, session: Any) -> None:  # noqa: ANN401  # onnxruntime.InferenceSession
        self._session = session
        self._frames = 0
        self._reset()

    def _reset(self) -> None:
        self._h = np.zeros((1, 1, 128), np.float32)
        self._c = np.zeros((1, 1, 128), np.float32)
        self._context = np.zeros((1, VAD_CONTEXT), np.float32)

    def __call__(self, pcm: bytes) -> float:
        chunk = (np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0)[None]
        x = np.concatenate([self._context, chunk], 1)
        out, self._h, self._c = self._session.run(
            None, {"input": x, "h": self._h, "c": self._c}
        )
        self._context = x[:, -VAD_CONTEXT:]
        self._frames += 1
        if self._frames % VAD_RESET_FRAMES == 0:
            self._reset()
        return float(np.ravel(out)[0])


class Turn:
    """Sözün bittiği olasılığı; çekirdekteki Pipecat'in yerel modeliyle aynı hesap.

    Kesiti (son 8 sn) ve özellikleri Pipecat'in analizcisi hazırlar; onu çekirdek değil bu
    süreç yükler. Eşiğin uyguladığı karar dönmez, olasılık döner.
    """

    def __init__(self) -> None:
        from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

        self._model = LocalSmartTurnAnalyzerV3()

    def __call__(self, pcm: bytes) -> float:
        audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
        return float(self._model._predict_endpoint(audio)["probability"])


def vad_session() -> Any:  # noqa: ANN401
    import onnxruntime
    from faster_whisper.utils import get_assets_path

    options = onnxruntime.SessionOptions()
    options.inter_op_num_threads = 1
    options.intra_op_num_threads = 1
    options.log_severity_level = 4
    # Parça başına çalışan küçük bir model; CPU'da GPU'ya gidip gelmekten hızlı.
    return onnxruntime.InferenceSession(
        os.path.join(get_assets_path(), "silero_vad_v6.onnx"),
        providers=["CPUExecutionProvider"],
        sess_options=options,
    )


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
    # Oturum durumsuzdur, bağlantılar paylaşır; durum her bağlantının `Silero`'sundadır.
    vad = vad_session()
    turn = Turn()
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

    @app.post("/turn")
    async def end_of_turn(request: Request, sample_rate: int) -> dict[str, Any]:
        if sample_rate != SAMPLE_RATE:
            raise HTTPException(400, f"expected {SAMPLE_RATE} Hz, got {sample_rate}")
        body = await request.body()
        if not body or len(body) % 2:
            raise HTTPException(400, "body is not 16-bit PCM")
        probability = await asyncio.to_thread(turn, body)
        return {"schema_version": SCHEMA_VERSION, "probability": probability}

    @app.websocket("/vad")
    async def voice_activity(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_json(
            {"schema_version": SCHEMA_VERSION, "sample_rate": SAMPLE_RATE, "frame": VAD_FRAME}
        )
        silero = Silero(vad)
        try:
            while True:
                pcm = await websocket.receive_bytes()
                if len(pcm) != VAD_FRAME * 2:
                    await websocket.close(code=1003, reason=f"expected {VAD_FRAME} samples")
                    return
                # Parça başına model döngüyü bekletmeyecek kadar kısa sürer.
                await websocket.send_bytes(np.array(silero(pcm), "<f4").tobytes())
        except WebSocketDisconnect:
            pass

    return app


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: main.py <config.yaml>")
    settings = Settings.model_validate(yaml.safe_load(Path(sys.argv[1]).read_text()))
    print(f"stt: {settings.model} on {settings.device} ({settings.compute_type})", flush=True)
    uvicorn.run(build(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
