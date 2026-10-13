"""Testlerin ortak sahteleri: saat ve bellekte olay kaydı."""

from datetime import UTC, datetime, timedelta

from mayen.core.events import Recorder
from mayen.ports.events import Event, EventKind
from mayen.ports.triggers import TurnId

T0 = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, start: datetime = T0) -> None:
        self.wall = start
        self.mono = 0.0

    def now(self) -> datetime:
        return self.wall

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


class MemoryEventLog:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def append(self, event: Event) -> None:
        self.events.append(event)

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Event]:
        return list(self.events)

    def kinds(self) -> list[EventKind]:
        return [e.header.kind for e in self.events]

    def of(self, kind: EventKind) -> list[Event]:
        return [e for e in self.events if e.header.kind is kind]


def recorder() -> tuple[Recorder, MemoryEventLog]:
    log = MemoryEventLog()
    return Recorder(log, FakeClock()), log
