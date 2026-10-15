"""Gözlemciden olay üretimi (§5.5): her kare bir kez, söz yalnızca transkriptte (§11)."""

import logging
import uuid

import pytest
from pipecat.frames.frames import Frame, MetricsFrame, TranscriptionFrame
from pipecat.metrics.metrics import LLMTokenUsage, LLMUsageMetricsData
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.tests.utils import run_test

from fakes import FakeClock, MemoryEventLog, transcript
from mayen.core.events import Recorder
from mayen.pipeline.events import EventObserver, SessionEvents, SessionTranscript
from mayen.ports.events import EventKind
from mayen.ports.tools import Caller, Role
from mayen.ports.transcript import Party
from mayen.ports.triggers import TurnId

TURN = TurnId(uuid.uuid4())
OWNER = Caller(Role.OWNER, "1", has_personal_device=True)


class Passing(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)


async def test_segments_and_token_counts_become_events_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    log = MemoryEventLog()
    events = SessionEvents(Recorder(log, FakeClock()), "s1", lambda: TURN)
    writer, store = transcript()
    heard = SessionTranscript(writer, "s1", lambda: TURN)
    usage = LLMUsageMetricsData(
        processor="llm",
        model="m",
        value=LLMTokenUsage(prompt_tokens=120, completion_tokens=8, total_tokens=128),
    )
    # Birkaç işlemciden geçen kare yine tek olaydır.
    await run_test(
        Pipeline([Passing(), Passing(), Passing()]),
        frames_to_send=[TranscriptionFrame("yarın sabah", "p1", ""), MetricsFrame([usage])],
        observers=[EventObserver(events, heard, lambda _: OWNER)],
    )

    assert log.kinds() == [EventKind.STT_SEGMENT, EventKind.LLM_USAGE]
    segment, tokens = log.events
    [utterance] = store.utterances
    assert (utterance.text, utterance.party, utterance.role) == (
        "yarın sabah",
        Party.PERSON,
        Role.OWNER,
    )
    assert (utterance.session, utterance.turn_id, utterance.person_id) == ("s1", TURN, "1")
    # Olay söze kimliğiyle bağlanır; metin iki yerde tutulmaz (§11).
    assert segment.header.related == (str(utterance.id),)
    assert "yarın sabah" not in str(segment.body)
    assert tokens.body["completion_tokens"] == 8
    assert {e.header.turn_id for e in log.events} == {TURN}
    assert "yarın sabah" not in caplog.text
