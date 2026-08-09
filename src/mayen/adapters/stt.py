"""STT servisi arayüzü (§6, §7).

Sunucu segment tespiti yapmaz: istemci tamamlanmış bir konuşma segmenti gönderir, buraya
o gelir (§7). Bu yüzden akışlı bir arayüz değil — tek segment girer, tek transkript çıkar.
"""

from dataclasses import dataclass
from typing import Protocol

from mayen.adapters.audio import Audio
from mayen.adapters.service import ModelService


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    language: str
    confidence: float | None
    """Servis vermiyorsa `None`. Sıfır yazmak "hiç güvenmiyorum" demek olurdu; eksik veri
    ile düşük değer aynı şey değil."""


class STTClient(ModelService, Protocol):
    async def transcribe(self, audio: Audio) -> Transcript:
        """Türkçe konuşmayı metne çevirir. Konuşmacı tanımayla paralel koşar ve onu
        beklemez (§6)."""
        ...
