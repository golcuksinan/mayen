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
çağırır ve turun bildirdiği ilerlemeyi (`turn.report.TurnReport`) durum tablosuna çevirir.
Gerçek koşucu `turn` katmanında (`session → turn` §4'e uygun), testlerde sahtesi verilir.

**Durum bildirimi de tersine bağımlılık.** `StateChanged` çerçevesini yazan `transport`,
`session`'ın *üstünde*; aktör onu import edemez. Bu yüzden aktör durumu bir `SessionSink`'e
duyurur, çerçeveye çeviren taraf sinki uygular — `obs`/`TraceSink` kalıbının aynısı.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Protocol

from mayen.data import clock
from mayen.obs.log import get_logger
from mayen.obs.trace import new_turn_id
from mayen.session.state import Event, State, is_closed, transition
from mayen.turn.report import TurnReport

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

    async def run(self, turn: ActiveTurn, report: TurnReport) -> None: ...


class _Report:
    """Turun dilini §5'in olaylarına çeviren tek yer.

    Çeviri burada, çünkü tablonun sahibi bu katman: `turn` `session`'ı import edemez (§4) ve
    olay sözlüğünü oraya kopyalamak, elle bakımı yapılan ikinci bir sözlük demek olurdu.
    """

    def __init__(self, apply: Callable[[Event], Awaitable[None]]) -> None:
        self._apply = apply

    async def understood(self) -> None:
        await self._apply(Event.COZUMLEME_BITTI)

    async def speaking(self) -> None:
        await self._apply(Event.ILK_SES_HAZIR)

    async def spoke(self) -> None:
        await self._apply(Event.SES_BITTI)

    async def answer_empty(self) -> None:
        await self._apply(Event.YANIT_BOS)

    async def approval_needed(self) -> None:
        await self._apply(Event.ONAY_GEREKLI)

    async def approved(self) -> None:
        await self._apply(Event.ONAY_VERILDI)

    async def refused(self) -> None:
        await self._apply(Event.ONAY_REDDEDILDI)

    async def approval_timed_out(self) -> None:
        await self._apply(Event.ONAY_ZAMAN_ASIMI)

    async def registration_needed(self) -> None:
        await self._apply(Event.KAYIT_GEREKLI)

    async def registration_done(self) -> None:
        await self._apply(Event.KAYIT_BITTI)


class SessionSink(Protocol):
    """Aktörün dışarıya duyurduğu şeyler (§13). `transport` uygular, `session` bilmez."""

    async def state_changed(self, state: State, turn_id: str | None) -> None: ...

    async def turn_cancelled(self, turn_id: str) -> None: ...

    async def turn_failed(self, turn_id: str, error: str) -> None:
        """Tur patladı (§14). Kayda düşmek yetmiyor: konuşan taraf sessizlikle hatayı
        ayırt edemez — sesin hiç gelmemesi de bir cevaptır ve yanlış olanıdır."""
        ...


class IdleWork(Protocol):
    """Boşta koşan, tur geldiğinde çekilen işler (Kural 11, §11.3'ün B4 maddesi).

    Aktör bunun **ne** olduğunu bilmiyor ve bilmemeli: bildiği tek şey turun ne zaman
    kuyruğa girdiği ve ne zaman bittiği. Uygulaması `memory.BackgroundWork`.

    İki yöntem de senkron: iptalin tamamlanmasını beklemek, tam da beklenmemesi gereken
    şeyi turun önüne koymak olurdu.
    """

    def turn_started(self) -> None: ...

    def turn_finished(self) -> None: ...


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
        """Segmenti kuyruğa koyar. Sıra global kilidin arkasında beklenir, burada değil.

        Arka plan işi **burada** çekiliyor, turun başladığı yerde değil (Kural 11, B4):
        §11.3 "tur kuyruğa girdiği anda" diyor ve aradaki fark ölçülebilir — kilidi
        beklerken iptal edilmemiş bir özetleme, ilk token'ı hâlâ bekletiyor olurdu.
        """
        self.last_interaction = clock.now()
        self._session.work_arrived()
        routed = self._session.route(segment)
        log.info("segment geldi", text=segment.payload, state=self._session.state, routed=routed)
        # Yönlendirme **burada**, kuyruğa girmeden: kapalı durumdaki turun beklediği
        # segment, o turu bekleyen kuyruğun arkasına geçemez (`Session.route`).
        if self._session.route(segment):
            return
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

    def __init__(
        self, runner: TurnRunner, sink: SessionSink, *, idle: IdleWork | None = None
    ) -> None:
        self._runner = runner
        self._sink = sink
        self._idle = idle
        self._actors: dict[str, DeviceActor] = {}
        # Aynı anda tek tur — kapsamı global (§5), aktör başına değil.
        self._turn_lock = asyncio.Lock()
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

    def work_arrived(self) -> None:
        """Kuyruğa iş girdi: boştaki arka plan işi çekilir (Kural 11)."""
        if self._idle is not None:
            self._idle.turn_started()

    def recent_devices(self) -> tuple[str, ...]:
        """Cihazlar, en son etkileşimden en eskiye. Zamanlanmış bildirimin hedefi buradan
        seçilir (§5 varlık takibi, §12).

        Hiç etkileşimi olmayan cihaz listenin sonunda: bağlanmış ama hiç konuşulmamış bir
        cihaz, konuşulmuş olanın önüne geçmemeli. **Bağlı olup olmadıklarına bakmıyor** —
        bağlantı defteri `transport`'ta ve `session` onu göremez (§4); burası yalnızca
        sırayı söylüyor, seçimi yapan taraf kendi defterine bakıyor.
        """
        actors = sorted(
            self._actors.values(),
            key=lambda actor: (
                actor.last_interaction is not None,
                actor.last_interaction or "",
            ),
            reverse=True,
        )
        return tuple(actor.device_id for actor in actors)

    @contextlib.asynccontextmanager
    async def exclusive(self) -> AsyncIterator[None]:
        """Turun global kilidini dışarıya açar (§12).

        Proaktif ses **bir tur değil**: §5'in tablosunda karşılığı yok ve burası ona durum
        yürütmüyor. Ama "kullanıcı ya da asistan konuşurken araya girmez, sıraya girer"
        demek tam olarak bu kilidi almak demek — kilidi almadan konuşmak, iki sesin aynı
        hoparlörde üst üste binmesi olurdu.
        """
        async with self._turn_lock:
            yield

    async def close(self) -> None:
        for actor in self._actors.values():
            await actor.stop()
        self._actors.clear()

    def route(self, segment: Segment) -> bool:
        """Kapalı durumdaki turun kendi kuyruğuna koyar; koyduysa `True` döner.

        **Eşzamanlı değil ve olmamalı.** Karar segment *geldiği anda* verilmek zorunda,
        aktörün kuyruğundan çıktığı anda değil — çünkü aktör o sırada koşan turu
        bekliyor olabilir. Kilitlenme tam buydu ve sahibin makinesinde görüldü
        (2026-08-16): tur `ONAY_BEKLIYOR`'da segment bekliyor, `DeviceActor._loop` o
        turu bekliyor, sahibin yazdığı "evet" ikisinin arasında `_inbox`'ta duruyor.
        Onay her seferinde zaman aşımına düştü ve sahip mesajının gitmediğini sandı —
        haklıydı, gitmemişti.

        Testler `deliver()`'ı doğrudan çağırdığı için aktör döngüsünü hiç geçmiyordu;
        `tests/test_session_actor.py` artık onay yolunu aktörden geçirerek koşuyor.
        """
        turn = self.active_turn
        if turn is None or not is_closed(self.state):
            return False
        # Kuyruk sınırsız: `put_nowait` burada bloke olamaz, ki senkron kalabilsin.
        turn.segments.put_nowait(segment)
        return True

    async def deliver(self, segment: Segment) -> None:
        """Gelen segmentin gideceği yeri seçer.

        **Kapalı durumda yeni tur açılmaz** (§5): `ONAY_BEKLIYOR` ve `KAYIT` sırasında
        gelen metin ajan katmanına *hiç* ulaşmaz, koşan turun kendi kuyruğuna girer.
        Sıraya alıp turun bitmesini beklemek de olmazdı: onay bekleyen tur zaten o
        segmenti bekliyor, yani sistem kendi kendini kilitlerdi.

        Kontrol burada da duruyor, `route()`'a taşınmış olmasına rağmen: bu yol tek
        segmentlik testlerin ve doğrudan çağrının kapısı, ve iki kapının kararı aynı olmalı.
        """
        if self.route(segment):
            return
        await self.run_turn(segment)

    async def run_turn(self, segment: Segment) -> None:
        """Bir segmenti tura çevirir. Global kilit yüzünden turlar sıraya girer."""
        async with self._turn_lock:
            turn = ActiveTurn(turn_id=new_turn_id(), segment=segment)
            self.active_turn = turn
            # Durum, koşucu başlamadan **önce** yürütülür: sonra yürütülseydi koşucunun
            # ilk olayı `COZUMLUYOR`'a geçişten önce gelebilirdi.
            await self._apply(Event.SEGMENT_ALINDI)
            # Koşucu kendi görevinde koşar; iptalin tutunacak bir yeri olması için.
            turn.task = asyncio.create_task(
                self._runner.run(turn, _Report(self._apply)), name=f"turn:{turn.turn_id}"
            )
            try:
                await turn.task
            except asyncio.CancelledError:
                if not turn.cancelled:
                    # Bu iptal bu tura ait değil — süreç kapanıyor. Yutmak, kapanışı
                    # bekleyen tarafın sonsuza kadar beklemesi demek olurdu.
                    raise
            except BaseException as error:
                # Önce sebep, sonra durum: istemci `IDLE`'ı hatadan önce görürse turun
                # sessizce bittiğini sanır (§14, Kural 13).
                await self._sink.turn_failed(turn.turn_id, f"{type(error).__name__}: {error}")
                # Patlayan tur sistemi kendi durumunda bırakmaz: bir sonraki segment
                # `IDLE` beklediği için, aksi halde ikinci bir hata olarak geri gelirdi.
                await self._reset()
                raise
            finally:
                self.active_turn = None
                # §11.2'nin ikinci anı: boştaki ilk fırsat. Tur patlamış olsa da geçerli —
                # bekleyen özetleme, turun sonucundan bağımsız.
                if self._idle is not None:
                    self._idle.turn_finished()

    async def interrupt(self, turn_id: str) -> None:
        """Söz kesme (§5, §12). Kapsamı **tek tur**, giden kuyruğun tamamı değil.

        `KONUSUYOR` ve `DUSUNUYOR`'da tur iptal edilir — ikincisi 2026-08-10'da tabloya
        eklendi (Kural 12). `ONAY_BEKLIYOR`'da ise yalnızca ses durur: durum değişmez ve
        bekleyen plan yaşar (B3) — sonraki segment onay çözümleyicisine gider. Tablonun
        tanımlamadığı bir durumda gelen söz kesme `InvalidTransitionError` yükseltir; §5
        onu tanımlamıyor ve varsayımla tanımlamak açık bir maddeyi kapatmak olurdu
        (Kural 13).
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
