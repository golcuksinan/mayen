"""Gözlemciden olay üretimi (§5.5): her kare bir kez, gövde yalnızca olay kaydında."""

import logging
import uuid

import pytest
from pipecat.frames.frames import Frame, MetricsFrame
from pipecat.metrics.metrics import LLMTokenUsage, LLMUsageMetricsData
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.tests.utils import run_test

from fakes import FakeClock, MemoryEventLog
from mayen.core.events import Recorder
from mayen.pipeline.events import EventObserver, SessionEvents
from mayen.ports.events import EventKind
from mayen.ports.triggers import TurnId

TURN = TurnId(uuid.uuid4())


class Passing(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)


async def test_token_counts_become_events_once(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    log = MemoryEventLog()
    events = SessionEvents(Recorder(log, FakeClock()), "s1", lambda: TURN)
    usage = LLMUsageMetricsData(
        processor="llm",
        model="m",
        value=LLMTokenUsage(prompt_tokens=120, completion_tokens=8, total_tokens=128),
    )
    # Birkaç işlemciden geçen kare yine tek olaydır.
    await run_test(
        Pipeline([Passing(), Passing(), Passing()]),
        frames_to_send=[MetricsFrame([usage])],
        observers=[EventObserver(events)],
    )

    [tokens] = log.events
    assert tokens.header.kind is EventKind.LLM_USAGE
    assert tokens.body["completion_tokens"] == 8
    assert tokens.header.turn_id == TURN
    assert "completion_tokens" not in caplog.text
