"""Mikrofon ve hoparlör: iki `Protocol`, iki sahte, bir PortAudio arka ucu.

Adaptör kalıbının aynısı (§4): donanım arayüzün arkasında. Sebebi de aynı — endpointing,
tur takibi ve söz kesme mantığı ses kartı olmadan, saniyenin altında ölçülebilmeli. CI'da
ses kartı yok; olsaydı bile mikrofonun ne duyduğu belirlenimci olmazdı.

**Yerelde ham PCM** (§13): 16 kHz, tek kanal, 16 bit işaretli. §19.5'in açık olduğu şey
*uzak* bağlantının sıkıştırması; yerelde doküman zaten PCM diyor ve kodek alanı çerçevede
duruyor.

**`sounddevice` isteğe bağlı bir bağımlılık.** PortAudio sistem kütüphanesi ister ve
metin istemcisinin ona ihtiyacı yok; import bu yüzden fonksiyonun içinde, kurulu değilse
hata anlaşılır (`ConfigError` değil, kurulum talimatı olan bir mesaj).
"""

import array
import math
from collections.abc import AsyncIterator
from typing import Protocol

from mayen.adapters.audio import AudioFormat, Codec

FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)
"""Yerelin biçimi. Tek yerde yazılı; mikrofon, hoparlör ve çerçeve aynı sayıyı kullanır."""

FRAME_MS = 20
"""Bir çerçevenin süresi. Yirmi milisaniye VAD'lerin alışılmış adımı: konuşma başlangıcını
yakalayacak kadar kısa, çerçeve başına iş anlamlı kalacak kadar uzun."""

SAMPLE_BYTES = 2
"""Bir örneğin uzunluğu (PCM16). Bölünmesi gereken sayı; hoparlör de bunu kullanıyor."""

FRAME_BYTES = FORMAT.sample_rate * FRAME_MS // 1000 * SAMPLE_BYTES


class AudioSource(Protocol):
    """Mikrofon: sabit boyda PCM çerçeveleri akıtır."""

    def frames(self) -> AsyncIterator[bytes]: ...


class AudioPlayer(Protocol):
    """Hoparlör. `stop()` çalanı **anında** kesmeli: söz kesmenin duyulur karşılığı o."""

    async def play(self, data: bytes) -> None: ...

    async def stop(self) -> None: ...

    async def close(self) -> None: ...


def rms(frame: bytes) -> float:
    """Çerçevenin karekök ortalaması (0–32767). `audioop` 3.13'te kaldırıldı, elle.

    Tek sayıda bayt yarım bir örnek demektir — sessizce kırpmak sıralamayı bozar ve
    hatayı çok uzakta gösterir (Kural 13).
    """
    if len(frame) % 2:
        raise ValueError(f"PCM16 çerçevesi çift sayıda bayt olmalı, {len(frame)} geldi")
    if not frame:
        return 0.0
    samples = array.array("h")
    samples.frombytes(frame)
    return math.sqrt(sum(float(s) * s for s in samples) / len(samples))


class FakeMicrophone:
    """Verilen çerçeveleri sırayla akıtır."""

    def __init__(self, frames: list[bytes]) -> None:
        self._frames = frames

    async def frames(self) -> AsyncIterator[bytes]:
        for frame in self._frames:
            yield frame


class FakePlayer:
    """Çalınanı biriktirir; `stop()` sonrası ne kaldığı testin asıl ölçtüğü şey."""

    def __init__(self) -> None:
        self.played: list[bytes] = []
        self.stops = 0
        self.closed = False

    async def play(self, data: bytes) -> None:
        self.played.append(data)

    async def stop(self) -> None:
        self.stops += 1
        self.played.clear()

    async def close(self) -> None:
        self.closed = True
