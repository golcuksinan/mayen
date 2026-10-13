"""Ortak saat ve olayların kaydı (§5.5): başlığı çekirdek doldurur, gövdeyi üreten bileşen."""

import logging
import time
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from mayen.ports.events import Clock, Event, EventId, EventKind, EventLog, Header, stamp
from mayen.ports.tools import Status
from mayen.ports.triggers import TurnId

log = logging.getLogger(__name__)


class SystemClock:
    """Makinenin saati. Makineler arası ortak saat AÇIK (§16.13)."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


def describe(header: Header) -> str:
    """Logun gördüğü tek şey: başlık (§14). Gövde buraya hiçbir yoldan girmez."""
    parts = [
        stamp(header.time),
        header.kind.value,
        f"source={header.source}",
        f"id={header.id}",
    ]
    if header.session is not None:
        parts.append(f"session={header.session}")
    if header.turn_id is not None:
        parts.append(f"turn={header.turn_id}")
    if header.status is not None:
        parts.append(f"status={header.status.value}")
    if header.duration_s is not None:
        parts.append(f"duration_s={header.duration_s:.3f}")
    if header.related:
        parts.append(f"related={','.join(header.related)}")
    return " ".join(parts)


class Recorder:
    """Olayları zarflayıp kaydeder ve başlığını loga yazar."""

    def __init__(self, events: EventLog, clock: Clock) -> None:
        self._events = events
        self.clock = clock

    def emit(
        self,
        kind: EventKind,
        source: str,
        body: Mapping[str, Any] | None = None,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        duration_s: float | None = None,
        status: Status | None = None,
        related: Sequence[str] = (),
    ) -> Event:
        header = Header(
            id=EventId(uuid.uuid4()),
            kind=kind,
            source=source,
            time=self.clock.now(),
            session=session,
            turn_id=turn_id,
            duration_s=duration_s,
            status=status,
            related=tuple(related),
        )
        event = Event(header, dict(body or {}))
        # Kayıt önce: yazılamayan olay yükselir ve logda yazılmış gibi görünmez.
        self._events.append(event)
        log.info("event %s", describe(header))
        return event
