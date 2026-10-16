"""Wake word (§6) ve sözün tur açıp açmadığı (§5.1): sahte servise karşı ve tek başına."""

import logging
import struct
from collections.abc import AsyncIterator

import pytest
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InputAudioRawFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
)
from pipecat.tests.utils import SleepFrame, run_test
from pipecat.turns.types import ProcessFrameResult

from fakes import FakeClock, FakeSpeech, speech_service
from mayen.pipeline.wake import ServiceWake, WakeStart, WakeWordFrame
from mayen.ports.speech import WAKE_FRAME


@pytest.fixture
async def fake() -> AsyncIterator[tuple[FakeSpeech, str]]:
    async with speech_service() as running:
        yield running


def _audio(level: float) -> InputAudioRawFrame:
    """Bir model adımı; sahte servisin puanı ilk örneğin büyüklüğüdür."""
    first = struct.pack("<h", int(level * 32767))
    return InputAudioRawFrame(
        audio=first + b"\x00\x00" * (WAKE_FRAME - 1), sample_rate=16000, num_channels=1
    )


async def test_wake_word_is_signalled_once_per_crossing(fake: tuple[FakeSpeech, str]) -> None:
    _, url = fake
    levels = [0.1, 0.9, 0.95, 0.2, 0.8]
    down, _ = await run_test(
        ServiceWake(url, threshold=0.5),
        frames_to_send=[*(_audio(v) for v in levels), SleepFrame(0.5)],
    )
    wakes = [f for f in down if isinstance(f, WakeWordFrame)]
    # Model aynı söz boyunca birkaç adım yüksek kalır; işaret eşiği her geçişte bir kez.
    assert [round(w.score, 2) for w in wakes] == [0.9, 0.8]
    assert sum(isinstance(f, InputAudioRawFrame) for f in down) == len(levels)


async def test_audio_split_across_frames_reaches_the_model_whole(
    fake: tuple[FakeSpeech, str],
) -> None:
    _, url = fake
    step = _audio(0.9).audio
    halves = [
        InputAudioRawFrame(audio=part, sample_rate=16000, num_channels=1)
        for part in (step[:1000], step[1000:])
    ]
    down, _ = await run_test(
        ServiceWake(url, threshold=0.5), frames_to_send=[*halves, SleepFrame(0.5)]
    )
    assert len([f for f in down if isinstance(f, WakeWordFrame)]) == 1


async def test_without_a_wake_model_audio_flows_and_nobody_wakes(
    fake: tuple[FakeSpeech, str], caplog: pytest.LogCaptureFixture
) -> None:
    service, url = fake
    service.wake_model = False
    with caplog.at_level(logging.ERROR):
        down, _ = await run_test(
            ServiceWake(url, threshold=0.5), frames_to_send=[_audio(0.9), SleepFrame(0.3)]
        )
    assert not [f for f in down if isinstance(f, WakeWordFrame)]
    assert any(isinstance(f, InputAudioRawFrame) for f in down)
    assert "wake word service" in caplog.text


class Running:
    def __init__(self) -> None:
        self.value = False

    def __call__(self) -> bool:
        return self.value


async def _strategy(clock: FakeClock, running: Running) -> tuple[WakeStart, list[str]]:
    seen: list[str] = []
    strategy = WakeStart(running, follow_up_s=3.0, clock=clock.monotonic)

    async def started(_: object, __: object) -> None:
        seen.append("started")

    async def reset(_: object) -> None:
        seen.append("reset")

    strategy.add_event_handler("on_user_turn_started", started)
    strategy.add_event_handler("on_reset_aggregation", reset)
    return strategy, seen


async def test_speech_without_wake_word_opens_no_turn_and_reaches_no_model() -> None:
    clock, running = FakeClock(), Running()
    strategy, seen = await _strategy(clock, running)
    speech = VADUserStartedSpeakingFrame()
    assert await strategy.process_frame(speech) is ProcessFrameResult.STOP
    text = TranscriptionFrame("çay koyayım mı", "u", "t")
    assert await strategy.process_frame(text) is ProcessFrameResult.STOP
    # Söz transkripte girer (kapı yazar) ama toplayıcıdan silinir: modele gitmez.
    assert seen == ["reset"]


async def test_wake_word_opens_a_turn() -> None:
    clock, running = FakeClock(), Running()
    strategy, seen = await _strategy(clock, running)
    assert await strategy.process_frame(WakeWordFrame(score=0.9)) is ProcessFrameResult.STOP
    assert seen == ["started"]


async def test_speech_in_a_running_turn_goes_on() -> None:
    clock, running = FakeClock(), Running()
    strategy, _ = await _strategy(clock, running)
    running.value = True
    frame = VADUserStartedSpeakingFrame()
    assert await strategy.process_frame(frame) is ProcessFrameResult.CONTINUE


async def test_follow_up_counts_from_when_speech_starts() -> None:
    clock, running = FakeClock(), Running()
    strategy, _ = await _strategy(clock, running)
    await strategy.process_frame(BotStartedSpeakingFrame())
    # Asistan konuşurken söz kesme serbest (§5.4).
    assert strategy.awake()
    await strategy.process_frame(BotStoppedSpeakingFrame())
    clock.advance(2.9)
    # Pencerenin son anında başlayan söz pencerenindir; yazıya dökülmesi sonra gelir.
    frame = VADUserStartedSpeakingFrame()
    assert await strategy.process_frame(frame) is ProcessFrameResult.CONTINUE
    clock.advance(0.2)
    assert await strategy.process_frame(frame) is ProcessFrameResult.STOP
