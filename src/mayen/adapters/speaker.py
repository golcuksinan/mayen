"""Konuşmacı tanıma servisi arayüzü (§3, §10.1).

Kendi sürecinde ve HTTP arkasında, ama **CPU'da** — Kural 2'ye istisna açılmadı, VRAM
bütçesi LLM/STT/TTS üçlüsüne kaldı (§3).

Arayüz yalnızca **gömü çıkarır**. Karşılaştırma, skor ve güven seviyesi burada değil:
kayıtlı profiller `data`'da durur, kademeye çeviren şey `policy`'dir ve eşikler §19.3'te
hâlâ açık. Skorlamayı buraya koymak, açık bir maddeyi varsayımla kapatmak olurdu.
"""

from dataclasses import dataclass
from typing import Protocol

from mayen.adapters.audio import Audio
from mayen.adapters.service import ModelService


@dataclass(frozen=True, slots=True)
class Embedding:
    """Ses gömüsü. Bir iddia değil, karşılaştırılacak bir vektör (§10.1)."""

    values: tuple[float, ...]

    def __len__(self) -> int:
        return len(self.values)


class SpeakerClient(ModelService, Protocol):
    async def embed(self, audio: Audio) -> Embedding:
        """Segmentten gömü çıkarır. STT ile paralel koşar ve onu beklemez (§6)."""
        ...
