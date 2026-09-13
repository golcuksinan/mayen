"""Sesin giydirildiği yer: hoparlöre çalan `Output` ve mikrofonu dinleyen döngü.

Metin istemcisinin protokol tarafı (`client/core.py`) hiç değişmiyor — P17'nin bütün
amacı buydu. Değişen tek şey `Output`'un uygulaması ve segmentin nereden geldiği.

**Yarım dubleks, bilerek ve geçici.** AEC yok; asistan konuşurken mikrofon onun kendi
sesini duyar ve her cevabı kendi kendine söz kesme sanardı. §18 bu ödünü zaten adıyla
koyuyor: yarım dubleks (konuşurken mikrofonu yok saymak) söz kesmeyi **öldürür**, o yüzden
gerçek bir AEC gerekir. Burada yapılan, o AEC gelene kadar sistemin çalışır kalmasıdır —
karar değil, ara durum. `--soz-kesme` bayrağı ödünü tersine çevirmek isteyene açık, ve ne
olacağı yardımda yazılı.

**Söz kesme konuşmanın başında yollanır**, segmentin sonunda değil: sonu beklemek, kullanıcı
sustuktan yarım saniye sonra kesmek olurdu — asistan o sırada hâlâ konuşuyor.

**İptal sesi anında keser.** `Cancelled` çerçevesi gelince hoparlörün tamponu atılıyor;
çalıp bitirmek iptali duyulur olmaktan çıkarırdı (§13).
"""

from client.audio import FORMAT, AudioPlayer, AudioSource
from client.core import Client
from client.endpointing import Endpointer, Settings
from client.output import Output, TextOutput
from mayen.obs.log import get_logger
from mayen.session.state import State

log = get_logger(__name__)


class VoiceOutput:
    """Ses parçalarını hoparlöre, geri kalanını uçbirime verir.

    Bilgilendirme satırları (transkript, tool, hata) metin çıkışına devrediliyor: onların
    sesli karşılığı yok ve olsaydı da asistanın cevabının üstüne binerdi.
    """

    def __init__(self, player: AudioPlayer, notes: Output | None = None) -> None:
        self._player = player
        self._notes = notes if notes is not None else TextOutput()
        self.speaking = False

    async def state(self, state: State, turn_id: str | None) -> None:
        await self._notes.state(state, turn_id)

    async def transcript(self, turn_id: str, text: str) -> None:
        await self._notes.transcript(turn_id, text)

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        await self._notes.tool_running(turn_id, tool_name)

    async def announcement(self, turn_id: str, text: str) -> None:
        await self._notes.announcement(turn_id, text)

    async def reply(self, turn_id: str, text: str) -> None:
        """Cevabın metni de yazılıyor: sesi duyan kullanıcının okumaya ihtiyacı yok ama
        kaçırdığı ya da anlamadığı cümlenin uçbirimde durması ucuz."""
        await self._notes.reply(turn_id, text)

    async def chunk(self, turn_id: str, seq: int, data: bytes) -> None:
        self.speaking = True
        await self._player.play(data)

    async def end(self, turn_id: str) -> None:
        self.speaking = False

    async def cancelled(self, turn_id: str) -> None:
        self.speaking = False
        await self._player.stop()
        await self._notes.cancelled(turn_id)

    async def failed(self, code: str, message: str) -> None:
        await self._notes.failed(code, message)


async def listen(
    client: Client,
    source: AudioSource,
    output: VoiceOutput,
    *,
    settings: Settings | None = None,
    barge_in: bool = False,
) -> None:
    """Mikrofonu dinler, tamamlanmış segmenti sunucuya yollar (§7).

    Akış bitene kadar koşar; iptal edilmesi (`asyncio` yolu) yeterlidir.
    """
    endpointer = Endpointer(settings)
    async for frame in source.frames():
        if output.speaking and not barge_in:
            # Yarım dubleks: kendi sesimizi duymamak için (bkz. modül başlığı).
            endpointer.reset()
            continue
        was_speaking = endpointer.speaking
        segment = endpointer.feed(frame)
        started = not was_speaking and endpointer.speaking
        if output.speaking and barge_in and started and await client.interrupt():
            log.info("söz kesildi")
        if segment is not None:
            await client.send_speech(FORMAT, segment)
    leftover = endpointer.flush()
    if leftover is not None:
        await client.send_speech(FORMAT, leftover)
