"""Sıralı TTS kuyruğu (§6).

**Parça N+1, parça N gönderilmeden gönderilmez.** §6 sıra bozulmasını kabul edilemez bir
hata sayıyor, o yüzden burada paralellik yok: bir cümle sentezlenip tamamen gönderilmeden
sonrakine geçilmiyor. Bir sonraki cümleyi önden sentezlemek ilk sesi hızlandırmaz — ilk
cümle zaten sıradaki ilk iş — ama sırayı yalnızca zamanlamaya emanet ederdi.

**`seq` tur boyunca artar, cümle başına sıfırlanmaz** (§13): istemci sırayı bununla
doğruluyor ve cümle sınırını bilmiyor.

**Çerçeveyi burası kurmuyor.** `transport` `turn`'ün *üstünde* (§4), yani `AudioChunk`
buradan üretilemez; kuyruk bir `AudioSink`'e yazıyor, çerçeveye çeviren taraf onu uyguluyor.
`SessionSink`/`TraceSink` kalıbının aynısı.

**İptal (Kural 12):** sentez üreteci `aclosing` içinde; tur iptal edildiğinde yarım kalan
sentez kapanır. O tura ait, kuyrukta bekleyen çerçeveleri düşürmek `SendQueue.cancel_turn`'ün
işi — kuyruk `transport`'ta ve buradan görünmüyor.
"""

from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Protocol

from mayen.adapters.audio import AudioFormat
from mayen.adapters.tts import TTSClient


class AudioSink(Protocol):
    """Turun ürettiği sesin çıkış kapısı. `transport` uygular, `turn` bilmez."""

    async def reply(self, turn_id: str, text: str) -> None:
        """Seslendirilmek üzere olan cümlenin metni (§13'ün `Reply` çerçevesi)."""
        ...

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None: ...

    async def audio_end(self, turn_id: str) -> None: ...


class SpeechQueue:
    """Cümleleri geldikleri sırayla sese çevirir ve sırayla gönderir."""

    def __init__(self, tts: TTSClient, sink: AudioSink) -> None:
        self._tts = tts
        self._sink = sink
        self._seq = 0

    async def speak(self, turn_id: str, pieces: AsyncIterator[str]) -> None:
        """Cümle bölücünün çıktısını sırayla seslendirir. Tur başına birden çok kez
        çağrılabilir: onay cümlesi ile asıl yanıt aynı turun sesidir ve `seq` ikisi boyunca
        artar."""
        async for piece in pieces:
            # Metin sesten **önce**: istemci cümleyi, sesi başlamadan görüyor. Sonra
            # yazılsaydı ekran hep bir cümle geriden gelirdi. Sentez patlarsa (§14) cümle
            # yine de görünmüş oluyor — hatırlatıcının metnini taşımanın gerekçesiyle aynı.
            await self._sink.reply(turn_id, piece)
            async with aclosing(self._tts.synthesize(piece)) as audio:
                async for data in audio:
                    await self._sink.audio_chunk(
                        turn_id, self._seq, self._tts.output_format, data
                    )
                    self._seq += 1

    async def end(self, turn_id: str) -> None:
        """Turun sesi bitti (§13).

        `speak` bunu kendisi yazmıyor: onay cümlesi de bu kuyruktan geçiyor ve turun
        ortasında yazılan bir `AudioEnd`, istemciye turun bittiğini söylerdi. İptalde ise
        hiç yazılmaz — turun bittiğini söyleyen çerçeve `Cancelled` olur.
        """
        await self._sink.audio_end(turn_id)
