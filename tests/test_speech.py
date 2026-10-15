"""STT ve TTS servis istemcileri (§3, §7, §14): sahte servislere karşı."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from pipecat.frames.frames import (
    ErrorFrame,
    InputAudioRawFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.tests.utils import SleepFrame, run_test

from mayen.pipeline.speech import ServiceSTT, ServiceTTS, split_parts
from mayen.ports.speech import SCHEMA_VERSION, Part, Transcription


@dataclass
class Fake:
    """Sözleşmeyi konuşan sahte servis; aldığı istekleri tutar."""

    sample_rate: int = 16000
    voices: list[str] = field(default_factory=lambda: ["emma"])
    version: int = SCHEMA_VERSION
    requests: list[Any] = field(default_factory=list)

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/health", self.health)
        app.router.add_post("/transcribe", self.transcribe)
        app.router.add_post("/speak", self.speak)
        return app

    async def health(self, _: web.Request) -> web.Response:
        return web.json_response(
            {
                "schema_version": self.version,
                "sample_rate": self.sample_rate,
                "voices": self.voices,
            }
        )

    async def transcribe(self, request: web.Request) -> web.Response:
        body = await request.read()
        self.requests.append((dict(request.query), len(body)))
        return web.json_response(
            {
                "schema_version": self.version,
                "text": " hello ",
                "language": "en",
                "segments": [{"text": " hello ", "no_speech_prob": 0.1, "avg_logprob": -0.2}],
            }
        )

    async def speak(self, request: web.Request) -> web.StreamResponse:
        self.requests.append(await request.json())
        response = web.StreamResponse()
        await response.prepare(request)
        # Tek sayıda bayt: örnek ortadan bölünür, istemci yarımı sonrakine taşımalı.
        await response.write(b"\x01" * 3201)
        await response.write(b"\x01" * 3199)
        await response.write_eof()
        return response


@pytest.fixture
async def fake() -> AsyncIterator[tuple[Fake, str]]:
    service = Fake()
    server = TestServer(service.app())
    await server.start_server()
    try:
        yield service, str(server.make_url("")).rstrip("/")
    finally:
        await server.close()


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


async def test_stt_turns_a_segment_into_text(fake: tuple[Fake, str]) -> None:
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
    fake: tuple[Fake, str],
) -> None:
    service, url = fake
    service.version = SCHEMA_VERSION + 1
    _, up = await run_test(ServiceSTT(url, None), frames_to_send=[SleepFrame(0.1)])
    errors = [f for f in up if isinstance(f, ErrorFrame)]
    assert errors and "schema_version" in errors[0].error


async def test_tts_streams_audio_in_the_language_voice(fake: tuple[Fake, str]) -> None:
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
    fake: tuple[Fake, str],
) -> None:
    service, url = fake
    tts = ServiceTTS(url, {"English": "emma"}, lambda: "Türkçe", sample_rate=16000)
    _, up = await run_test(tts, frames_to_send=[TTSSpeakFrame("Merhaba."), SleepFrame(0.2)])
    assert any("Türkçe" in f.error for f in up if isinstance(f, ErrorFrame))
    assert service.requests == []


async def test_tts_with_a_missing_voice_fails_at_start(fake: tuple[Fake, str]) -> None:
    _, url = fake
    tts = ServiceTTS(url, {"English": "brian"}, lambda: "English", sample_rate=16000)
    _, up = await run_test(tts, frames_to_send=[SleepFrame(0.1)])
    assert any("brian" in f.error for f in up if isinstance(f, ErrorFrame))
