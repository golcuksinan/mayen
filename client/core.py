"""İstemcinin protokol tarafı: el sıkışma, tur takibi, söz kesme (§13).

**Aktif turu istemci de biliyor.** Sunucu ölü turun çerçevesini kendi tarafında düşürüyor,
ama ağda ve tamponda yolu yarılamış parçalar kalabilir; §13 bu yüzden filtreyi *iki* tarafa
birden yazıyor. Kural: `turn_id` istemcinin bildiği aktif tur değilse parça çalınmaz.
`seq` tek başına yetmez — iptal edilmiş cevabın kırıntısı yeni cevabın ilk parçasından
ayırt edilemezdi.

**Turu açan `Transcript`.** Segment gönderildiğinde `turn_id` henüz yok: onu sunucu
üretiyor (§7, endpointing istemcide). Bu yüzden istemci segmentini yolladıktan sonra
transkripti bekler ve turu oradan öğrenir.

**Sıra atlaması düşürülmüyor, bildiriliyor.** Eksik `seq` kaybolmuş ses demek; parçayı
atmak kaybı ikiye katlardı. Sessiz kalmak da Kural 13'e aykırı — kayda geçiyor.

**Yön doğrulanıyor**, sunucunun yaptığının aynası: istemciden çıkması gereken bir çerçeve
tel üzerinden geri gelirse protokol hatasıdır, sessizce yok sayılmaz.

**Canlılık yoklaması otomatik değil.** `ping()` var ama zamanlayıcısı yok: aralık ölçülmüş
bir sayı değil ve §19'da yok. Bağlantının koptuğunu bugün okuma döngüsü söylüyor.
"""

import asyncio
import contextlib
import itertools
from collections.abc import AsyncIterator

from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from client.output import Output
from mayen.adapters.audio import AudioFormat
from mayen.obs.log import get_logger
from mayen.session.state import State
from mayen.transport.frames import (
    PROTOCOL_VERSION,
    Announcement,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ErrorFrame,
    Frame,
    Hello,
    Interrupt,
    Ping,
    Pong,
    Rejected,
    Reply,
    ServerFrame,
    SpeechSegment,
    StateChanged,
    TextSegment,
    ToolRunning,
    Transcript,
    Welcome,
)
from mayen.transport.wire import ProtocolError, decode, encode

log = get_logger(__name__)

_SERVER_FRAMES = (
    Welcome,
    Rejected,
    Transcript,
    StateChanged,
    ToolRunning,
    Reply,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ErrorFrame,
    Announcement,
    Pong,
)


class HandshakeError(Exception):
    """Sunucu bağlantıyı reddetti ya da beklenmedik bir cevap verdi (§13)."""


class Client:
    """Tek bir bağlantı. Okuma döngüsü `run()`, yazma tarafı çağıranın."""

    def __init__(
        self,
        socket: ClientConnection,
        device_id: str,
        output: Output,
        *,
        protocol_version: int = PROTOCOL_VERSION,
    ) -> None:
        self._socket = socket
        self._output = output
        self._version = protocol_version
        self.device_id = device_id
        self.state = State.IDLE
        self.active_turn: str | None = None
        #: Ölü turun düşen parçaları. Sıfır olmaması bir arıza değil — söz kesmenin
        #: normal sonucu; ölçülebilir olması §13'ün kuralının çalıştığının kanıtı.
        self.dropped = 0
        self._segments = itertools.count(1)
        self._expected_seq = 0

    async def handshake(self) -> Welcome:
        """Bağlantının ilk çerçevesi. Ret bir istisna: istemcinin devam edecek hâli yok."""
        await self._send(Hello(protocol_version=self._version, device_id=self.device_id))
        frame = await self._recv()
        if isinstance(frame, Rejected):
            raise HandshakeError(f"{frame.reason} (sunucu sürümü {frame.server_version})")
        if not isinstance(frame, Welcome):
            raise HandshakeError(f"El sıkışma cevabı beklenirken {frame.TYPE!r} geldi")
        return frame

    async def say(self, text: str) -> str:
        """Metin segmenti yollar (P1'in sahte STT yolu) ve `segment_id`'yi döndürür."""
        segment_id = self._next_segment_id()
        await self._send(TextSegment(segment_id=segment_id, text=text))
        return segment_id

    async def send_speech(self, audio_format: AudioFormat, data: bytes) -> str:
        """Tamamlanmış konuşma segmenti (§7). Mikrofon arka ucu geldiğinde çağıran o olur."""
        segment_id = self._next_segment_id()
        await self._send(SpeechSegment(segment_id=segment_id, format=audio_format, data=data))
        return segment_id

    async def interrupt(self) -> bool:
        """Aktif turu keser. Tur yoksa yollamaz: kapsam tek tur, kuyruğun tamamı değil."""
        turn_id = self.active_turn
        if turn_id is None:
            return False
        await self._send(Interrupt(turn_id=turn_id))
        return True

    async def ping(self) -> None:
        await self._send(Ping())

    async def run(self) -> None:
        """Okuma döngüsü. Bağlantı kapanınca sessizce biter, kayda geçer."""
        try:
            async for raw in self._socket:
                try:
                    frame = _server_frame(decode(raw))
                except ProtocolError as error:
                    # Sunucunun bozuk çerçeveye davranışının aynısı: bağlantıyı düşürmek
                    # bir sonraki çerçevenin de bozuk olacağını varsaymak olurdu.
                    log.info("bozuk çerçeve", error=str(error))
                    await self._output.failed("protocol", str(error))
                    continue
                try:
                    await self._handle(frame)
                except Exception as error:
                    # Çıkışın arızası bağlantıyı düşürmüyor ve **sessizce yutulmuyor**
                    # (Kural 13). Bozuk çerçevedeki kararın aynısı: bir çerçevenin
                    # başarısızlığı sonrakinin de başarısız olacağı anlamına gelmez.
                    # Yutulduğu sürüm görülmüştü: hoparlör bir parçada hata verince okuma
                    # döngüsü ölüyor, ekrana hiçbir şey düşmüyor ve istemci o andan sonra
                    # sessizce sağır kalıyordu — kullanıcı yazıyor, cevap gelmiyor.
                    log.exception("çerçeve işlenemedi", frame=frame.TYPE)
                    await self._output.failed("client", f"{frame.TYPE}: {error}")
        except ConnectionClosed:
            log.info("bağlantı kapandı", device_id=self.device_id)

    async def _handle(self, frame: ServerFrame) -> None:
        match frame:
            case StateChanged(state=state, turn_id=turn_id):
                self.state = state
                await self._output.state(state, turn_id)
            case Transcript(turn_id=turn_id, text=text):
                self.active_turn = turn_id
                self._expected_seq = 0
                await self._output.transcript(turn_id, text)
            case Announcement(turn_id=turn_id, text=text):
                # Kullanıcının açmadığı tur (§12). `Transcript`'in yaptığının aynısı:
                # turu açmasaydı §13'ün filtresi kendi sesini düşürürdü.
                self.active_turn = turn_id
                self._expected_seq = 0
                await self._output.announcement(turn_id, text)
            case ToolRunning(turn_id=turn_id, tool_name=tool_name):
                if self._belongs(turn_id):
                    await self._output.tool_running(turn_id, tool_name)
            case Reply(turn_id=turn_id, text=text):
                if self._belongs(turn_id):
                    await self._output.reply(turn_id, text)
            case AudioChunk(turn_id=turn_id, seq=seq, data=data):
                if not self._belongs(turn_id):
                    return
                if seq != self._expected_seq:
                    # Eksik parça kaybolmuş ses; atmak kaybı ikiye katlardı.
                    log.warning(
                        "sıra atlandı", turn_id=turn_id, expected=self._expected_seq, seq=seq
                    )
                self._expected_seq = seq + 1
                await self._output.chunk(turn_id, seq, data)
            case AudioEnd(turn_id=turn_id):
                if not self._belongs(turn_id):
                    return
                self.active_turn = None
                await self._output.end(turn_id)
            case Cancelled(turn_id=turn_id):
                if not self._belongs(turn_id):
                    return
                self.active_turn = None
                await self._output.cancelled(turn_id)
            case ErrorFrame(code=code, message=message):
                await self._output.failed(code, message)
            case Pong() | Welcome() | Rejected():
                # El sıkışma tekrarlanmaz; `Pong` yalnızca canlılık cevabı.
                log.info("beklenmeyen çerçeve", frame=frame.TYPE)

    def _belongs(self, turn_id: str) -> bool:
        """§13'ün filtresi: bilmediğim turun parçası çalınmaz."""
        if turn_id == self.active_turn:
            return True
        self.dropped += 1
        log.info("ölü turun çerçevesi düştü", turn_id=turn_id, active=self.active_turn)
        return False

    def _next_segment_id(self) -> str:
        """Bağlantı içinde benzersiz olması yeterli; sunucu `turn_id`'yi kendisi üretiyor."""
        return f"{self.device_id}-{next(self._segments)}"

    async def _send(self, frame: Frame) -> None:
        await self._socket.send(encode(frame))

    async def _recv(self) -> ServerFrame:
        return _server_frame(decode(await self._socket.recv()))


@contextlib.asynccontextmanager
async def connect(url: str, device_id: str, output: Output) -> AsyncIterator[Client]:
    """Bağlanır, el sıkışır, okuma döngüsünü arka planda koşturur ve çıkışta kapatır."""
    socket = await ws_connect(url)
    client = Client(socket, device_id, output)
    try:
        await client.handshake()
    except BaseException:
        await socket.close()
        raise
    reader = asyncio.create_task(client.run(), name=f"read:{device_id}")
    try:
        yield client
    finally:
        await socket.close()
        reader.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reader


def _server_frame(frame: Frame) -> ServerFrame:
    """Yön doğrulaması; sunucudaki kontrolün aynası."""
    if not isinstance(frame, _SERVER_FRAMES):
        raise ProtocolError(f"{frame.TYPE!r} istemciden sunucuya gider, tersi değil")
    return frame
