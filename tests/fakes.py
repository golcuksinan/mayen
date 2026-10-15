"""Testlerin ortak sahteleri: saat, bellekte olay kaydı ve transkript."""

from datetime import UTC, datetime, timedelta

from mayen.core.events import Recorder
from mayen.core.transcript import Transcript
from mayen.pipeline.events import SessionTranscript
from mayen.pipeline.session import Sessions
from mayen.ports.events import Event, EventKind
from mayen.ports.transcript import Utterance
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


class MemoryTranscript:
    def __init__(self) -> None:
        self.utterances: list[Utterance] = []

    def append(self, utterance: Utterance) -> None:
        self.utterances.append(utterance)

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Utterance]:
        return list(self.utterances)


def transcript() -> tuple[Transcript, MemoryTranscript]:
    store = MemoryTranscript()
    return Transcript(store, FakeClock()), store


def session_transcript(
    sessions: Sessions, session: str = "s1"
) -> tuple[SessionTranscript, MemoryTranscript]:
    """Oturumun transkripti; tur kimliği, wiring'deki gibi oturumun süren turundan."""
    writer, store = transcript()

    def turn_id() -> TurnId | None:
        turn = sessions.running(session)
        return None if turn is None else turn.id

    return SessionTranscript(writer, session, turn_id), store
