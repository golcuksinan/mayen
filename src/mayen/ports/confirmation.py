"""Sesli niyet onayının sözlüğü ve model portları (§10.5)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class Resolution(StrEnum):
    """Çözümleyicinin üç sonucu; kısıt dışı bir cevap bunlardan biri değil, hatadır (§10.5)."""

    CONFIRM = "confirm"
    REJECT = "reject"
    UNCLEAR = "unclear"


class Outcome(StrEnum):
    """Bir onay planının nasıl kapandığı; modele bu değerle bildirilir."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass(frozen=True)
class PlannedCall:
    """Onay bekleyen tek çağrı; soru cümlesi yalnızca bundan yazılır (§10.5 adım 3)."""

    name: str
    description: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class Answer:
    """Onay beklenirken gelen tek segment.

    `speaker`, segmenti söyleyen kişinin kimliğidir; bilinmiyorsa `None`. Kimin doldurduğu
    kapının işi değildir: eşleşme kuralı (§10.5 adım 4) yalnızca bu alana bakar. `record`,
    sözün transkriptteki kaydıdır (`ref`); planın kapanış olayı ona bağlanır, çünkü bu söz
    modele değil çözümleyiciye gitmiştir.
    """

    text: str
    speaker: str | None
    record: str | None = None


class QuestionWriter(Protocol):
    """Plandaki çağrılardan tek bir onay sorusu yazar (§10.5 adım 3)."""

    async def write(self, calls: Sequence[PlannedCall]) -> str: ...


class AnswerResolver(Protocol):
    """Soruya verilen cevabı üç sonuçtan birine çevirir; kısıt dışı cevapta yükseltir."""

    async def resolve(self, question: str, answer: str) -> Resolution: ...
