"""Mayen'in sözü transkripte (§11): toplayıcının söylediği, kesildiyse söylediği kadarı."""

import uuid

from pipecat.frames.frames import (
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMAssistantAggregator
from pipecat.tests.utils import SleepFrame, run_test

from fakes import MemoryEventLog, MemoryTranscript, transcript
from mayen.app.wiring import _bind_response
from mayen.core.events import Recorder, SystemClock
from mayen.core.transcript import Transcript
from mayen.core.turns import Turns
from mayen.pipeline.events import SessionTranscript
from mayen.pipeline.session import UNIDENTIFIED, Sessions, TriggerGate
from mayen.pipeline.text import TextOutput
from mayen.ports.transcript import Party
from mayen.ports.triggers import Fate, Priority, TriggerSource, TurnId

TURN = TurnId(uuid.uuid4())


def bound(store_and_writer: tuple[Transcript, MemoryTranscript]) -> LLMAssistantAggregator:
    writer, _ = store_and_writer
    sessions = Sessions(Turns(dict.fromkeys(TriggerSource, Fate.CANCEL)), Priority.NORMAL)
    gate = TriggerGate(
        "s1",
        sessions,
        lambda _: UNIDENTIFIED,
        Recorder(MemoryEventLog(), SystemClock()),
        SessionTranscript(writer, "s1", lambda: TURN),
        settle_s=0.1,
        response_timeout_s=0.3,
    )
    assistant = LLMAssistantAggregator(LLMContext())
    _bind_response(assistant, gate, SessionTranscript(writer, "s1", lambda: TURN))
    return assistant


async def test_reply_is_written_once_and_tool_only_reply_is_not() -> None:
    pair = transcript()
    _, store = pair
    assistant = bound(pair)
    await run_test(
        assistant,
        frames_to_send=[
            LLMFullResponseStartFrame(),
            LLMFullResponseEndFrame(),  # yalnızca tool çağıran cevap: söz yok
            LLMFullResponseStartFrame(),
            LLMTextFrame("Note "),
            LLMTextFrame("deleted."),
            LLMFullResponseEndFrame(),
            LLMFullResponseStartFrame(),
            LLMTextFrame("I will"),
            SleepFrame(0.05),
            InterruptionFrame(),
        ],
    )
    assert [(u.text, u.interrupted) for u in store.utterances] == [
        ("Note deleted.", False),
        ("I will", True),
    ]
    assert {(u.party, u.role, u.turn_id) for u in store.utterances} == {
        (Party.ASSISTANT, None, TURN)
    }


async def test_question_asked_in_writing_reaches_history_and_transcript() -> None:
    # Yazılı hatta TTS yok; soruyu geçmişe ve transkripte TextOutput işler.
    pair = transcript()
    _, store = pair
    assistant = bound(pair)
    await run_test(
        Pipeline([TextOutput(), assistant]),
        frames_to_send=[TTSSpeakFrame("Delete note 5?", append_to_context=True)],
    )
    assert assistant.context.messages == [{"role": "assistant", "content": "Delete note 5?"}]
    assert [u.text for u in store.utterances] == ["Delete note 5?"]
