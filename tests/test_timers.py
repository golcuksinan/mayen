"""Zamanlayıcılar (§12): gecikme toleransı, kaçırılanlar özeti, tetikleyici döngüsü."""

import asyncio
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest

from fakes import T0, FakeClock
from mayen.adapters.storage.sqlite import Database, SqliteTimerStore
from mayen.adapters.trigger.timer import TimerTrigger
from mayen.core.timers import SYSTEM, TimerDispatcher, local, sort_due
from mayen.ports.timers import Timer, TimerState
from mayen.ports.tools import Sensitivity
from mayen.ports.triggers import Priority, Trigger, TriggerSource


def timer(id_: str, at: float, tolerance_s: float = 60.0) -> Timer:
    return Timer(
        id_,
        T0 + timedelta(seconds=at),
        f"t{id_}",
        Priority.NORMAL,
        tolerance_s,
        Sensitivity.PERSONAL,
        "p1",
        TimerState.PENDING,
    )


def test_due_within_tolerance_fires_beyond_it_is_missed() -> None:
    pending = [timer("1", -60), timer("2", -61), timer("3", 0), timer("4", 1)]
    due = sort_due(pending, T0)
    assert [t.id for t in due.fire] == ["1", "3"]
    assert [t.id for t in due.missed] == ["2"]


def test_zero_tolerance_fires_only_on_time() -> None:
    due = sort_due([timer("1", 0, 0.0), timer("2", -0.5, 0.0)], T0)
    assert ([t.id for t in due.fire], [t.id for t in due.missed]) == (["1"], ["2"])


@pytest.fixture
def store(tmp_path: Path) -> Iterator[SqliteTimerStore]:
    with Database(tmp_path / "m.db") as db:
        yield SqliteTimerStore(db)


class Submitted:
    def __init__(self) -> None:
        self.triggers: list[Trigger] = []
        self.fail = False

    async def __call__(self, trigger: Trigger) -> None:
        if self.fail:
            raise ValueError("no gate")
        self.triggers.append(trigger)


def add(
    store: SqliteTimerStore, at: float, text: str, priority: Priority, person: str = "p1"
) -> str:
    due = T0 + timedelta(seconds=at)
    return store.add(due, text, priority, 60.0, Sensitivity.PERSONAL, person).id


async def test_due_timer_becomes_a_system_trigger_once(store: SqliteTimerStore) -> None:
    clock, submitted = FakeClock(), Submitted()
    add(store, 10, "ilaç", Priority.HIGH)
    dispatcher = TimerDispatcher(store, clock, submitted, lambda *_: "s1")
    await dispatcher.dispatch()
    assert submitted.triggers == []
    clock.advance(10)
    await dispatcher.dispatch()
    await dispatcher.dispatch()
    [trigger] = submitted.triggers
    assert trigger == Trigger(
        "s1",
        Priority.HIGH,
        TriggerSource.TIMER,
        "ilaç",
        SYSTEM,
        {"due": local(T0 + timedelta(seconds=10))},
    )
    assert store.pending() == []


async def test_missed_timers_arrive_as_one_summary(store: SqliteTimerStore) -> None:
    """Uzun bir kapanıştan sonra: toleransı içindeki çalar, aşanlar tek özette (§12)."""
    clock, submitted = FakeClock(), Submitted()
    add(store, -3600, "uyan", Priority.NORMAL)
    add(store, -1800, "toplantı", Priority.URGENT)
    add(store, -30, "ilaç", Priority.NORMAL)
    await TimerDispatcher(store, clock, submitted, lambda *_: "s1").dispatch()
    fired, summary = submitted.triggers
    assert fired.content == "ilaç"
    assert (summary.content, summary.priority) == ("", Priority.URGENT)
    assert [m["text"] for m in summary.details["missed"]] == ["uyan", "toplantı"]
    assert store.pending() == []


async def test_without_a_session_timers_wait(store: SqliteTimerStore) -> None:
    """Hiçbir cihaz bağlı değilse kuyrukta kalır; bağlanınca tolerans yine sayılır (§12)."""
    clock, submitted = FakeClock(), Submitted()
    add(store, 0, "ilaç", Priority.NORMAL)
    target: list[str | None] = [None]
    dispatcher = TimerDispatcher(store, clock, submitted, lambda *_: target[0])
    await dispatcher.dispatch()
    assert submitted.triggers == [] and len(store.pending()) == 1
    clock.advance(61)
    target[0] = "s1"
    await dispatcher.dispatch()
    [summary] = submitted.triggers
    assert summary.details["missed"][0]["text"] == "ilaç"


async def test_each_timer_goes_to_its_own_persons_session(store: SqliteTimerStore) -> None:
    """Hedef kişiye ve hassasiyete göre (§12); kaçırılanlar her oturumda tek özet."""
    clock, submitted = FakeClock(), Submitted()
    add(store, 0, "ilaç", Priority.NORMAL, "p1")
    add(store, 0, "ödev", Priority.NORMAL, "p2")
    add(store, -3600, "uyan", Priority.NORMAL, "p1")
    add(store, -3600, "koşu", Priority.NORMAL, "p2")
    add(store, 0, "kimsesiz", Priority.NORMAL, "p3")
    asked: list[tuple[str | None, Sensitivity]] = []

    def target(person: str | None, sensitivity: Sensitivity) -> str | None:
        asked.append((person, sensitivity))
        return {"p1": "s1", "p2": "s2"}.get(person or "")

    await TimerDispatcher(store, clock, submitted, target).dispatch()
    assert {
        (t.session, t.content or t.details["missed"][0]["text"]) for t in submitted.triggers
    } == {
        ("s1", "ilaç"),
        ("s2", "ödev"),
        ("s1", "uyan"),
        ("s2", "koşu"),
    }
    assert {s for _, s in asked} == {Sensitivity.PERSONAL}
    assert [t.text for t in store.pending()] == ["kimsesiz"]


async def test_failed_submit_keeps_the_timer_pending(store: SqliteTimerStore) -> None:
    clock, submitted = FakeClock(), Submitted()
    add(store, 0, "ilaç", Priority.NORMAL)
    submitted.fail = True
    dispatcher = TimerDispatcher(store, clock, submitted, lambda *_: "s1")
    with pytest.raises(ValueError):
        await dispatcher.dispatch()
    assert len(store.pending()) == 1
    submitted.fail = False
    await dispatcher.dispatch()
    assert [t.content for t in submitted.triggers] == ["ilaç"]


async def test_trigger_looks_at_once_and_then_on_every_interval() -> None:
    looks: list[float] = []
    loop = asyncio.get_running_loop()

    async def dispatch() -> None:
        looks.append(loop.time())

    task = asyncio.create_task(TimerTrigger(dispatch, interval_s=0.01).run())
    await asyncio.sleep(0.035)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(looks) >= 3
