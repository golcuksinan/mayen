"""Sahte TTS."""

import asyncio
from collections.abc import AsyncGenerator

from mayen.adapters.audio import AudioFormat, Codec
from mayen.adapters.errors import ServiceUnavailableError

FAKE_FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)


class FakeTTS:
    """Metni UTF-8 baytları olarak "seslendirir".

    Yük okunabilir kalıyor: bir testin ses parçasını çözüp hangi cümlenin çalındığını
    doğrulayabilmesi, TTS kuyruğunun sıra kuralını (§6) test edilebilir yapan şey.

    **Cümlenin sonuna bir boşluk ekleniyor.** Bölücü cümleleri `strip()`'liyor (TTS'e
    boşluk vermek anlamsız) ve gerçek TTS'te iki cümlenin arasındaki ayrım seste zaten
    var — duraklama. Metin olarak akıtınca o ayrım kayboluyordu ve istemcide cümleler
    "çalışmıyor.Başka" diye bitişiyordu. Ayıracı ekleyecek yer burası: cümleyi akıtılacak
    yüke çeviren tek yer bu, ve istemci parçaların cümle sınırını göremez.
    """

    def __init__(
        self, *, name: str = "fake-tts", chunk_size: int = 8, available: bool = True
    ) -> None:
        self._name = name
        self._chunk_size = chunk_size
        self.available = available
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def output_format(self) -> AudioFormat:
        return FAKE_FORMAT

    async def health(self) -> bool:
        return self.available

    async def synthesize(self, text: str) -> AsyncGenerator[bytes]:
        if not self.available:
            raise ServiceUnavailableError(self._name, "servis kapalı")
        self.calls.append(text)
        payload = (text if text.endswith(" ") else f"{text} ").encode("utf-8")
        for start in range(0, len(payload), self._chunk_size):
            await asyncio.sleep(0)
            yield payload[start : start + self._chunk_size]
