"""Sahibin ses izi (§10.2, §10.4): ses dosyalarından, konuşmacı servisiyle.

Kurulum betiğinin parçasıdır ve makinenin başında çalışır; iz sesle verilemez. Örneklerin izleri
birim uzunlukta ortalanır. Dosyalar 16 bit PCM WAV'dır ve hızları servisin bildirdiği hızdır;
çevirme yapılmaz, hızı tutmayan dosya reddedilir: sessizce yeniden örneklenen bir kayıt izi
bozabilir ve bu hiçbir yerde görünmez.
"""

import json
import urllib.error
import urllib.request
import wave
from collections.abc import Sequence
from pathlib import Path

from mayen.core.speakers import mean
from mayen.ports.speech import EMBED, HEALTH, Embedding, parse_embedding, parse_health


class VoiceError(Exception):
    """Ses dosyası ya da konuşmacı servisi kullanılamıyor."""


def read_pcm(path: Path, sample_rate: int) -> bytes:
    """Tek kanal 16 bit PCM; çok kanallı dosyada yalnızca ilk kanal."""
    try:
        with wave.open(str(path), "rb") as w:
            if w.getsampwidth() != 2:
                raise VoiceError(f"{path}: not 16-bit PCM")
            if w.getframerate() != sample_rate:
                raise VoiceError(
                    f"{path}: {w.getframerate()} Hz, the speaker service wants {sample_rate} Hz"
                    f" (ffmpeg -i {path.name} -ac 1 -ar {sample_rate} -sample_fmt s16 out.wav)"
                )
            channels = w.getnchannels()
            frames = w.readframes(w.getnframes())
    except (OSError, wave.Error, EOFError) as e:
        raise VoiceError(f"{path}: {e}") from e
    if channels == 1:
        return frames
    step = 2 * channels
    return b"".join(frames[i : i + 2] for i in range(0, len(frames), step))


def _request(url: str, data: bytes | None = None) -> object:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data), timeout=60) as r:
            return json.load(r)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        raise VoiceError(f"speaker service {url}: {e}") from e


def voiceprint(url: str, files: Sequence[Path]) -> Embedding:
    """Dosyaların ortak izi; model, servisin bildirdiği modeldir."""
    if not files:
        raise VoiceError("no voice samples")
    base = url.rstrip("/")
    rate = parse_health(_request(base + HEALTH)).sample_rate
    embeddings = [parse_embedding(_request(base + EMBED, read_pcm(f, rate))) for f in files]
    models = {e.model for e in embeddings}
    if len(models) != 1:
        raise VoiceError(f"the speaker service changed model mid-way: {sorted(models)}")
    return Embedding(models.pop(), mean([e.vector for e in embeddings]))
