"""Onay kapısı (§10.5, §9.3): kurallar Pipecat'siz, kapı Pipecat'in test hattında."""

import asyncio
import json
import logging
from collections.abc import Sequence
from typing import Any

import pytest
from pipecat.frames.frames import (
    Frame,
    FunctionCallFromLLM,
    FunctionCallResultFrame,
    FunctionCallsStartedFrame,
    LLMMessagesAppendFrame,
    TranscriptionFrame,
    TTSSpeakFrame,
)
from pipecat.tests.utils import SleepFrame, run_test
from pydantic import BaseModel

from fakes import FakeClock, MemoryEventLog
from mayen.core.confirmation import (
    Plan,
    Step,
    missing_values,
    next_step,
    resolve_answer,
    speaker_matches,
)
from mayen.core.events import Recorder
from mayen.pipeline.confirmation import ConfirmationGateProcessor
from mayen.pipeline.events import UTTERANCE, SessionEvents
from mayen.ports.confirmation import Answer, PlannedCall, Resolution
from mayen.ports.events import EventKind
from mayen.ports.tools import (
    Caller,
    Confirmation,
    Effect,
    Role,
    Sensitivity,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
)

OWNER = Caller(Role.OWNER, "p1", has_personal_device=True)
DELETE_1 = PlannedCall("note_delete", "delete a note", {"id": 1})


class Resolver:
    def __init__(self, *answers: Resolution | Exception) -> None:
        self.answers = list(answers)
        self.asked: list[tuple[str, str]] = []

    async def resolve(self, question: str, answer: str) -> Resolution:
        self.asked.append((question, answer))
        out = self.answers.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


class Writer:
    def __init__(self, *questions: str) -> None:
        self.questions = list(questions)
        self.plans: list[Sequence[PlannedCall]] = []

    async def write(self, calls: Sequence[PlannedCall]) -> str:
        self.plans.append(calls)
        return self.questions.pop(0) if len(self.questions) > 1 else self.questions[0]


# --- kurallar ---------------------------------------------------------------


def test_missing_values_checks_every_leaf() -> None:
    calls = [
        PlannedCall("note_delete", "", {"id": 2}),
        PlannedCall("contact_add", "", {"name": "Gülşen", "tags": ["iş"], "note": None}),
    ]
    assert missing_values(calls, "Delete note 2 and add Gülşen?") == ["iş"]
    assert missing_values(calls, "Delete note 2 and add Gülşen, tagged iş?") == []


def test_unknown_or_other_speaker_does_not_match() -> None:
    assert speaker_matches(OWNER, Answer("evet", "p1"))
    assert not speaker_matches(OWNER, Answer("evet", "p2"))
    assert not speaker_matches(OWNER, Answer("evet", None))
    nobody = Caller(Role.UNKNOWN, None, has_personal_device=False)
    assert not speaker_matches(nobody, Answer("evet", None))


async def test_other_speaker_is_unclear_without_asking_the_resolver() -> None:
    resolver = Resolver(Resolution.CONFIRM)
    plan = Plan(OWNER, question="Delete note 1?")
    assert await resolve_answer(plan, Answer("evet", "p2"), resolver) is Resolution.UNCLEAR
    assert resolver.asked == []
    assert await resolve_answer(plan, Answer("evet", "p1"), resolver) is Resolution.CONFIRM


def test_unclear_is_asked_once_more_then_cancelled() -> None:
    plan = Plan(OWNER)
    assert next_step(plan, Resolution.CONFIRM) is Step.EXECUTE
    assert next_step(plan, Resolution.REJECT) is Step.REJECT
    assert next_step(plan, Resolution.UNCLEAR) is Step.ASK_AGAIN
    plan.asked_again = True
    assert next_step(plan, Resolution.UNCLEAR) is Step.CANCEL


# --- kapı -------------------------------------------------------------------


class NoteId(BaseModel):
    id: int


def _spec(name: str) -> ToolSpec[Any]:
    async def run(args: Any, ctx: ToolContext) -> ToolResult:  # noqa: ANN401
        return ToolResult(Status.OK)

    return ToolSpec(
        name=name,
        description=name,
        args=NoteId,
        effect=Effect.IRREVERSIBLE,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=False,
        timeout_s=1,
        run=run,
    )


DELETE = _spec("note_delete")


class Executed:
    def __init__(self) -> None:
        self.order: list[int] = []

    def body(self, note: int) -> Any:  # noqa: ANN401
        async def execute() -> ToolResult:
            self.order.append(note)
            return ToolResult(Status.OK, {"deleted": note})

        return execute


def gate(
    writer: Writer,
    resolver: Resolver,
    timeout_s: float = 5,
    log: MemoryEventLog | None = None,
) -> ConfirmationGateProcessor:
    events = SessionEvents(Recorder(log or MemoryEventLog(), FakeClock()), "s1", lambda: None)
    return ConfirmationGateProcessor(writer, resolver, timeout_s, lambda f: f.user_id, events)


async def request(
    g: ConfirmationGateProcessor,
    executed: Executed,
    note: int,
    kind: Confirmation = Confirmation.INTENT,
) -> None:
    await g.request(DELETE, NoteId(id=note), kind, executed.body(note), OWNER)


def started(*ids: str) -> FunctionCallsStartedFrame:
    calls = [FunctionCallFromLLM("note_delete", i, {}, None) for i in ids]
    return FunctionCallsStartedFrame(function_calls=calls)


def result(call_id: str) -> FunctionCallResultFrame:
    return FunctionCallResultFrame(
        function_name="note_delete",
        tool_call_id=call_id,
        arguments={},
        result={"status": "awaiting_confirmation"},
    )


def said(text: str, speaker: str = "p1") -> TranscriptionFrame:
    return TranscriptionFrame(text, speaker, "")


def of[F: Frame](frames: Sequence[Frame], kind: type[F]) -> list[F]:
    return [f for f in frames if isinstance(f, kind)]


def closed(frames: Sequence[Frame]) -> tuple[dict[str, Any], bool]:
    """Kapının modele eklediği tek sonuç mesajı ve modelin konuşturulup konuşturulmadığı."""
    (frame,) = of(frames, LLMMessagesAppendFrame)
    (message,) = frame.messages
    assert isinstance(message, dict) and isinstance(message["content"], str)
    return json.loads(message["content"]), frame.run_llm is True


async def test_calls_of_one_response_are_asked_together_once_all_closed() -> None:
    writer = Writer("Delete notes 1 and 2?")
    resolver = Resolver(Resolution.CONFIRM)
    g, executed = gate(writer, resolver), Executed()
    await request(g, executed, 1)
    await request(g, executed, 2)

    down, _ = await run_test(
        g,
        frames_to_send=[
            started("a", "b"),
            result("a"),
            SleepFrame(0.05),
            result("b"),
            SleepFrame(0.05),
            said("evet"),
            SleepFrame(0.05),
        ],
    )

    assert [len(p) for p in writer.plans] == [2]
    assert [f.text for f in of(down, TTSSpeakFrame)] == ["Delete notes 1 and 2?"]
    assert executed.order == [1, 2]
    content, speak = closed(down)
    assert content["confirmation"] == "confirmed"
    assert [c["result"] for c in content["calls"]] == [
        {"status": "ok", "deleted": 1},
        {"status": "ok", "deleted": 2},
    ]
    assert speak
    # Onay cevabı ana modele gitmez (§5.4).
    assert of(down, TranscriptionFrame) == []


async def test_no_question_while_a_call_of_the_response_is_still_open() -> None:
    writer = Writer("Delete note 1?")
    g, executed = gate(writer, Resolver()), Executed()
    await request(g, executed, 1)

    down, _ = await run_test(
        g, frames_to_send=[started("a", "b"), result("a"), SleepFrame(0.05)]
    )

    assert writer.plans == []
    assert of(down, TTSSpeakFrame) == []


async def test_other_speakers_yes_never_confirms() -> None:
    resolver = Resolver()
    g, executed = gate(Writer("Delete note 1?"), resolver), Executed()
    await request(g, executed, 1)

    down, _ = await run_test(
        g,
        frames_to_send=[
            started("a"),
            result("a"),
            SleepFrame(0.05),
            said("evet", "p2"),
            SleepFrame(0.05),
            said("evet", "p2"),
            SleepFrame(0.05),
        ],
    )

    assert resolver.asked == []
    assert executed.order == []
    assert len(of(down, TTSSpeakFrame)) == 2  # bir kez daha soruldu
    content, _ = closed(down)
    assert content["confirmation"] == "cancelled"


async def test_reject_runs_nothing() -> None:
    g, executed = gate(Writer("Delete note 1?"), Resolver(Resolution.REJECT)), Executed()
    await request(g, executed, 1)

    down, _ = await run_test(
        g, frames_to_send=[started("a"), result("a"), SleepFrame(0.05), said("hayır")]
    )

    assert executed.order == []
    assert closed(down)[0]["confirmation"] == "rejected"


async def test_question_without_the_values_is_never_read() -> None:
    writer = Writer("Delete that note?")
    g, executed = gate(writer, Resolver()), Executed()
    await request(g, executed, 1)

    down, _ = await run_test(g, frames_to_send=[started("a"), result("a"), SleepFrame(0.05)])

    assert len(writer.plans) == 2  # bir kez yeniden istendi
    assert of(down, TTSSpeakFrame) == []
    assert closed(down)[0]["confirmation"] == "rejected"


async def test_timeout_rejects_silently() -> None:
    g, executed = gate(Writer("Delete note 1?"), Resolver(), timeout_s=0.05), Executed()
    await request(g, executed, 1)

    down, _ = await run_test(g, frames_to_send=[started("a"), result("a"), SleepFrame(0.2)])

    content, speak = closed(down)
    assert content["confirmation"] == "timed_out"
    assert not speak
    assert executed.order == []


async def test_plan_of_an_interrupted_turn_is_cancelled_silently() -> None:
    g, executed = gate(Writer("Delete note 1?"), Resolver(Resolution.CONFIRM)), Executed()
    await request(g, executed, 1)

    async def interrupted() -> None:
        await asyncio.sleep(0.1)
        await g.drop()

    dropping = asyncio.create_task(interrupted())
    down, _ = await run_test(
        g, frames_to_send=[started("a"), result("a"), SleepFrame(0.2), said("evet")]
    )
    await dropping

    content, speak = closed(down)
    assert content["confirmation"] == "cancelled"
    assert content["reason"] == "turn interrupted"
    assert not speak
    assert not g.awaiting
    # Sonradan gelen "evet" düşen planı onaylamaz.
    assert executed.order == []


async def test_out_of_grammar_answer_is_an_error_not_unclear() -> None:
    resolver = Resolver(ValueError("MAYBE"))
    g, executed = gate(Writer("Delete note 1?"), resolver), Executed()
    await request(g, executed, 1)

    down, _ = await run_test(
        g, frames_to_send=[started("a"), result("a"), SleepFrame(0.05), said("belki")]
    )

    content, _ = closed(down)
    assert content["confirmation"] == "error"
    assert executed.order == []


async def test_identity_confirmation_is_rejected_while_unavailable() -> None:
    writer = Writer("Delete note 1?")
    g, executed = gate(writer, Resolver()), Executed()
    await request(g, executed, 1, Confirmation.IDENTITY)

    down, _ = await run_test(g, frames_to_send=[started("a"), result("a"), SleepFrame(0.05)])

    assert writer.plans == []
    assert closed(down)[0]["confirmation"] == "rejected"


async def test_text_flows_to_the_model_when_nothing_is_awaited() -> None:
    g = gate(Writer("x"), Resolver())
    down, _ = await run_test(g, frames_to_send=[said("hava nasıl")])
    assert [f.text for f in of(down, TranscriptionFrame)] == ["hava nasıl"]


async def test_closing_is_an_event_and_the_log_carries_no_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    log = MemoryEventLog()
    g, executed = (
        gate(Writer("Delete note 1?"), Resolver(Resolution.REJECT), log=log),
        Executed(),
    )
    await request(g, executed, 1)

    answer = said("hayır silme")
    answer.metadata[UTTERANCE] = "utterance:u1"
    await run_test(
        g,
        frames_to_send=[started("a"), result("a"), SleepFrame(0.05), answer],
    )

    [event] = log.of(EventKind.CONFIRMATION_CLOSED)
    # Cevap olan söz modele gitmedi; olay ona bağlanır.
    assert event.header.related == ("utterance:u1",)
    assert event.header.status is Status.DENIED
    assert event.header.duration_s is not None
    assert event.body["calls"] == [{"tool": "note_delete", "arguments": {"id": 1}}]
    # Soru, cevap ve argümanlar olay kaydındadır, logda değil (§14).
    for content in ("Delete note 1?", "hayır silme", '"id"'):
        assert content not in caplog.text
