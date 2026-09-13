"""Proaktif ses kanalı (§12): hedef cihaz, sıraya girme, söz kesmeden etkilenmeme."""

import asyncio

from mayen.adapters.audio import AudioFormat
from mayen.adapters.fakes.tts import FakeTTS
from mayen.data import clock
from mayen.data.repositories.tasks import ScheduledTask, TaskKind, TaskStatus
from mayen.scheduler.announce import Announcer
from mayen.scheduler.reminders import reminder_handler
from mayen.session.actor import Segment, Session
from mayen.session.state import State
from mayen.turn.report import TurnReport


class Sink:
    """`ProactiveSink` + `SessionSink`: duyulan her şeyi cihazına göre toplar."""

    def __init__(self, connected: set[str] | None = None) -> None:
        self.devices = connected if connected is not None else set()
        self.frames: list[tuple[str, str, object]] = []

    # --- ProactiveSink
    def connected(self) -> frozenset[str]:
        return frozenset(self.devices)

    async def announcement(self, device_id: str, turn_id: str, text: str) -> None:
        self.frames.append((device_id, "announcement", (turn_id, text)))

    async def announcement_chunk(
        self, device_id: str, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        self.frames.append((device_id, "chunk", (turn_id, seq)))

    async def announcement_end(self, device_id: str, turn_id: str) -> None:
        self.frames.append((device_id, "end", turn_id))

    # --- SessionSink
    async def state_changed(self, state: State, turn_id: str | None) -> None: ...

    async def turn_cancelled(self, turn_id: str) -> None: ...

    async def turn_failed(self, turn_id: str, error: str) -> None: ...

    def kinds(self, device_id: str) -> list[str]:
        return [kind for device, kind, _ in self.frames if device == device_id]


class SlowRunner:
    """Bir turu, salıverilene kadar `KONUSUYOR`'da tutan koşucu."""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, turn: object, report: TurnReport) -> None:
        await report.understood()
        await report.speaking()
        self.started.set()
        await self.release.wait()
        await report.spoke()


class IdleRunner:
    async def run(self, turn: object, report: TurnReport) -> None: ...


def _session(sink: Sink) -> Session:
    return Session(IdleRunner(), sink)


def _task(message: object) -> ScheduledTask:
    return ScheduledTask(
        id=1,
        kind=TaskKind.REMINDER.value,
        payload={"message": message},
        due_at=clock.now(),
        status=TaskStatus.BEKLIYOR,
        outcome=None,
        person_id=None,
        created_at=clock.now(),
        settled_at=None,
    )


async def test_announcement_frame_precedes_the_audio() -> None:
    """İstemci turu bilmeden gelen parçayı §13 gereği atardı."""
    sink = Sink({"salon"})
    announcer = Announcer(FakeTTS(), _session(sink), sink)

    turn_id = await announcer.announce("İlaç vakti.")

    assert turn_id is not None
    assert sink.kinds("salon")[0] == "announcement"
    assert sink.kinds("salon")[-1] == "end"
    assert "chunk" in sink.kinds("salon")


async def test_target_is_the_most_recently_used_connected_device() -> None:
    sink = Sink({"salon", "mutfak"})
    session = _session(sink)
    # Damga saniye çözünürlüğünde (§16'nın tek biçimi): iki turu arka arkaya koşturmak
    # eşit zaman üretir ve sıralamayı zamanlamaya emanet ederdi.
    session.actor("salon").last_interaction = "2026-08-10T10:00:00Z"
    session.actor("mutfak").last_interaction = "2026-08-10T10:05:00Z"
    try:
        await Announcer(FakeTTS(), session, sink).announce("İlaç vakti.")
    finally:
        await session.close()

    assert {device for device, _, _ in sink.frames} == {"mutfak"}


async def test_disconnected_device_is_not_chosen_even_if_it_spoke_last() -> None:
    sink = Sink({"salon"})
    session = _session(sink)
    session.actor("mutfak").last_interaction = "2026-08-10T10:05:00Z"
    try:
        await Announcer(FakeTTS(), session, sink).announce("İlaç vakti.")
    finally:
        await session.close()

    assert {device for device, _, _ in sink.frames} == {"salon"}


async def test_with_no_device_the_notice_is_queued_and_given_to_the_first_to_connect() -> None:
    """§12: düşürülmüyor. Duyulmayan hatırlatıcı, hiç kurulmamış hatırlatıcıdır."""
    sink = Sink()
    announcer = Announcer(FakeTTS(), _session(sink), sink)

    assert await announcer.announce("bir") is None
    assert await announcer.announce("iki") is None
    assert sink.frames == []

    sink.devices.add("salon")
    announcer.connected("salon")
    await asyncio.sleep(0.05)
    await announcer.close()

    texts = [payload[1] for _, kind, payload in sink.frames if kind == "announcement"]  # type: ignore[index]
    assert texts == ["bir", "iki"], "sıra korunuyor: hangi hatırlatıcının ne zamana ait olduğu"


async def test_announcement_waits_for_the_running_turn() -> None:
    """§12: araya girmiyor, sıraya giriyor."""
    sink = Sink({"salon"})
    runner = SlowRunner()
    session = Session(runner, sink)
    announcer = Announcer(FakeTTS(), session, sink)

    turn = asyncio.create_task(session.run_turn(Segment("s1", "salon", "selam")))
    await runner.started.wait()

    notice = asyncio.create_task(announcer.announce("İlaç vakti."))
    await asyncio.sleep(0.05)
    assert sink.frames == [], "asistan konuşurken bildirim başlamadı"

    runner.release.set()
    await turn
    await notice
    await session.close()

    assert sink.kinds("salon")[0] == "announcement"


async def test_interrupt_does_not_touch_the_announcement_turn() -> None:
    """İptalin kapsamı tek tur (§5, §12): bildirimin kendi `turn_id`'si var."""
    sink = Sink({"salon"})
    session = _session(sink)
    announcer = Announcer(FakeTTS(), session, sink)

    turn_id = await announcer.announce("İlaç vakti.")
    before = len(sink.frames)
    assert turn_id is not None

    await session.interrupt(turn_id)  # ölü/ilgisiz tur: sessizce yok sayılmıyor, kayda geçiyor

    assert len(sink.frames) == before
    await session.close()


async def test_reminder_handler_reports_whether_it_was_heard() -> None:
    sink = Sink({"salon"})
    handler = reminder_handler(Announcer(FakeTTS(), _session(sink), sink))

    outcome = await handler(_task("İlaç vakti."))

    assert outcome.startswith("seslendirildi")


async def test_reminder_handler_records_a_queued_notice_as_such() -> None:
    sink = Sink()
    handler = reminder_handler(Announcer(FakeTTS(), _session(sink), sink))

    assert await handler(_task("İlaç vakti.")) == "kuyruklandı: bağlı cihaz yok"


async def test_reminder_without_a_message_fails_loudly() -> None:
    """Boş bir hatırlatıcı seslendirmek, kullanıcıya sebepsiz ses çıkarmak olurdu."""
    sink = Sink({"salon"})
    handler = reminder_handler(Announcer(FakeTTS(), _session(sink), sink))

    try:
        await handler(_task(None))
    except ValueError:
        return
    raise AssertionError("bozuk yük sessizce geçti")
