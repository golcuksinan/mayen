"""WebSocket sunucusu (§13). P3'ün bıraktığı boşluk: sözleşme vardı, konuşan taraf yoktu.

Sunucunun tamamı üç parçadan ibaret ve hiçbiri turu bilmiyor:

- `Connection` — tek istemci soketi. El sıkışmayı yapar, gelen çerçeveleri oturuma
  çevirir, giden çerçeveleri `SendQueue`'dan tek bir yazıcı görevle akıtır.
- `Connections` — açık bağlantıların defteri. Yayın (`broadcast`) ve tura yönlendirme
  burada.
- `FrameSink` — `session.SessionSink` **ve** `turn.runner.TurnSink`'in tek uygulaması:
  alt katmanların çerçeve görmeden duyurduğu her şeyi çerçeveye çevirir.

**Neden tek sink iki protokolü birden uyguluyor:** ikisi de "dışarıya duyur" demek ve
duyurulan yer aynı sokettir. İki nesneye bölmek, aynı bağlantı defterini iki yerden
tutmak olurdu.

**`FrameSink` oturumu ikinci fazda alıyor** (`attach`). Gerçek bir döngü var: `Session`
kurulurken sink'i istiyor, sink de turun sahibini bulmak için oturumu. Döngüyü bir
`Protocol` kıramaz — iki taraf da somut olarak birbirinin *örneğini* istiyor, arayüzünü
değil. İkinci faz bunu görünür kılıyor; kapalı bir kurucu sarmalayıcı yalnızca gizlerdi.

**Turun sesi yalnızca konuşan cihaza gider, durum ise herkese.** Durum sistem geneli:
aynı anda tek tur var (§5), yani `KONUŞUYOR` ikinci cihaz için de doğru bir bilgi. Ses,
transkript ve tool bildirimi ise o turun cihazına ait. Turun cihazı `session.active_turn`
üzerinden okunur — turun sahibini zaten orası tutuyor ve tur bitmeden temizlenmiyor.
Eşleşmeyen `turn_id` **ölü turun geç kalmış çerçevesidir** (§13 bunu açıkça bekliyor):
düşürülür ve kayda geçer, sessizce yok sayılmaz.

**Yön doğrulanır.** Tel üzerinde her çerçeve çözülebilir, ama sunucudan istemciye giden
bir çerçeve istemciden gelemez. Doğrulanmazsa istemci `Welcome` yollayıp sunucunun
kendi sözlüğünü karşısına koyabilirdi; sessizce yok saymak Kural 13'e aykırı.
"""

import asyncio
import contextlib
from collections.abc import Callable, Iterable

from websockets.asyncio.server import Server as WebSocketServer
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from mayen.adapters.audio import Audio, AudioFormat
from mayen.obs.log import get_logger
from mayen.session.actor import Segment, Session
from mayen.session.state import State
from mayen.transport.frames import (
    PROTOCOL_VERSION,
    Announcement,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ClientFrame,
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
)
from mayen.transport.handshake import negotiate
from mayen.transport.queue import DEFAULT_MAXSIZE, SendQueue
from mayen.transport.wire import ProtocolError, decode, encode

log = get_logger(__name__)

_CLIENT_FRAMES = (Hello, SpeechSegment, TextSegment, Interrupt, Ping)


class Connection:
    """Tek istemci soketi: bir gönderme kuyruğu ve onu boşaltan tek yazıcı görev.

    Yazıcının tek olması sıranın garantisi (§6): iki görev aynı sokete yazsaydı sıra
    yalnızca zamanlamaya kalırdı.
    """

    def __init__(
        self, socket: ServerConnection, device_id: str, *, queue_maxsize: int = DEFAULT_MAXSIZE
    ) -> None:
        self.device_id = device_id
        self._socket = socket
        self._queue = SendQueue(queue_maxsize)
        self._writer: asyncio.Task[None] | None = None

    async def send(self, frame: ServerFrame) -> None:
        """Kuyruğa koyar. Kuyruk doluysa **bekler**, çerçeve düşmez (§13)."""
        await self._queue.put(frame)

    async def send_now(self, frame: ServerFrame) -> None:
        """Kuyruğu atlayarak yazar. Yalnızca el sıkışma cevabı için: yazıcı görev henüz
        yok ve `Rejected`'ın ardından bağlantı kapanacak."""
        await self._socket.send(encode(frame))

    async def cancel_turn(self, turn_id: str) -> int:
        return await self._queue.cancel_turn(turn_id)

    def start(self) -> None:
        if self._writer is None:
            self._writer = asyncio.create_task(self._pump(), name=f"send:{self.device_id}")

    async def stop(self) -> None:
        if self._writer is None:
            return
        self._writer.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._writer
        self._writer = None

    async def _pump(self) -> None:
        while True:
            frame = await self._queue.get()
            try:
                await self._socket.send(encode(frame))
            except ConnectionClosed:
                # Bağlantı kapandı: okuma tarafı da bitecek ve `stop()` bu görevi
                # toplayacak. Kural 13 gereği sessiz değil — kaç çerçevenin yazılamadan
                # kaldığı ölçülebilir olmalı.
                log.info(
                    "bağlantı kapalı, gönderilemedi",
                    device_id=self.device_id,
                    frame=frame.TYPE,
                    pending=len(self._queue),
                )
                return


class Connections:
    """Açık bağlantıların defteri."""

    def __init__(self) -> None:
        self._by_device: dict[str, Connection] = {}

    def get(self, device_id: str) -> Connection | None:
        return self._by_device.get(device_id)

    def add(self, connection: Connection) -> Connection | None:
        """Bağlantıyı deftere yazar; aynı cihazın eskisi varsa onu döndürür.

        Yerine koymak reddetmekten iyi: kopan bir bağlantının soketi hemen toplanmaz ve
        yeniden bağlanan istemci "bu cihaz zaten bağlı" diye reddedilirdi.
        """
        previous = self._by_device.get(connection.device_id)
        self._by_device[connection.device_id] = connection
        return previous

    def remove(self, connection: Connection) -> None:
        # Kimlik kontrolü şart: yerine yeni bir bağlantı geçtiyse eskisinin kapanışı
        # yenisini defterden silmemeli.
        if self._by_device.get(connection.device_id) is connection:
            del self._by_device[connection.device_id]

    async def broadcast(self, frame: ServerFrame) -> None:
        """Sistem geneli bir çerçeveyi tüm bağlantılara koyar.

        Eşzamanlı, çünkü kuyruğu dolu tek bir istemci diğerlerinin bildirimini
        sırasında bekletmemeli. Yine de yavaş istemci **herkesi** yavaşlatır: kuyruk
        dolduğunda beklemek §13'ün kuralı ve düşürmek seçenek değil.
        """
        if not self._by_device:
            return
        await asyncio.gather(*(conn.send(frame) for conn in tuple(self._by_device.values())))

    def all(self) -> Iterable[Connection]:
        return tuple(self._by_device.values())


class FrameSink:
    """`SessionSink` + `TurnSink`: alt katmanların duyurduğu her şeyin çerçeveye çevrildiği
    tek yer. Modül başlığındaki yönlendirme kuralları burada uygulanıyor."""

    def __init__(self, connections: Connections) -> None:
        self._connections = connections
        self._session: Session | None = None

    def attach(self, session: Session) -> None:
        """Kurulumun ikinci fazı; gerekçesi modül başlığında."""
        self._session = session

    # --- session.SessionSink ------------------------------------------------------------

    async def state_changed(self, state: State, turn_id: str | None) -> None:
        await self._connections.broadcast(StateChanged(state=state, turn_id=turn_id))

    async def turn_cancelled(self, turn_id: str) -> None:
        """Önce o tura ait bekleyen çerçeveler düşer, **sonra** `Cancelled` yazılır.

        Sıra tersine olsaydı istemci iptali duyduktan sonra ölü turun kuyrukta bekleyen
        parçalarını almaya devam ederdi. Düşürme tüm bağlantılarda yapılıyor: tur tek de
        olsa, kuyruğunda o `turn_id` bulunan başka bir bağlantı kalmamalı.
        """
        for connection in self._connections.all():
            dropped = await connection.cancel_turn(turn_id)
            if dropped:
                log.info("iptalde düşen çerçeve", turn_id=turn_id, dropped=dropped)
        await self._send(turn_id, Cancelled(turn_id=turn_id))

    async def turn_failed(self, turn_id: str, error: str) -> None:
        """§14'ün ayrı kanalı: hata turun cihazına gider, yayına değil — patlayan tur
        ikinci cihazın işi değil."""
        log.info("tur başarısız, istemciye bildiriliyor", turn_id=turn_id, error=error)
        await self._send(turn_id, ErrorFrame(code="turn_failed", message=error))

    # --- turn.runner.TurnSink -----------------------------------------------------------

    async def transcript(self, turn_id: str, segment_id: str, text: str) -> None:
        await self._send(turn_id, Transcript(segment_id=segment_id, turn_id=turn_id, text=text))

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        await self._send(turn_id, ToolRunning(turn_id=turn_id, tool_name=tool_name))

    async def reply(self, turn_id: str, text: str) -> None:
        await self._send(turn_id, Reply(turn_id=turn_id, text=text))

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        await self._send(
            turn_id, AudioChunk(turn_id=turn_id, seq=seq, format=audio_format, data=data)
        )

    async def audio_end(self, turn_id: str) -> None:
        await self._send(turn_id, AudioEnd(turn_id=turn_id))

    # --- scheduler.announce.ProactiveSink ------------------------------------------------

    def connected(self) -> frozenset[str]:
        return frozenset(connection.device_id for connection in self._connections.all())

    async def announcement(self, device_id: str, turn_id: str, text: str) -> None:
        await self._to_device(device_id, Announcement(turn_id=turn_id, text=text))

    async def announcement_chunk(
        self, device_id: str, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        await self._to_device(
            device_id, AudioChunk(turn_id=turn_id, seq=seq, format=audio_format, data=data)
        )

    async def announcement_end(self, device_id: str, turn_id: str) -> None:
        await self._to_device(device_id, AudioEnd(turn_id=turn_id))

    # --- yönlendirme --------------------------------------------------------------------

    async def _to_device(self, device_id: str, frame: ServerFrame) -> None:
        """Adı verilen cihaza yollar. Turun yolundan ayrı: proaktif bildirimin turu yok,
        yani `active_turn`'e bakan yönlendirme onu düşürürdü (§12)."""
        connection = self._connections.get(device_id)
        if connection is None:
            # Bildirim seslendirilirken cihaz koptu. Kalan parçalar da düşecek; sessiz
            # kalmak, duyulmadığı hiç bilinmeyen bir hatırlatıcı demek olurdu (Kural 13).
            log.info("bildirimin cihazı bağlı değil", device_id=device_id, frame=frame.TYPE)
            return
        await connection.send(frame)

    async def _send(self, turn_id: str, frame: ServerFrame) -> None:
        connection = self._route(turn_id)
        if connection is None:
            return
        await connection.send(frame)

    def _route(self, turn_id: str) -> Connection | None:
        if self._session is None:
            raise RuntimeError("FrameSink oturuma bağlanmadı: `attach()` çağrılmalı")
        turn = self._session.active_turn
        if turn is None or turn.turn_id != turn_id:
            log.info(
                "ölü turun çerçevesi düştü",
                turn_id=turn_id,
                active=turn.turn_id if turn else None,
            )
            return None
        connection = self._connections.get(turn.segment.device_id)
        if connection is None:
            # Cihaz tur ortasında koptu. Turu öldürmek gerekmez — iptal istemciden gelir
            # ya da tur biter; ama sessiz kalmak, kaybolan sesi ölçülemez yapardı.
            log.info(
                "turun cihazı bağlı değil", turn_id=turn_id, device_id=turn.segment.device_id
            )
        return connection


class Server:
    """Soketleri karşılayan taraf. Turu bilmez: gelen çerçeveyi oturuma çevirir, o kadar."""

    def __init__(
        self,
        session: Session,
        connections: Connections,
        *,
        queue_maxsize: int = DEFAULT_MAXSIZE,
        on_connected: Callable[[str], None] | None = None,
    ) -> None:
        self._session = session
        self._connections = connections
        self._queue_maxsize = queue_maxsize
        #: Bir cihaz bağlandığında haber verilen taraf — bugün tek kullanıcısı, bekleyen
        #: proaktif bildirimi ilk bağlanan cihaza veren `Announcer` (§12). Senkron,
        #: bilerek: el sıkışmadan hemen sonra beklemek, o bağlantıdan gelen çerçeveleri
        #: (söz kesme dâhil) okumayı geciktirirdi.
        self._on_connected = on_connected

    async def serve(self, host: str, port: int) -> WebSocketServer:
        """Dinlemeye başlar ve sunucuyu döndürür. Kapatmak çağıranın işi."""
        return await serve(self.handle, host, port)

    async def handle(self, socket: ServerConnection) -> None:
        """Tek bağlantının ömrü: el sıkışma, okuma döngüsü, kapanış."""
        connection = await self._greet(socket)
        if connection is None:
            return
        previous = self._connections.add(connection)
        if previous is not None:
            log.info("cihazın önceki bağlantısı düştü", device_id=connection.device_id)
            await previous.stop()
        connection.start()
        if self._on_connected is not None:
            self._on_connected(connection.device_id)
        try:
            await self._read(socket, connection)
        finally:
            self._connections.remove(connection)
            await connection.stop()

    async def _greet(self, socket: ServerConnection) -> Connection | None:
        """El sıkışma (§13). Ret bir istisna değil `Rejected` çerçevesi."""
        try:
            raw = await socket.recv()
        except ConnectionClosed:
            return None
        try:
            frame = _client_frame(decode(raw))
        except ProtocolError as error:
            await socket.send(encode(_rejected(str(error))))
            await socket.close()
            return None

        answer = negotiate(frame)
        if isinstance(answer, Rejected):
            log.info("el sıkışma reddedildi", reason=answer.reason)
            await socket.send(encode(answer))
            await socket.close()
            return None

        if not isinstance(frame, Hello):  # pragma: no cover - `negotiate` onu reddetmişti
            raise ProtocolError(f"El sıkışma beklenirken {frame.TYPE!r} geldi")
        if not frame.device_id:
            await socket.send(encode(_rejected("Cihaz kimliği boş olamaz")))
            await socket.close()
            return None

        connection = Connection(socket, frame.device_id, queue_maxsize=self._queue_maxsize)
        await connection.send_now(answer)
        return connection

    async def _read(self, socket: ServerConnection, connection: Connection) -> None:
        try:
            async for raw in socket:
                try:
                    frame = _client_frame(decode(raw))
                except ProtocolError as error:
                    # Bozuk çerçeve bağlantıyı kapatmıyor: tek bir çerçevenin bozuk olması
                    # bir sonrakinin de bozuk olacağı anlamına gelmez ve turun ortasında
                    # bağlantıyı düşürmek, hatayı bildirmekten pahalı. Hata ayrı kanaldan
                    # gidiyor (§14) ve sessiz değil (Kural 13).
                    log.info("bozuk çerçeve", device_id=connection.device_id, error=str(error))
                    await connection.send(ErrorFrame(code="protocol", message=str(error)))
                    continue
                try:
                    await self._dispatch(frame, connection)
                except Exception as error:
                    # Geçerli bir çerçevenin işlenmesi patladı — örneğin §5'in tablosunda
                    # tanımlı olmayan bir geçiş. Bağlantıyı düşürmek istemcinin gördüğü
                    # tek şeyi (soket kapandı) hatanın kendisinden fakir yapardı; hata
                    # ayrı kanaldan bildiriliyor (§14) ve kayda geçiyor (Kural 13).
                    log.exception(
                        "çerçeve işlenemedi",
                        device_id=connection.device_id,
                        frame=frame.TYPE,
                    )
                    await connection.send(
                        ErrorFrame(code=type(error).__name__, message=str(error))
                    )
        except ConnectionClosed:
            log.info("bağlantı kapandı", device_id=connection.device_id)

    async def _dispatch(self, frame: ClientFrame, connection: Connection) -> None:
        match frame:
            case Ping():
                await connection.send(Pong())
            case Hello():
                # El sıkışma bağlantının **ilk** çerçevesi (§13); ikincisi sürüm
                # pazarlığını turun ortasına taşımak olurdu.
                await connection.send(
                    ErrorFrame(code="protocol", message="El sıkışma tekrarlanamaz")
                )
            case Interrupt(turn_id=turn_id):
                await self._session.interrupt(turn_id)
            case SpeechSegment(segment_id=segment_id, format=audio_format, data=data):
                await self._submit(
                    connection, segment_id, Audio(format=audio_format, data=data)
                )
            case TextSegment(segment_id=segment_id, text=text):
                await self._submit(connection, segment_id, text)

    async def _submit(self, connection: Connection, segment_id: str, payload: object) -> None:
        """Segmenti cihazın aktörüne bırakır ve **beklemez**.

        Beklemek okuma döngüsünü turun süresi boyunca durdururdu; söz kesme de o döngüden
        geliyor, yani turu iptal edecek çerçeve turun bitmesini beklerdi (Kural 12).
        """
        segment = Segment(
            segment_id=segment_id, device_id=connection.device_id, payload=payload
        )
        await self._session.actor(connection.device_id).submit(segment)


def _client_frame(frame: Frame) -> ClientFrame:
    """Yönü doğrular; gerekçesi modül başlığında."""
    if not isinstance(frame, _CLIENT_FRAMES):
        raise ProtocolError(f"{frame.TYPE!r} sunucudan istemciye gider, tersi değil")
    return frame


def _rejected(reason: str) -> Rejected:
    return Rejected(reason=reason, server_version=PROTOCOL_VERSION)
