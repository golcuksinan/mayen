"""Tetikleyici kapısı (§5.1–§5.3) Pipecat'in test hattında."""

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import pytest
from pipecat.frames.frames import (
    DataFrame,
    Frame,
    FunctionCallFromLLM,
    FunctionCallResultFrame,
    FunctionCallsStartedFrame,
    InterruptionFrame,
    LLMMessagesAppendFrame,
    LLMRunFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.tests.utils import SleepFrame, run_test

from mayen.core.turns import Turns
from mayen.pipeline.session import HeardOnly, Sessions, TriggerGate
from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import Fate, Priority, Trigger, TriggerSource

OWNER = Caller(Role.OWNER, "p1", has_personal_device=True)
SYSTEM = Caller(Role.SYSTEM, "p1", has_personal_device=True)

SETTLE_S = 0.1
TIMEOUT_S = 0.3


@dataclass
class Call(DataFrame):
    """Test hattında bir adım; kapıdan önceki kareler işlendikten sonra çalışır."""

    fn: Callable[[], Awaitable[None] | None]


class Steps(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, Call):
            out = frame.fn()
            if out is not None:
                await out
            return
        await self.push_frame(frame, direction)


def make(
    fates: dict[TriggerSource, Fate] | None = None,
    holds: Sequence[Callable[[], bool]] = (),
) -> tuple[Sessions, TriggerGate]:
    turns = Turns(fates or dict.fromkeys(TriggerSource, Fate.CANCEL))
    sessions = Sessions(turns, Priority.NORMAL)
    gate = TriggerGate(
        "s1",
        sessions,
        lambda _: OWNER,
        settle_s=SETTLE_S,
        response_timeout_s=TIMEOUT_S,
        holds=holds,
    )
    return sessions, gate


def trig(
    priority: Priority, source: TriggerSource = TriggerSource.TIMER, content: str = "x"
) -> Trigger:
    return Trigger(
        "s1", priority, source, content, OWNER if source is TriggerSource.TEXT else SYSTEM
    )


async def run(gate: TriggerGate, frames: Sequence[Frame]) -> tuple[list[Frame], list[Frame]]:
    down, up = await run_test(Pipeline([gate, Steps()]), frames_to_send=frames)
    return list(down), list(up)


def appended(frames: Sequence[Frame]) -> list[dict[str, str]]:
    return [m for f in frames if isinstance(f, LLMMessagesAppendFrame) for m in f.messages]  # type: ignore[misc]


def interruptions(frames: Sequence[Frame]) -> int:
    return sum(isinstance(f, InterruptionFrame) for f in frames)


async def test_text_trigger_goes_to_the_model_as_the_users_message() -> None:
    sessions, gate = make()
    down, _ = await run(
        gate,
        [Call(lambda: sessions.submit(trig(Priority.NORMAL, TriggerSource.TEXT, "selam")))],
    )
    assert appended(down) == [{"role": "user", "content": "selam"}]
    assert next(f for f in down if isinstance(f, LLMMessagesAppendFrame)).run_llm


async def test_system_trigger_is_a_labelled_developer_message() -> None:
    sessions, gate = make()
    down, _ = await run(
        gate, [Call(lambda: sessions.submit(trig(Priority.HIGH, content="su iç")))]
    )
    [message] = appended(down)
    assert message["role"] == "developer"
    assert json.loads(message["content"]) == {
        "trigger": "timer",
        "priority": "high",
        "content": "su iç",
    }


async def test_waiting_trigger_starts_when_the_turn_goes_quiet() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="a"))),
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="b"))),
        Call(gate.response_started),
        SleepFrame(SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    # Model cevap yazarken tur sürer; ikinci tetikleyici beklemededir.
    assert [json.loads(m["content"])["content"] for m in appended(down)] == ["a"]

    sessions, gate = make()
    frames = [*frames, Call(gate.response_stopped), SleepFrame(SETTLE_S * 3)]
    down, _ = await run(gate, frames)
    assert [json.loads(m["content"])["content"] for m in appended(down)] == ["a", "b"]


async def test_turn_without_a_response_closes_after_the_timeout() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="a"))),
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="b"))),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    assert [json.loads(m["content"])["content"] for m in appended(down)] == ["a", "b"]


async def test_open_tool_call_and_holds_keep_the_turn_open() -> None:
    held = [True]
    sessions, gate = make(holds=[lambda: held[0]])
    call = FunctionCallFromLLM("note_add", "c1", {}, None)
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="a"))),
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="b"))),
        Call(gate.response_started),
        Call(gate.response_stopped),
        FunctionCallsStartedFrame(function_calls=[call]),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    assert len(appended(down)) == 1

    sessions, gate = make(holds=[lambda: held[0]])
    frames = [
        *frames,
        FunctionCallResultFrame("note_add", "c1", {}, None, None),
        SleepFrame(SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    assert len(appended(down)) == 1  # onay beklenirken de tur açıktır

    held[0] = False
    sessions, gate = make(holds=[lambda: held[0]])
    down, _ = await run(gate, frames)
    assert len(appended(down)) == 2


async def test_higher_priority_cuts_with_pipecats_interruption_and_a_note() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="chat"))),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
    ]
    down, up = await run(gate, frames)
    assert interruptions(down) == 1
    assert interruptions(up) == 1
    messages = appended(down)
    assert json.loads(messages[1]["content"]) == {"interrupted": "timer"}
    assert json.loads(messages[2]["content"])["content"] == "alarm"


async def test_restarted_trigger_is_delivered_again_without_a_note() -> None:
    sessions, gate = make(
        {**dict.fromkeys(TriggerSource, Fate.CANCEL), TriggerSource.TIMER: Fate.RESTART}
    )
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="reminder"))),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    contents = [json.loads(m["content"]).get("content") for m in appended(down)]
    assert contents == ["reminder", "alarm", "reminder"]


# --- ses ---


async def test_speech_opens_a_voice_turn_without_pushing_anything() -> None:
    _, gate = make()
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        TranscriptionFrame("selam", "u", "t"),
        UserStoppedSpeakingFrame(),
    ]
    seen: list[TriggerSource | None] = []

    def look() -> None:
        seen.append(gate.turn.trigger.source if gate.turn else None)

    down, _ = await run(gate, [*frames, Call(look)])
    assert seen == [TriggerSource.VOICE]
    assert appended(down) == []


async def test_identified_owner_is_cut_only_by_urgent() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        TranscriptionFrame("selam", "u", "t"),
        Call(lambda: sessions.submit(trig(Priority.HIGH, content="reminder"))),
    ]
    down, _ = await run(gate, frames)
    assert appended(down) == []


async def test_speech_over_a_lower_turn_is_not_cut_twice() -> None:
    # Söz başlayınca Pipecat zaten keser; kapı ikinci bir kesme yollamaz, akıbeti uygular.
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="chat"))),
        SleepFrame(0.05),  # sistem karesi veri karesini geçmesin
        UserStartedSpeakingFrame(),
    ]
    down, up = await run(gate, frames)
    assert interruptions(down) == interruptions(up) == 0
    assert json.loads(appended(down)[1]["content"]) == {"interrupted": "timer"}


@pytest.mark.parametrize(
    ("priority", "muted"), [(Priority.URGENT, True), (Priority.LOW, False)]
)
async def test_user_is_muted_over_a_higher_priority_turn(
    priority: Priority, muted: bool
) -> None:
    sessions, gate = make()
    strategy = HeardOnly(gate)
    result: list[bool] = []

    async def check() -> None:
        result.append(await strategy.process_frame(UserStartedSpeakingFrame()))

    await run(gate, [Call(lambda: sessions.submit(trig(priority))), Call(check)])
    assert result == [muted]


async def test_restarted_voice_turn_runs_the_model_again() -> None:
    sessions, gate = make(
        {**dict.fromkeys(TriggerSource, Fate.CANCEL), TriggerSource.VOICE: Fate.RESTART}
    )
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
        UserStoppedSpeakingFrame(),
        SleepFrame(TIMEOUT_S * 2 + SETTLE_S * 6),
    ]
    down, _ = await run(gate, frames)
    assert any(isinstance(f, LLMRunFrame) for f in down)
