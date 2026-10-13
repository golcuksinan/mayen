"""Tetikleyici ve turun sözlüğü (§5.1–§5.3)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, NewType
from uuid import UUID

from mayen.ports.tools import Caller

# Sayaç değil uuid: kayıtlar süreçten uzun yaşar ve tekil olmak zorundadır (§5.2).
TurnId = NewType("TurnId", UUID)


class Priority(StrEnum):
    """Büyükten küçüğe; sıra `rank` ile okunur (§5.1)."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Büyük olan önce gelir."""
        return len(Priority) - list(Priority).index(self)


class TriggerSource(StrEnum):
    """Yeni bir girdi yolu yeni bir adaptördür, yeni bir kaynak değil (§5.1)."""

    VOICE = "voice"
    TEXT = "text"
    TIMER = "timer"
    EVENT = "event"


class Fate(StrEnum):
    """Kesilen turun akıbeti; turu açan tetikleyicinin kaynağına göre config'tedir (§5.3)."""

    CANCEL = "cancel"
    RESTART = "restart"
    RESUME = "resume"


@dataclass(frozen=True)
class Trigger:
    """Turu başlatan şey (§5.1). `requester` turun kime ait olduğudur; kimse konuşmadan
    açılan turda rolü `system`'dir (§10.2)."""

    session: str
    priority: Priority
    source: TriggerSource
    content: str
    requester: Caller
    # Kaynağın modele verdiği yapılandırılmış ayrıntı (hatırlatmanın vadesi gibi); JSON'a
    # çevrilebilir. Sistem cümle kurmaz, olayı etiketli veri olarak verir (§2.1).
    details: Mapping[str, Any] = field(default_factory=dict)
