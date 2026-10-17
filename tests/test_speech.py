"""STT ve TTS servis istemcileri (§3, §7, §14): sahte servislere karşı."""

import asyncio
import struct
from collections.abc import AsyncIterator
from typing import Any

import numpy as np
import pytest
from pipecat.audio.turn.base_turn_analyzer import (
    BaseTurnAnalyzer,
    BaseTurnParams,
    EndOfTurnState,
)
from pipecat.audio.turn.smart_turn.base_smart_turn import (
    SmartTurnParams,
    SmartTurnTimeoutException,
)
from pipecat.frames.frames import (
    ErrorFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    UserStartedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import MetricsData
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMUserAggregator,
    LLMUserAggregatorParams,
)
from pipecat.tests.utils import SleepFrame, run_test
from pipecat.turns.user_start import VADUserTurnStartStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from fakes import FakeSpeech, speech_service
from mayen.pipeline.sounds import ToolSound
from mayen.pipeline.speech import (
    VOICE,
    ServiceSpeaker,
    ServiceSTT,
    ServiceTTS,
    ServiceTurn,
    ServiceVAD,
    TurnEndSignal,
    TurnEndToStt,
    split_parts,
)
from mayen.ports.speech import SCHEMA_VERSION, VAD_FRAME, Embedding, Part, Transcription


@pytest.fixture
async def fake() -> AsyncIterator[tuple[FakeSpeech, str]]:
    async with speech_service() as running:
        yield running


def test_split_parts_carries_an_open_tag() -> None:
    parts, open_tag = split_parts("Your note for <tr>Ayşe", None)
    assert parts == [Part(None, "Your note for "), Part("tr", "Ayşe")]
    assert open_tag == "tr"
    parts, open_tag = split_parts("Hanım</tr> is saved.", open_tag)
    assert parts == [Part("tr", "Hanım"), Part(None, " is saved.")]
    assert open_tag is None


def test_a_lone_tag_has_nothing_to_read() -> None:
    assert split_parts("</tr>", "tr") == ([], None)


def _speech() -> list[Any]:
    audio = InputAudioRawFrame(audio=b"\x00\x00" * 1600, sample_rate=16000, num_channels=1)
    return [VADUserStartedSpeakingFrame(), audio, audio, VADUserStoppedSpeakingFrame()]


async def test_stt_turns_a_segment_into_text(fake: tuple[FakeSpeech, str]) -> None:
    service, url = fake
    down, _ = await run_test(
        ServiceSTT(url, "en", join_turn_s=0), frames_to_send=[*_speech(), SleepFrame(0.3)]
    )
    texts = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert [(t.text, str(t.language)) for t in texts] == [("hello", "en")]
    result = texts[0].result
    assert isinstance(result, Transcription) and result.segments[0].avg_logprob == -0.2
    assert service.requests[0][0] == {"language": "en"}


_SEGMENT = 2 * 1600 * 2  # `_speech()`'in iki ses karesi, bayt


def _transcribed(service: FakeSpeech) -> list[int]:
    return [n for query, n in service.requests if isinstance(query, dict)]


async def test_stt_transcribes_a_turn_as_one_piece(fake: tuple[FakeSpeech, str]) -> None:
    service, url = fake
    down, _ = await run_test(
        ServiceSTT(url, "en", join_turn_s=0),
        frames_to_send=[
            UserStartedSpeakingFrame(),
            *_speech(),
            SleepFrame(0.1),
            *_speech(),
            SleepFrame(0.1),
            TurnEndSignal(),
            SleepFrame(0.3),
        ],
    )
    texts = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert [t.text for t in texts] == ["hello"] and texts[0].finalized
    [size] = _transcribed(service)
    assert size > 2 * _SEGMENT  # iki parça ve aralarındaki ses birlikte


async def test_a_word_that_ended_just_before_the_turn_opens_its_start(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    down, _ = await run_test(
        ServiceSTT(url, "en", join_turn_s=0.5),
        frames_to_send=[
            *_speech(),  # "Hey Mayen": wake word turu sözün bitişinden sonra açar
            SleepFrame(0.1),
            UserStartedSpeakingFrame(),
            *_speech(),
            TurnEndSignal(),
            SleepFrame(0.8),
        ],
    )
    assert len([f for f in down if isinstance(f, TranscriptionFrame)]) == 1
    [size] = _transcribed(service)
    assert size > 2 * _SEGMENT


async def test_outside_a_turn_each_word_is_still_transcribed(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    down, _ = await run_test(
        ServiceSTT(url, "en", join_turn_s=0.1),
        frames_to_send=[*_speech(), SleepFrame(0.3), *_speech(), SleepFrame(0.3)],
    )
    assert len([f for f in down if isinstance(f, TranscriptionFrame)]) == 2
    assert len(_transcribed(service)) == 2


async def test_stt_sends_the_same_words_to_the_speaker_service(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    stt = ServiceSTT(url, "en", ServiceSpeaker(url), join_turn_s=0)
    down, _ = await run_test(stt, frames_to_send=[*_speech(), SleepFrame(0.3)])
    [text] = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert text.metadata[VOICE] == Embedding("ecapa", (0.6, 0.8))
    sizes = [n for kind, n in service.requests if kind == "embed"]
    assert sizes and sizes[0] == service.requests[0][1]  # aynı ses, aynı hızda


async def test_unreachable_speaker_service_leaves_the_words_without_a_voice(
    fake: tuple[FakeSpeech, str],
) -> None:
    _, url = fake
    stt = ServiceSTT(url, "en", ServiceSpeaker("http://127.0.0.1:9"), join_turn_s=0)
    down, _ = await run_test(stt, frames_to_send=[*_speech(), SleepFrame(0.3)])
    [text] = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert text.text == "hello" and text.metadata[VOICE] is None


async def test_stt_with_another_contract_version_fails_loudly(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    service.version = SCHEMA_VERSION + 1
    _, up = await run_test(ServiceSTT(url, None), frames_to_send=[SleepFrame(0.1)])
    errors = [f for f in up if isinstance(f, ErrorFrame)]
    assert errors and "schema_version" in errors[0].error


async def test_tts_streams_audio_in_the_language_voice(fake: tuple[FakeSpeech, str]) -> None:
    service, url = fake
    tts = ServiceTTS(url, {"English": "emma"}, lambda: "English", sample_rate=16000)
    down, _ = await run_test(
        tts, frames_to_send=[TTSSpeakFrame("Saved for <tr>Ayşe</tr>."), SleepFrame(0.3)]
    )
    audio = b"".join(f.audio for f in down if isinstance(f, TTSAudioRawFrame))
    assert len(audio) == 6400  # yarım örnek kaybolmadı, araya bayt girmedi
    assert service.requests == [
        {
            "schema_version": SCHEMA_VERSION,
            "voice": "emma",
            "parts": [
                {"language": None, "text": "Saved for "},
                {"language": "tr", "text": "Ayşe"},
                {"language": None, "text": "."},
            ],
        }
    ]


async def test_tts_without_a_voice_for_the_language_is_an_error(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    tts = ServiceTTS(url, {"English": "emma"}, lambda: "Türkçe", sample_rate=16000)
    _, up = await run_test(tts, frames_to_send=[TTSSpeakFrame("Merhaba."), SleepFrame(0.2)])
    assert any("Türkçe" in f.error for f in up if isinstance(f, ErrorFrame))
    assert service.requests == []


async def test_tts_with_a_missing_voice_fails_at_start(fake: tuple[FakeSpeech, str]) -> None:
    _, url = fake
    tts = ServiceTTS(url, {"English": "brian"}, lambda: "English", sample_rate=16000)
    _, up = await run_test(tts, frames_to_send=[SleepFrame(0.1)])
    assert any("brian" in f.error for f in up if isinstance(f, ErrorFrame))


def _frame(level: int) -> bytes:
    return struct.pack("<h", level) * VAD_FRAME


async def test_vad_takes_the_confidence_from_the_service(fake: tuple[FakeSpeech, str]) -> None:
    service, url = fake
    vad = ServiceVAD(url)
    vad.set_sample_rate(16000)
    loud = await asyncio.to_thread(vad.voice_confidence, _frame(32767))
    quiet = await asyncio.to_thread(vad.voice_confidence, _frame(0))
    await vad.cleanup()
    assert (loud, quiet) == (1.0, 0.0)
    assert service.vad_connections == 1  # akış tek bağlantıda; model durumu ona ait


async def test_vad_with_another_frame_size_hears_nothing_and_retries_slowly(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    service.vad_frame = VAD_FRAME * 2
    vad = ServiceVAD(url)
    vad.set_sample_rate(16000)
    for _ in range(3):
        assert await asyncio.to_thread(vad.voice_confidence, _frame(32767)) == 0.0
    await vad.cleanup()
    assert service.vad_connections == 1  # her parçada yeniden bağlanmıyor


async def test_vad_without_a_service_hears_nothing() -> None:
    vad = ServiceVAD("http://127.0.0.1:9")
    vad.set_sample_rate(16000)
    assert await asyncio.to_thread(vad.voice_confidence, _frame(32767)) == 0.0


def _ending(level: float) -> np.ndarray:
    audio = np.zeros(16000, np.float32)
    audio[-1] = level
    return audio


async def test_turn_takes_the_probability_from_the_service(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    turn = ServiceTurn(url)
    turn.set_sample_rate(16000)
    done = await asyncio.to_thread(turn._predict_endpoint, _ending(0.9))
    open_ = await asyncio.to_thread(turn._predict_endpoint, _ending(0.1))
    assert (done["prediction"], open_["prediction"]) == (1, 0)
    assert done["probability"] == pytest.approx(0.9, abs=1e-3)
    # Ses 16 bit PCM olarak, hızıyla gider.
    assert service.requests == [({"sample_rate": "16000"}, 32000)] * 2


async def test_turn_with_another_contract_version_is_not_finished(
    fake: tuple[FakeSpeech, str],
) -> None:
    service, url = fake
    service.version = SCHEMA_VERSION + 1
    turn = ServiceTurn(url)
    turn.set_sample_rate(16000)
    assert (await asyncio.to_thread(turn._predict_endpoint, _ending(0.9)))["prediction"] == 0


async def test_turn_without_a_service_is_not_finished() -> None:
    turn = ServiceTurn("http://127.0.0.1:9")
    turn.set_sample_rate(16000)
    assert (await asyncio.to_thread(turn._predict_endpoint, _ending(0.9)))["prediction"] == 0


async def test_turn_waiting_past_the_silence_is_finished(fake: tuple[FakeSpeech, str]) -> None:
    service, url = fake
    service.turn_delay_s = 0.5
    turn = ServiceTurn(url, params=SmartTurnParams(stop_secs=0.1))
    turn.set_sample_rate(16000)
    with pytest.raises(SmartTurnTimeoutException):
        await asyncio.to_thread(turn._predict_endpoint, _ending(0.1))


async def test_tool_sound_is_short_and_at_the_output_rate() -> None:
    sound = ToolSound()

    async def blip_after_start() -> None:
        await asyncio.sleep(0.05)
        await sound.play()

    task = asyncio.create_task(blip_after_start())
    down, _ = await run_test(sound, frames_to_send=[SleepFrame(0.2)])
    await task
    [blip] = [f for f in down if isinstance(f, OutputAudioRawFrame)]
    assert blip.sample_rate == 24000  # run_test'in çıkış hızı
    assert len(blip.audio) == 2 * int(24000 * 0.13)


class _CompleteAtSilence(BaseTurnAnalyzer):
    """Her sessizlikte "bitti" der; Smart Turn'ün yerine."""

    @property
    def speech_triggered(self) -> bool:
        return False

    @property
    def params(self) -> BaseTurnParams:
        return BaseTurnParams()

    def append_audio(self, buffer: bytes, is_speech: bool) -> EndOfTurnState:
        return EndOfTurnState.INCOMPLETE

    async def analyze_end_of_turn(self) -> tuple[EndOfTurnState, MetricsData | None]:
        return EndOfTurnState.COMPLETE, None

    def clear(self) -> None:
        pass


async def test_the_turn_decision_reaches_the_stt_once() -> None:
    user = LLMUserAggregator(
        LLMContext(),
        params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                start=[VADUserTurnStartStrategy()],
                stop=[TurnEndToStt(turn_analyzer=_CompleteAtSilence())],
            ),
        ),
    )
    _, up = await run_test(
        user, frames_to_send=[*_speech(), SleepFrame(0.1)], expected_up_frames=None
    )
    assert len([f for f in up if isinstance(f, TurnEndSignal)]) == 1
