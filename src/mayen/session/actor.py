"""Oturum aktörü (§5).

Oturumun bitişi yoktur; sistem açık olduğu sürece tek bir sürekli konuşma akışı vardır.
Bu yüzden buradaki `Session` "bir oturum nesnesi" değil, **süreç boyunca yaşayan tek
koordinatör**tür.

**Cihaz başına aktör, ama aktif tur tutamacı global.** İkisi ayrı şeyler: her cihazın
kendi kuyruğu var, çünkü bir cihazın segmenti başka bir cihazın bağlantı olaylarını
bekletmemeli. Ama tur global bir kilidin arkasında koşar — sistemde aynı anda tek tur
vardır (§5), tek GPU ve tek konuşma akışı olduğu için. İkinci cihazdan gelen segment
sıraya girer; `asyncio.Lock` bekleyenleri geliş sırasında uyandırır.

**Turun kendisi burada koşmuyor.** Bu paket saf mantık, I/O yok: aktör bir `TurnRunner`
çağırır ve turun bildirdiği olaylarla durum tablosunu yürütür. Gerçek koşucu `turn`
katmanında doğacak (`session → turn` §4'e uygun), testlerde sahtesi verilir.

**Durum bildirimi de tersine bağımlılık.** `StateChanged` çerçevesini yazan `transport`,
`session`'ın *üstünde*; aktör onu import edemez. Bu yüzden aktör durumu bir `SessionSink`'e
duyurur, çerçeveye çeviren taraf sinki uygular — `obs`/`TraceSink` kalıbının aynısı.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol

from mayen.data import clock
from mayen.obs.log import get_logger
from mayen.session.state import Event, State, is_closed, transition

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Segment:
    """Aktöre ulaşan tamamlanmış segment (§7).

    `payload` bilinçli olarak opak: endpointing istemcide çalışır, sunucu segmenti tekrar
    tespit etmez ve aktör içeriğine hiç bakmaz — sesi çözen de metni okuyan da koşucudur.
    """

    segment_id: str
    device_id: str
    payload: object


@dataclass(slots=True)
class ActiveTurn:
    """Koşan turun tutamacı. Sistemde aynı anda en fazla bir tane vardır."""

    turn_id: str
    segment: Segment
    #: Turu koşan görev. İptal (Kural 12) bunun üzerinden yürür — tutamağın tek sahibi
    #: olması, iptalin kapsamının **tur** olmasını yapısal olarak garanti eder. Ayrı bir
    #: iptal jetonu yok: asyncio'nunki zaten var, ikincisi unutulacak ikinci yol demek.
    task: asyncio.Task[None] | None = field(default=None, repr=False)
    #: "Konuşmayı kes, ama turu öldürme." Yalnızca `ONAY_BEKLIYOR`'da kullanılır (B3):
    #: onay cümlesi okunurken söze girilirse ses durur, plan yaşar.
    speech_stopped: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    #: Turun söz kesme yüzünden bittiğini işaretler. `CancelledError`'ın bu turun kendi
    #: iptali mi yoksa dışarıdan gelen bir kapatma mı olduğunu ayırt etmenin tek yolu.
    cancelled: bool = False
    #: Tur **kapalı** bir durumdayken gelen segmentler (§5). Yeni tur açmazlar ve ajana
    #: ulaşmazlar; onları okuyacak olan koşucudur — `ONAY_BEKLIYOR`'da onay çözümleyicisi,
    #: `KAYIT`'ta kayıt akışı.
    segments: asyncio.Queue[Segment] = field(default_factory=asyncio.Queue, repr=False)


class TurnRunner(Protocol):
    """Bir turu koşan taraf. `report` ile ilerlemesini bildirir; durumu aktör yürütür."""

    async def run(
        self, turn: ActiveTurn, report: Callable[[Event], Awaitable[None]]
    ) -> None: ...


class SessionSink(Protocol):
    """Aktörün dışarıya duyurduğu şeyler (§13). `transport` uygular, `session` bilmez."""

    async def state_changed(self, state: State, turn_id: str | None) -> None: ...

    async def turn_cancelled(self, turn_id: str) -> None: ...


class DeviceActor:
    """Tek cihazın kuyruğu ve görevi. Varlık (presence) zamanını da bu tutar (§12)."""

    def __init__(self, device_id: str, session: "Session") -> None:
        self.device_id = device_id
        self._session = session
        self._inbox: asyncio.Queue[Segment] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        #: O cihazdan gelen **son kullanıcı etkileşiminin** zamanı. Zamanlanmış bildirim
        #: en son kullanılan cihaza yönlendirilirken buna bakılır (§12).
        self.last_interaction: str | None = None

    async def submit(self, segment: Segment) -> None:
        """Segmenti kuyruğa koyar. Sıra global kilidin arkasında beklenir, burada değil."""
        self.last_interaction = clock.now()
        await self._inbox.put(segment)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name=f"actor:{self.device_id}")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _loop(self) -> None:
        while True:
            segment = await self._inbox.get()
            try:
                await self._session.deliver(segment)
            except Exception:
                # Kural 13: bir turun patlaması aktörü sessizce öldürmez, kayda düşer ve
                # sıradaki segment işlenmeye devam eder.
                log.exception("tur başarısız", device_id=self.device_id)
            finally:
                self._inbox.task_done()


class Session:
    """Süreç boyunca yaşayan koordinatör: cihaz aktörleri, global tur kilidi, durum."""

    def __init__(self, runner: TurnRunner, sink: SessionSink) -> None:
        self._runner = runner
        self._sink = sink
        self._actors: dict[str, DeviceActor] = {}
        # Aynı anda tek tur — kapsamı global (§5), aktör başına değil.
        self._turn_lock = asyncio.Lock()
        self._turn_counter = 0
        self.state = State.IDLE
        self.active_turn: ActiveTurn | None = None

    def actor(self, device_id: str) -> DeviceActor:
        """Cihazın aktörünü döner, yoksa kurar ve başlatır. Kimliksiz cihaz yok (§5)."""
        if not device_id:
            raise ValueError("Cihaz kimliği zorunludur")
        actor = self._actors.get(device_id)
        if actor is None:
            actor = DeviceActor(device_id, self)
            actor.start()
            self._actors[device_id] = actor
        return actor

    async def close(self) -> None:
        for actor in self._actors.values():
            await actor.stop()
        self._actors.clear()

    async def deliver(self, segment: Segment) -> None:
        """Gelen segmentin gideceği yeri seçer. Aktörün kuyruğundan çıkan her segment
        buradan geçer.

        **Kapalı durumda yeni tur açılmaz** (§5): `ONAY_BEKLIYOR` ve `KAYIT` sırasında
        gelen metin ajan katmanına *hiç* ulaşmaz, koşan turun kendi kuyruğuna girer.
        Sıraya alıp turun bitmesini beklemek de olmazdı: onay bekleyen tur zaten o
        segmenti bekliyor, yani sistem kendi kendini kilitlerdi.
        """
        turn = self.active_turn
        if turn is not None and is_closed(self.state):
            await turn.segments.put(segment)
            return
        await self.run_turn(segment)

    async def run_turn(self, segment: Segment) -> None:
        """Bir segmenti tura çevirir. Global kilit yüzünden turlar sıraya girer."""
        async with self._turn_lock:
            turn = ActiveTurn(turn_id=self._next_turn_id(), segment=segment)
            self.active_turn = turn
            # Durum, koşucu başlamadan **önce** yürütülür: sonra yürütülseydi koşucunun
            # ilk olayı `COZUMLUYOR`'a geçişten önce gelebilirdi.
            await self._apply(Event.SEGMENT_ALINDI)
            # Koşucu kendi görevinde koşar; iptalin tutunacak bir yeri olması için.
            turn.task = asyncio.create_task(
                self._runner.run(turn, self._apply), name=f"turn:{turn.turn_id}"
            )
            try:
                await turn.task
            except asyncio.CancelledError:
                if not turn.cancelled:
                    # Bu iptal bu tura ait değil — süreç kapanıyor. Yutmak, kapanışı
                    # bekleyen tarafın sonsuza kadar beklemesi demek olurdu.
                    raise
            except BaseException:
                # Patlayan tur sistemi kendi durumunda bırakmaz: bir sonraki segment
                # `IDLE` beklediği için, aksi halde ikinci bir hata olarak geri gelirdi.
                await self._reset()
                raise
            finally:
                self.active_turn = None

    async def interrupt(self, turn_id: str) -> None:
        """Söz kesme (§5, §12). Kapsamı **tek tur**, giden kuyruğun tamamı değil.

        `KONUSUYOR`'da tur iptal edilir. `ONAY_BEKLIYOR`'da ise yalnızca ses durur:
        durum değişmez ve bekleyen plan yaşar (B3) — sonraki segment onay çözümleyicisine
        gider. Tablonun tanımlamadığı bir durumda gelen söz kesme `InvalidTransitionError`
        yükseltir; §5 onu tanımlamıyor ve varsayımla tanımlamak açık bir maddeyi kapatmak
        olurdu (Kural 13).
        """
        turn = self.active_turn
        if turn is None or turn.turn_id != turn_id:
            # Ölü turun geç kalmış çerçevesi (§13). Beklenen bir durum, hata değil —
            # ama sessiz de değil: iptal sonrası trafiğin ölçülebilmesi gerekiyor.
            log.info(
                "ilgisiz söz kesme", turn_id=turn_id, active=turn.turn_id if turn else None
            )
            return

        # Önce tablo: tanımsız bir durumda hiçbir şey iptal edilmeden yükselmeli.
        await self._apply(Event.SOZ_KESILDI)
        turn.speech_stopped.set()
        if self.state is State.ONAY_BEKLIYOR:
            return  # plan yaşıyor; turu öldürmüyoruz

        turn.cancelled = True
        if turn.task is not None:
            turn.task.cancel()
        # O tura ait bekleyen çerçeveleri düşürmek çağıranın işi (`SendQueue.cancel_turn`):
        # kuyruk `transport`'ta ve `session` onu import edemez (§4).
        await self._sink.turn_cancelled(turn_id)

    def _next_turn_id(self) -> str:
        # `turn_id`'yi sunucu üretir (§13): gelen segment henüz bir tura ait değil.
        self._turn_counter += 1
        return f"t{self._turn_counter}"

    async def _reset(self) -> None:
        """Durumu tabloya sormadan `IDLE`'a çeker. Yalnızca turun başarısız bittiği yol."""
        self.state = State.IDLE
        turn_id = self.active_turn.turn_id if self.active_turn else None
        await self._sink.state_changed(self.state, turn_id)

    async def _apply(self, event: Event) -> None:
        """Olayı tabloya uygular ve yeni durumu duyurur. Tanımsız çift yükselir (Kural 13)."""
        self.state = transition(self.state, event)
        turn_id = self.active_turn.turn_id if self.active_turn else None
        await self._sink.state_changed(self.state, turn_id)
