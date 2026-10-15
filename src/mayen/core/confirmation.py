"""Onay planının kuralları (§10.5, §9.3); hattaki uygulaması `pipeline`'dadır."""

from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from mayen.ports.confirmation import Answer, AnswerResolver, PlannedCall, Resolution
from mayen.ports.tools import Caller, Confirmation, ToolResult


@dataclass(frozen=True)
class Entry:
    call: PlannedCall
    kind: Confirmation
    execute: Callable[[], Awaitable[ToolResult]]


@dataclass
class Plan:
    """Bir cevaptaki onay gerektiren bütün çağrılar; kullanıcıya tek soru gider (§9.3)."""

    requester: Caller  # turu açan kişi; cevabı yalnızca o verebilir (§10.5 adım 4)
    entries: list[Entry] = field(default_factory=list)
    question: str = ""
    asked_again: bool = False
    answers: list[str] = field(default_factory=list)  # cevap olan sözlerin kayıtları

    @property
    def calls(self) -> list[PlannedCall]:
        return [e.call for e in self.entries]

    @property
    def kind(self) -> Confirmation:
        """Planın istediği en güçlü onay; kimlik onayı niyeti de kanıtlar (§10.3)."""
        if any(e.kind is Confirmation.IDENTITY for e in self.entries):
            return Confirmation.IDENTITY
        return Confirmation.INTENT


def _leaves(value: object) -> Iterator[str]:
    if isinstance(value, Mapping):
        for v in value.values():
            yield from _leaves(v)
    elif isinstance(value, list | tuple):
        for v in value:
            yield from _leaves(v)
    elif value is not None:
        yield str(value)


def missing_values(calls: Sequence[PlannedCall], question: str) -> list[str]:
    """Soruda aynen geçmeyen argüman değerleri (§10.5 adım 3)."""
    return [v for c in calls for v in _leaves(c.arguments) if v not in question]


def speaker_matches(requester: Caller, answer: Answer) -> bool:
    """Kimliği bilinmeyen bir konuşmacı turu açan kişiyle eşleşmiş sayılamaz."""
    return answer.speaker is not None and answer.speaker == requester.person_id


async def resolve_answer(plan: Plan, answer: Answer, resolver: AnswerResolver) -> Resolution:
    """Eşleşmeyen konuşmacının cevabı, söylenenden bağımsız olarak belirsizdir (§10.5 adım 4).

    Bu durumda çözümleyici hiç çağrılmaz: odadaki başka birinin "evet"i ne derse desin
    sorulan kişinin onayı yerine geçmez.
    """
    if not speaker_matches(plan.requester, answer):
        return Resolution.UNCLEAR
    return await resolver.resolve(plan.question, answer.text)


class Step(StrEnum):
    EXECUTE = "execute"
    REJECT = "reject"
    ASK_AGAIN = "ask_again"
    CANCEL = "cancel"


def next_step(plan: Plan, resolution: Resolution) -> Step:
    """Belirsiz cevap bir kez daha sorulur; ikincisi iptaldir (§10.5 adım 5)."""
    if resolution is Resolution.CONFIRM:
        return Step.EXECUTE
    if resolution is Resolution.REJECT:
        return Step.REJECT
    return Step.CANCEL if plan.asked_again else Step.ASK_AGAIN
