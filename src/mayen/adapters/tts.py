"""TTS servisi arayüzü (§6).

Sıralama burada zorlanmaz: §6'nın "parça N+1, parça N gönderilmeden gönderilmez" kuralı
TTS kuyruğunun işi (P8). Bu arayüz tek bir metin parçasını sese çevirir; kuyruk onu
cümle bölücünün verdiği sırayla çağırır.
"""

from collections.abc import AsyncGenerator
from typing import Protocol

from mayen.adapters.audio import AudioFormat
from mayen.adapters.service import ModelService


class TTSClient(ModelService, Protocol):
    @property
    def output_format(self) -> AudioFormat:
        """Ürettiği sesin biçimi. Çerçeve başlığına bu yazılır; taşıma katmanı biçimi
        tahmin etmez."""
        ...

    def synthesize(self, text: str) -> AsyncGenerator[bytes]:
        """Metni parça parça sese çevirir.

        Akışlı, çünkü ilk sesin çıkış süresi ölçülen bir hedef (§6): son parçayı bekleyen
        bir arayüz o bütçeyi baştan harcar. İptal, `stream` ile aynı yoldan — üreteci
        kapatmak (Kural 12).
        """
        ...
