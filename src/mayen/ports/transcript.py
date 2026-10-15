"""Transkript deposu portu (§11): kim, ne zaman, ne söyledi; Mayen'in kendi sözleri dahil.

Söz yalnızca burada durur; olay kaydı ona kimliğiyle bağlanır (`Header.related`). Aynı metin
iki yerde tutulsaydı unut ve sil birinde unutulurdu (§11.4).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType, Protocol
from uuid import UUID

from mayen.ports.tools import Role
from mayen.ports.triggers import TurnId

UtteranceId = NewType("UtteranceId", UUID)


class Party(StrEnum):
    """Sözün kimden geldiği; saklanan sözlüktür (§11.6)."""

    PERSON = "person"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Utterance:
    id: UtteranceId
    time: datetime
    session: str
    turn_id: TurnId | None  # tur dışında duyulan söz de yazılır (§6, sürekli STT)
    party: Party
    # Kişinin o anki rolü ve kimliği; Mayen'in sözünde ikisi de boştur.
    role: Role | None
    person_id: str | None
    text: str
    interrupted: bool = False  # Mayen'in sözü yarıda kesildi; metin söylenen kadardır


class TranscriptStore(Protocol):
    """Okuma zaman sırasıyladır; aralık `[since, until)`."""

    def append(self, utterance: Utterance) -> None: ...

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Utterance]: ...
