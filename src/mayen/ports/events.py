"""Olay zarfı, ortak saat ve olay kaydı portu (§5.5, §11)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, NewType, Protocol
from uuid import UUID

from mayen.ports.tools import Status
from mayen.ports.triggers import TurnId

EventId = NewType("EventId", UUID)

# Sabit genişlik: damgalar metin olarak sıralandığında zaman sırası bozulmasın (§5.5).
_STAMP = "%Y-%m-%dT%H:%M:%S.%fZ"


def stamp(moment: datetime) -> str:
    """Saklanan ve yazılan her zaman damgasının tek biçimi: ISO-8601 UTC (§5.5)."""
    if moment.tzinfo is None:
        # Dilimsiz an yerel mi UTC mi belli değildir; tahmin etmek sıralamayı sessizce kaydırır.
        raise ValueError("naive datetime has no time zone")
    return moment.astimezone(UTC).strftime(_STAMP)


def parse_stamp(text: str) -> datetime:
    return datetime.strptime(text, _STAMP).replace(tzinfo=UTC)


class Clock(Protocol):
    """Ortak saat (§5.5): her modül zamanı buradan alır."""

    def now(self) -> datetime:
        """Duvar saati, UTC; damga içindir."""
        ...

    def monotonic(self) -> float:
        """Saniye; yalnızca süre ölçmek içindir, duvar saati geri alınsa da geri gitmez."""
        ...


class EventKind(StrEnum):
    """Olay türleri; saklanan sözlüktür, depo CHECK kısıtını buradan kurar (§11.6)."""

    TURN_STARTED = "turn.started"
    TURN_INTERRUPTED = "turn.interrupted"
    TURN_FINISHED = "turn.finished"
    TOOL_REQUESTED = "tool.requested"  # model çağrıyı istedi; gövde çalışmayabilir
    TOOL_STARTED = "tool.started"
    TOOL_FINISHED = "tool.finished"
    CONFIRMATION_CLOSED = "confirmation.closed"
    STT_SEGMENT = "stt.segment"
    LLM_USAGE = "llm.usage"
    STATE_CHANGED = "state.changed"


class SessionState(StrEnum):
    """Oturumun durumu (§5.4); `state.changed` gövdesinde. Turu olmayan oturum `idle`dır."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


def ref(store: str, record_id: object) -> str:
    """Başka bir depodaki kaydın olaydan gösterilişi (`Header.related`): `depo:kimlik`."""
    return f"{store}:{record_id}"


@dataclass(frozen=True)
class Header:
    """Her olayda aynı alanlar (§5.5). Log yalnızca bunu yazar; içerik buraya girmez (§14)."""

    id: EventId
    kind: EventKind
    source: str  # olayı üreten bileşen
    time: datetime
    session: str | None = None
    turn_id: TurnId | None = None
    duration_s: float | None = None
    status: Status | None = None  # olayı üreten bileşen bildirir
    # Sil, kaydın olay kaydındaki kopyalarını gövdeyi okumadan buradan bulur (§11.4).
    related: Sequence[str] = ()


@dataclass(frozen=True)
class Event:
    header: Header
    body: Mapping[str, Any] = field(default_factory=dict)  # türe özgü; JSON'a çevrilebilir


class EventLog(Protocol):
    """Olay kaydı deposu (§11). Okuma zaman sırasıyladır; aralık `[since, until)`.

    Ekleme eşzamanlıdır: tek kısa bir yazmadır ve olaylar üretildikleri sırayla yazılır.
    """

    def append(self, event: Event) -> None: ...

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Event]: ...
