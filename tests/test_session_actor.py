"""Aktör iskeleti testleri (§5): cihaz kuyruğu, global tek tur, varlık takibi."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from mayen.session.actor import ActiveTurn, Segment, Session
from mayen.session.state import Event, InvalidTransitionError, State


class RecordingSink:
    """Duyurulan durumları ve iptalleri toplar."""

    def __init__(self) -> None:
        self.seen: list[tuple[State, str | None]] = []
        self.cancelled: list[str] = []

    async def state_changed(self, state: State, turn_id: str | None) -> None:
        self.seen.append((state, turn_id))

    async def turn_cancelled(self, turn_id: str) -> None:
        self.cancelled.append(turn_id)


class ScriptedRunner:
    """Verilen olayları sırayla bildirir; araya `gate` konabilir."""

    def __init__(self, events: list[Event], gate: asyncio.Event | None = None) -> None:
        self.events = events
        self.gate = gate
        self.turn_ids: list[str] = []

    async def run(self, turn: ActiveTurn, report: Callable[[Event], Awaitable[None]]) -> None:
        self.turn_ids.append(turn.turn_id)
        if self.gate is not None:
            await self.gate.wait()
        for event in self.events:
            await report(event)


class WaitingRunner:
    """Verilen olayları bildirir, sonra bekler — söz kesmenin yakalayacağı yer."""

    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.started = asyncio.Event()
        self.was_cancelled = False

    async def run(self, turn: ActiveTurn, report: Callable[[Event], Awaitable[None]]) -> None:
        for event in self.events:
            await report(event)
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.was_cancelled = True
            raise


HAPPY_PATH = [Event.COZUMLEME_BITTI, Event.ILK_SES_HAZIR, Event.SES_BITTI]
UNTIL_SPEAKING = [Event.COZUMLEME_BITTI, Event.ILK_SES_HAZIR]
UNTIL_APPROVAL = [Event.COZUMLEME_BITTI, Event.ONAY_GEREKLI]


def segment(device_id: str, segment_id: str = "s1") -> Segment:
    return Segment(segment_id=segment_id, device_id=device_id, payload="merhaba")


async def test_turn_walks_the_state_machine_and_returns_to_idle() -> None:
    sink = RecordingSink()
    session = Session(ScriptedRunner(HAPPY_PATH), sink)
    await session.run_turn(segment("salon"))

    assert [state for state, _ in sink.seen] == [
        State.COZUMLUYOR,
        State.DUSUNUYOR,
        State.KONUSUYOR,
        State.IDLE,
    ]
    assert session.state is State.IDLE


async def test_server_mints_the_turn_id() -> None:
    # Gelen segment henüz bir tura ait değil (§13); kimliği sunucu üretir.
    runner = ScriptedRunner(HAPPY_PATH)
    session = Session(runner, RecordingSink())
    await session.run_turn(segment("salon", "s1"))
    await session.run_turn(segment("mutfak", "s2"))
    assert runner.turn_ids == ["t1", "t2"]


async def test_only_one_turn_runs_at_a_time_across_devices() -> None:
    # Aynı anda tek tur, kapsamı global (§5): ikinci cihazın segmenti sıraya girer.
    gate = asyncio.Event()
    runner = ScriptedRunner(HAPPY_PATH, gate=gate)
    session = Session(runner, RecordingSink())

    first = asyncio.create_task(session.run_turn(segment("salon", "s1")))
    await asyncio.sleep(0)
    second = asyncio.create_task(session.run_turn(segment("mutfak", "s2")))
    await asyncio.sleep(0)

    assert runner.turn_ids == ["t1"]  # ikincisi kilitte bekliyor
    gate.set()
    await asyncio.gather(first, second)
    assert runner.turn_ids == ["t1", "t2"]


async def test_actor_processes_its_queue() -> None:
    runner = ScriptedRunner(HAPPY_PATH)
    session = Session(runner, RecordingSink())
    actor = session.actor("salon")
    await actor.submit(segment("salon", "s1"))
    await actor.submit(segment("salon", "s2"))

    async with asyncio.timeout(1):
        while len(runner.turn_ids) < 2:
            await asyncio.sleep(0)
    await session.close()


async def test_presence_is_tracked_per_device() -> None:
    session = Session(ScriptedRunner([]), RecordingSink())
    salon = session.actor("salon")
    mutfak = session.actor("mutfak")

    assert salon.last_interaction is None
    await salon.submit(segment("salon"))
    assert salon.last_interaction is not None
    assert mutfak.last_interaction is None  # §12: en son kullanılan cihaz ayırt edilebilir
    await session.close()


async def test_same_device_reuses_its_actor() -> None:
    session = Session(ScriptedRunner([]), RecordingSink())
    assert session.actor("salon") is session.actor("salon")
    await session.close()


async def test_device_id_is_required() -> None:
    session = Session(ScriptedRunner([]), RecordingSink())
    with pytest.raises(ValueError, match="Cihaz kimliği"):
        session.actor("")


async def test_failing_turn_does_not_kill_the_actor() -> None:
    class ExplodingRunner:
        def __init__(self) -> None:
            self.calls = 0

        async def run(
            self, turn: ActiveTurn, report: Callable[[Event], Awaitable[None]]
        ) -> None:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("koşucu patladı")

    runner = ExplodingRunner()
    session = Session(runner, RecordingSink())
    actor = session.actor("salon")
    await actor.submit(segment("salon", "s1"))
    await actor.submit(segment("salon", "s2"))

    async with asyncio.timeout(1):
        while runner.calls < 2:
            await asyncio.sleep(0)
    await session.close()


# --- söz kesme (§5, §12) ----------------------------------------------------------------


async def start_turn(session: Session, runner: WaitingRunner) -> asyncio.Task[None]:
    task = asyncio.create_task(session.run_turn(segment("salon")))
    async with asyncio.timeout(1):
        await runner.started.wait()
    return task


async def test_barge_in_while_speaking_cancels_the_turn() -> None:
    sink = RecordingSink()
    runner = WaitingRunner(UNTIL_SPEAKING)
    session = Session(runner, sink)
    task = await start_turn(session, runner)
    assert sink.seen[-1] == (State.KONUSUYOR, "t1")

    await session.interrupt("t1")
    async with asyncio.timeout(1):
        await task

    assert session.state is State.IDLE
    assert runner.was_cancelled  # iptal asyncio'nun kendi yolundan indi
    assert sink.cancelled == ["t1"]


async def test_barge_in_while_reading_approval_keeps_the_plan_alive() -> None:
    # B3: ses durur, durum değişmez, tur yaşar — segment onay çözümleyicisine gidecek.
    sink = RecordingSink()
    runner = WaitingRunner(UNTIL_APPROVAL)
    session = Session(runner, sink)
    task = await start_turn(session, runner)
    assert session.state is State.ONAY_BEKLIYOR
    turn = session.active_turn
    assert turn is not None

    await session.interrupt("t1")

    assert session.state is State.ONAY_BEKLIYOR
    assert turn.speech_stopped.is_set()  # ses durdu
    assert not turn.cancelled and not task.done()  # ama plan yaşıyor
    assert sink.cancelled == []  # iptal bildirimi de gitmedi

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_interrupt_for_another_turn_is_ignored() -> None:
    # İptal sonrası ağda kalan ölü turun çerçevesi (§13): beklenen, hata değil.
    sink = RecordingSink()
    runner = WaitingRunner(UNTIL_SPEAKING)
    session = Session(runner, sink)
    task = await start_turn(session, runner)

    await session.interrupt("t9")

    assert session.state is State.KONUSUYOR
    assert sink.cancelled == []
    assert not task.done()

    await session.interrupt("t1")
    await task


async def test_interrupt_in_an_undefined_state_is_not_swallowed() -> None:
    # §5 DÜŞÜNÜYOR'da söz kesmeyi tanımlamıyor; varsayımla tanımlamak açık maddeyi
    # kapatmak olurdu (Kural 13).
    runner = WaitingRunner([Event.COZUMLEME_BITTI])
    session = Session(runner, RecordingSink())
    task = await start_turn(session, runner)
    assert session.state is State.DUSUNUYOR

    with pytest.raises(InvalidTransitionError):
        await session.interrupt("t1")

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_next_turn_runs_after_a_barge_in() -> None:
    # İptalin kapsamı tur: sistem tıkanmaz, sıradaki segment yeni bir tur açar.
    runner = WaitingRunner(UNTIL_SPEAKING)
    session = Session(runner, RecordingSink())
    task = await start_turn(session, runner)
    await session.interrupt("t1")
    await task

    plain = ScriptedRunner(HAPPY_PATH)
    session._runner = plain  # koşucuyu değiştirmenin başka yolu yok
    await session.run_turn(segment("mutfak", "s2"))
    assert plain.turn_ids == ["t2"]
    assert session.state is State.IDLE


# --- kapalı durumlar ve zaman aşımı (§5, §17.5) -----------------------------------------


async def test_changing_the_subject_during_approval_never_reaches_the_agent() -> None:
    # ONAY_BEKLİYOR kapalı bir durum (§5): gelen segment yeni tur açmaz, koşan turun
    # kuyruğuna girer — orada onu okuyacak olan onay çözümleyicisidir.
    runner = WaitingRunner(UNTIL_APPROVAL)
    session = Session(runner, RecordingSink())
    task = await start_turn(session, runner)
    turn = session.active_turn
    assert turn is not None

    other = segment("salon", "s2")
    await session.deliver(other)

    assert session.active_turn is turn  # yeni tur açılmadı
    assert turn.segments.get_nowait() is other

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_speaking_during_recording_does_not_start_a_turn() -> None:
    # KAYIT da kapalı (§5): ses profili kaydı sırasında gelen segment normal tur akışına
    # girmez.
    runner = WaitingRunner([Event.COZUMLEME_BITTI, Event.KAYIT_GEREKLI])
    session = Session(runner, RecordingSink())
    task = await start_turn(session, runner)
    turn = session.active_turn
    assert turn is not None

    await session.deliver(segment("salon", "s2"))

    assert turn.segments.qsize() == 1
    assert session.active_turn is turn

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_a_segment_in_an_open_state_starts_a_new_turn() -> None:
    # Kapalı olmayan durumda aynı yol yeni tur açar; ikisini ayıran tek şey `is_closed`.
    runner = ScriptedRunner(HAPPY_PATH)
    session = Session(runner, RecordingSink())
    await session.deliver(segment("salon", "s1"))
    assert runner.turn_ids == ["t1"]


async def test_approval_timeout_returns_to_idle_without_speaking() -> None:
    # Zaman aşımı = red (Kural 5) ama plan düşer ve konuşulmaz: karşıda kimse yok.
    # Sayacı işleten taraf politika (§10); aktör yalnızca olayı tabloya uygular.
    sink = RecordingSink()
    session = Session(
        ScriptedRunner([Event.COZUMLEME_BITTI, Event.ONAY_GEREKLI, Event.ONAY_ZAMAN_ASIMI]),
        sink,
    )
    await session.run_turn(segment("salon"))

    assert [state for state, _ in sink.seen] == [
        State.COZUMLUYOR,
        State.DUSUNUYOR,
        State.ONAY_BEKLIYOR,
        State.IDLE,
    ]
    assert State.KONUSUYOR not in [state for state, _ in sink.seen]
