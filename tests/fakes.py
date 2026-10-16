"""Testlerin ortak sahteleri: saat, bellekte olay kaydı, transkript ve ses servisleri."""

import asyncio
import struct
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer

from mayen.core.events import Recorder
from mayen.core.transcript import Transcript
from mayen.pipeline.events import SessionTranscript
from mayen.pipeline.session import Sessions
from mayen.ports.events import Event, EventKind
from mayen.ports.speech import SCHEMA_VERSION, VAD_FRAME, WAKE_FRAME
from mayen.ports.transcript import Utterance
from mayen.ports.triggers import TurnId

T0 = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, start: datetime = T0) -> None:
        self.wall = start
        self.mono = 0.0

    def now(self) -> datetime:
        return self.wall

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


class MemoryEventLog:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def append(self, event: Event) -> None:
        self.events.append(event)

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Event]:
        return list(self.events)

    def kinds(self) -> list[EventKind]:
        return [e.header.kind for e in self.events]

    def of(self, kind: EventKind) -> list[Event]:
        return [e for e in self.events if e.header.kind is kind]


def recorder() -> tuple[Recorder, MemoryEventLog]:
    log = MemoryEventLog()
    return Recorder(log, FakeClock()), log


class MemoryTranscript:
    def __init__(self) -> None:
        self.utterances: list[Utterance] = []

    def append(self, utterance: Utterance) -> None:
        self.utterances.append(utterance)

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Utterance]:
        return list(self.utterances)


def transcript() -> tuple[Transcript, MemoryTranscript]:
    store = MemoryTranscript()
    return Transcript(store, FakeClock()), store


def session_transcript(
    sessions: Sessions, session: str = "s1"
) -> tuple[SessionTranscript, MemoryTranscript]:
    """Oturumun transkripti; tur kimliği, wiring'deki gibi oturumun süren turundan."""
    writer, store = transcript()

    def turn_id() -> TurnId | None:
        turn = sessions.running(session)
        return None if turn is None else turn.id

    return SessionTranscript(writer, session, turn_id), store


@dataclass
class FakeSpeech:
    """STT ve TTS sözleşmesini konuşan sahte servis (§3); aldığı istekleri tutar."""

    sample_rate: int = 16000
    voices: list[str] = field(default_factory=lambda: ["emma"])
    version: int = SCHEMA_VERSION
    requests: list[Any] = field(default_factory=list)
    vad_frame: int = VAD_FRAME
    vad_connections: int = 0
    turn_delay_s: float = 0.0
    wake_model: bool = True
    embed_model: str = "ecapa"
    embed_vector: list[float] = field(default_factory=lambda: [0.6, 0.8])

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/health", self.health)
        app.router.add_post("/transcribe", self.transcribe)
        app.router.add_post("/speak", self.speak)
        app.router.add_get("/vad", self.vad)
        app.router.add_post("/turn", self.turn)
        app.router.add_get("/wake", self.wake)
        app.router.add_post("/embed", self.embed)
        return app

    async def embed(self, request: web.Request) -> web.Response:
        body = await request.read()
        self.requests.append(("embed", len(body)))
        return web.json_response(
            {
                "schema_version": self.version,
                "model": self.embed_model,
                "vector": self.embed_vector,
            }
        )

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

    async def vad(self, request: web.Request) -> web.WebSocketResponse:
        """Olasılık, parçanın ilk örneğinin büyüklüğü: test sesi kendisi seçer."""
        self.vad_connections += 1
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json(
            {
                "schema_version": self.version,
                "sample_rate": self.sample_rate,
                "frame": self.vad_frame,
            }
        )
        async for message in ws:
            if message.type is WSMsgType.BINARY:
                first = struct.unpack_from("<h", message.data)[0]
                await ws.send_bytes(struct.pack("<f", first / 32767))
        return ws

    async def wake(self, request: web.Request) -> web.WebSocketResponse:
        """Puan, parçanın ilk örneğinin büyüklüğü (VAD gibi); model yoksa selamsız kapanır."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        if not self.wake_model:
            await ws.close(code=1011, message=b"no wake word model")
            return ws
        hello = {"schema_version": self.version, "sample_rate": self.sample_rate}
        await ws.send_json({**hello, "frame": WAKE_FRAME})
        async for message in ws:
            if message.type is WSMsgType.BINARY:
                first = struct.unpack_from("<h", message.data)[0]
                await ws.send_bytes(struct.pack("<f", first / 32767))
        return ws

    async def turn(self, request: web.Request) -> web.Response:
        """Olasılık, sesin son örneğinin büyüklüğü: test sesi kendisi seçer."""
        body = await request.read()
        self.requests.append((dict(request.query), len(body)))
        await asyncio.sleep(self.turn_delay_s)
        last = struct.unpack_from("<h", body, len(body) - 2)[0]
        return web.json_response({"schema_version": self.version, "probability": last / 32767})

    async def speak(self, request: web.Request) -> web.StreamResponse:
        self.requests.append(await request.json())
        response = web.StreamResponse()
        await response.prepare(request)
        # Tek sayıda bayt: örnek ortadan bölünür, istemci yarımı sonrakine taşımalı.
        await response.write(b"\x01" * 3201)
        await response.write(b"\x01" * 3199)
        await response.write_eof()
        return response


@asynccontextmanager
async def speech_service() -> AsyncIterator[tuple[FakeSpeech, str]]:
    """Ayakta bir sahte ses servisi ve adresi."""
    service = FakeSpeech()
    server = TestServer(service.app())
    await server.start_server()
    try:
        yield service, str(server.make_url("")).rstrip("/")
    finally:
        await server.close()
