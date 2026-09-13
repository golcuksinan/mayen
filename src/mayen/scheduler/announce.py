"""Proaktif ses kanalı (§12).

Zamanlanmış bir görev, kullanıcı hiçbir şey sormadan ses üretebilir. Bu kanal **tur
akışından ayrıdır ama aynı TTS kuyruğunu kullanır** — o yüzden burada ikinci bir sentez
yolu yok, `turn.speech.SpeechQueue` olduğu gibi çağrılıyor.

**Proaktif ses bir tur değil.** §5'in tablosunda karşılığı yok ve burası oturuma durum
yürütmüyor; yürütseydi, tabloda olmayan bir geçişi kod uydurmuş olurdu. Turdan aldığı tek
şey **sıra**: `Session.exclusive()` global tur kilidini tutuyor, yani bildirim kullanıcı
ya da asistan konuşurken araya girmiyor, sıraya giriyor (§12).

**Kendi `turn_id`'si var** (§12) ve bu onu söz kesmeden koruyan şeyin ta kendisi: iptalin
kapsamı tek tur (§5, §13), yani kullanıcının asistanı kesmesi kuyruktaki hatırlatıcıyı
sessizce çöpe atmaz. Ama aynı kural istemcide de var — bilmediği turun parçası çalınmaz —
bu yüzden sesten önce `Announcement` çerçevesi gidiyor ve turu istemciye o açıyor.

**Hedef: en son etkileşimde bulunulan cihaz** (§12). Sıra oturumdan, bağlılık defterden
geliyor; ikisinin kesişimi boşsa bildirim **kuyruklanır ve ilk bağlanan cihaza verilir**.
Düşürmek olmazdı: hatırlatıcı, duyulmadığında hiçbir işe yaramayan tek çıktı türü.

**Metin tek parça sentezleniyor**, cümle bölücüden geçmiyor. Bölücünün işi akan token'ları
erkenden sese çevirmek (§6); burada metnin tamamı zaten elde ve bir hatırlatıcı bir
cümledir. Bölücüyü çağırmak, olmayan bir akışı taklit etmek olurdu.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import Protocol

from mayen.adapters.audio import AudioFormat
from mayen.adapters.tts import TTSClient
from mayen.obs.log import get_logger
from mayen.obs.trace import new_turn_id
from mayen.session.actor import Session
from mayen.turn.speech import SpeechQueue

log = get_logger(__name__)


class ProactiveSink(Protocol):
    """Bildirimin dışarı çıktığı kapı. `transport` uygular, `scheduler` bilmez.

    Turun sinkinden ayrı, çünkü yönlendirme kuralı başka: turun sesi `active_turn`'ün
    cihazına gider, bildirimin sesi ise **adı verilen** cihaza — ortada tur yok.
    """

    def connected(self) -> frozenset[str]: ...

    async def announcement(self, device_id: str, turn_id: str, text: str) -> None: ...

    async def announcement_chunk(
        self, device_id: str, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None: ...

    async def announcement_end(self, device_id: str, turn_id: str) -> None: ...


class _DeviceAudio:
    """`SpeechQueue`'nun beklediği `AudioSink`'i tek cihaza bağlar.

    Uyarlayıcı burada, çünkü kuyruğun sözleşmesini bildirim için genişletmek turu
    ilgilendirmeyen bir alanı (`device_id`) tur akışının içine sokardı.
    """

    def __init__(self, sink: ProactiveSink, device_id: str) -> None:
        self._sink = sink
        self._device_id = device_id

    async def reply(self, turn_id: str, text: str) -> None:
        """Proaktif metin **yollanmıyor**: `Announcement` onu sesten önce zaten taşıdı
        (§12) ve ikinci bir çerçeve aynı cümleyi ekranda iki kez gösterirdi."""

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        await self._sink.announcement_chunk(self._device_id, turn_id, seq, audio_format, data)

    async def audio_end(self, turn_id: str) -> None:
        await self._sink.announcement_end(self._device_id, turn_id)


class Announcer:
    """Metni proaktif olarak seslendiren taraf."""

    def __init__(self, tts: TTSClient, session: Session, sink: ProactiveSink) -> None:
        self._tts = tts
        self._session = session
        self._sink = sink
        #: Hiçbir cihaz bağlı değilken biriken bildirimler (§12). Sırası korunuyor:
        #: iki hatırlatıcı ters sırada duyulursa hangisinin ne zamana ait olduğu kaybolur.
        self._pending: list[str] = []
        self._tasks: set[asyncio.Task[None]] = set()

    async def announce(self, text: str) -> str | None:
        """Bildirimi seslendirir; cihaz yoksa kuyruklar.

        Dönen değer turun kimliği, kuyruğa alındıysa `None` — çağıran hangi görevin
        gerçekten duyulduğunu kayda geçirebilsin diye (Kural 13).
        """
        device_id = self._target()
        if device_id is None:
            self._pending.append(text)
            log.info("bildirim kuyruklandı: bağlı cihaz yok", pending=len(self._pending))
            return None
        return await self._speak(device_id, text)

    def connected(self, device_id: str) -> None:
        """Bir cihaz bağlandı: bekleyen bildirimler ona verilir (§12).

        Görev olarak koşuyor, çünkü çağıran el sıkışmayı yeni bitirmiş okuma döngüsü:
        orada beklemek, bildirim seslendirilene kadar o bağlantıdan gelen hiçbir çerçevenin
        —söz kesme dâhil (Kural 12)— okunmaması demek olurdu.
        """
        if not self._pending:
            return
        pending, self._pending = self._pending, []
        task = asyncio.create_task(self._drain(device_id, pending), name="announce:pending")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def close(self) -> None:
        for task in tuple(self._tasks):
            task.cancel()
        for task in tuple(self._tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _drain(self, device_id: str, pending: list[str]) -> None:
        for text in pending:
            await self._speak(device_id, text)

    async def _speak(self, device_id: str, text: str) -> str:
        turn_id = new_turn_id()
        # Kilit sentezin **tamamını** kapsıyor: yalnızca ilk parçayı korumak, kullanıcının
        # araya giren turuyla bildirimin ortasından itibaren üst üste binmesi olurdu.
        async with self._session.exclusive():
            queue = SpeechQueue(self._tts, _DeviceAudio(self._sink, device_id))
            # Önce çerçeve, sonra ses: istemci turu bilmeden gelen parçayı §13 gereği atar.
            await self._sink.announcement(device_id, turn_id, text)
            await queue.speak(turn_id, _one(text))
            await queue.end(turn_id)
        log.info("bildirim seslendirildi", turn_id=turn_id, device_id=device_id)
        return turn_id

    def _target(self) -> str | None:
        """En son etkileşimde bulunulan **bağlı** cihaz (§12)."""
        connected = self._sink.connected()
        if not connected:
            return None
        for device_id in self._session.recent_devices():
            if device_id in connected:
                return device_id
        # Bağlı ama hiç konuşulmamış cihaz: hedef yine de var. Sıralı bir seçim değil,
        # ama bildirimin duyulması bunun tek alternatifi olan sessizlikten iyidir.
        return sorted(connected)[0]


async def _one(text: str) -> AsyncIterator[str]:
    yield text
