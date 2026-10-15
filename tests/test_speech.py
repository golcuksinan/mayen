"""STT ve TTS servis istemcileri (§3, §7, §14): sahte servislere karşı."""

import asyncio
import struct
from collections.abc import AsyncIterator
from typing import Any

import pytest
from pipecat.frames.frames import (
    ErrorFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.tests.utils import SleepFrame, run_test

from fakes import FakeSpeech, speech_service
from mayen.pipeline.sounds import ToolSound
from mayen.pipeline.speech import ServiceSTT, ServiceTTS, ServiceVAD, split_parts
from mayen.ports.speech import SCHEMA_VERSION, VAD_FRAME, Part, Transcription


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
        ServiceSTT(url, "en"), frames_to_send=[*_speech(), SleepFrame(0.3)]
    )
    texts = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert [(t.text, str(t.language)) for t in texts] == [("hello", "en")]
    result = texts[0].result
    assert isinstance(result, Transcription) and result.segments[0].avg_logprob == -0.2
    assert service.requests[0][0] == {"language": "en"}


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
