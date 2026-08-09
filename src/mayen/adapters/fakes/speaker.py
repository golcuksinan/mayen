"""Sahte konuşmacı tanıma."""

import hashlib

from mayen.adapters.audio import Audio
from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.speaker import Embedding

DIMENSION = 16


class FakeSpeaker:
    """Ses yükünden **belirlenimci** bir gömü üretir.

    Aynı ses hep aynı vektörü, farklı ses farklı vektörü verir. Rastgele bir vektör
    döndürmek testleri sessizce yanıltırdı: iki farklı konuşmacı kazara eşleşebilir ya da
    aynı konuşmacı iki turda eşleşmeyebilirdi. `values` bire indirgenmiş (norm 1) çünkü
    karşılaştırma kosinüs benzerliğine dayanacak (§10.1).
    """

    def __init__(self, *, name: str = "fake-speaker", available: bool = True) -> None:
        self._name = name
        self.available = available
        self.calls: list[Audio] = []

    @property
    def name(self) -> str:
        return self._name

    async def health(self) -> bool:
        return self.available

    async def embed(self, audio: Audio) -> Embedding:
        if not self.available:
            raise ServiceUnavailableError(self._name, "servis kapalı")
        self.calls.append(audio)
        digest = hashlib.blake2b(audio.data, digest_size=DIMENSION).digest()
        norm = sum(b * b for b in digest) ** 0.5
        return Embedding(tuple(b / norm for b in digest))
