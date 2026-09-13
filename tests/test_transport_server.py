"""WebSocket sunucusu testleri (§13).

Gerçek soket üzerinden koşuyor: `serve` ile bir gevşek bağlantı noktası açılıyor ve
istemci `websockets`'in kendi istemcisi. Sahte bir soket, tam da bu paketin işi olan
şeyi — el sıkışma, kodlama, sıralı yazma — atlardı. GPU yok, model yok, saniyenin
altında bitiyor.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from mayen.adapters.audio import AudioFormat, Codec
from mayen.session.actor import ActiveTurn, Session
from mayen.session.state import State
from mayen.transport.frames import (
    PROTOCOL_VERSION,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ErrorFrame,
    Frame,
    Hello,
    Interrupt,
    Ping,
    Pong,
    Rejected,
    SpeechSegment,
    StateChanged,
    TextSegment,
    ToolRunning,
    Transcript,
    Welcome,
)
from mayen.transport.server import Connections, FrameSink, Server
from mayen.transport.wire import decode, encode
from mayen.turn.report import TurnReport

FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)
TIMEOUT = 2.0


class ScriptedRunner:
    """Turu sahte bir koşucuyla yürütür: transkript, bir ses parçası, bitiş.

    Sunucunun ölçtüğü şey yönlendirme; gerçek `turn.Runner` burada ne bir şey ekler ne
    de çıkarır, ama STT/TTS sahtelerini de sürüklerdi.
    """

    def __init__(self, sink: FrameSink, *, chunks: int = 1, tool: str | None = None) -> None:
        self._sink = sink
        self._chunks = chunks
        self._tool = tool
        self.started = asyncio.Event()
        #: `DÜŞÜNÜYOR`'da tutar (ses başlamadan önce).
        #: `ÇÖZÜMLÜYOR`'da tutar (transkriptten sonra, `understood`'dan önce).
        self.resolving = asyncio.Event()
        self.resolving.set()
        self.thinking = asyncio.Event()
        self.thinking.set()
        #: `KONUŞUYOR`'da tutar (ilk parçadan sonra).
        self.release = asyncio.Event()
        self.release.set()
        self.turn_ids: list[str] = []

    async def run(self, turn: ActiveTurn, report: TurnReport) -> None:
        self.turn_ids.append(turn.turn_id)
        self.started.set()
        text = turn.segment.payload if isinstance(turn.segment.payload, str) else "ses"
        await self._sink.transcript(turn.turn_id, turn.segment.segment_id, text)
        await self.resolving.wait()
        await report.understood()
        if self._tool is not None:
            await self._sink.tool_running(turn.turn_id, self._tool)
        await self.thinking.wait()
        for seq in range(self._chunks):
            await self._sink.audio_chunk(turn.turn_id, seq, FORMAT, b"\x00\x01")
            if seq == 0:
                await report.speaking()
                # Kapı ilk parçadan **sonra**: söz kesme ancak `KONUŞUYOR`'da tanımlı
                # (§5). `DÜŞÜNÜYOR`'da barge-in tabloda hâlâ açık — P4'ten devreden
                # doküman kararı; testin onu varsayımla kapatması olmaz.
                await self.release.wait()
        await self._sink.audio_end(turn.turn_id)
        await report.spoke()


@asynccontextmanager
async def running(
    make_runner: "type[ScriptedRunner] | None" = None, **kwargs: object
) -> AsyncIterator[tuple[int, Session, ScriptedRunner]]:
    """Sunucuyu gevşek bir bağlantı noktasında ayağa kaldırır."""
    connections = Connections()
    sink = FrameSink(connections)
    runner = (make_runner or ScriptedRunner)(sink, **kwargs)  # type: ignore[arg-type]
    session = Session(runner, sink)
    sink.attach(session)
    server = Server(session, connections)
    websocket = await server.serve("127.0.0.1", 0)
    port = websocket.sockets[0].getsockname()[1]
    try:
        yield port, session, runner
    finally:
        websocket.close()
        await websocket.wait_closed()
        await session.close()


async def handshake(
    port: int, device_id: str = "dev1", version: int = PROTOCOL_VERSION
) -> tuple[ClientConnection, Frame]:
    socket = await connect(f"ws://127.0.0.1:{port}")
    await socket.send(encode(Hello(protocol_version=version, device_id=device_id)))
    return socket, await recv(socket)


@asynccontextmanager
async def client(port: int, device_id: str = "dev1") -> AsyncIterator[ClientConnection]:
    socket, answer = await handshake(port, device_id)
    assert isinstance(answer, Welcome)
    try:
        yield socket
    finally:
        await socket.close()


async def recv(socket: ClientConnection) -> Frame:
    async with asyncio.timeout(TIMEOUT):
        return decode(await socket.recv())


async def expect[T: Frame](socket: ClientConnection, kind: type[T]) -> T:
    """Aradaki durum çerçevelerini atlayarak beklenen tipi bulur."""
    async with asyncio.timeout(TIMEOUT):
        while True:
            frame = decode(await socket.recv())
            if isinstance(frame, kind):
                return frame


async def drain(socket: ClientConnection, seconds: float = 0.15) -> list[Frame]:
    """Kısa bir süre içinde gelen her şeyi toplar. Gelmemesi gerekeni ölçmek için."""
    frames: list[Frame] = []
    try:
        async with asyncio.timeout(seconds):
            while True:
                frames.append(decode(await socket.recv()))
    except (TimeoutError, ConnectionClosed):
        pass
    return frames


# --- el sıkışma -------------------------------------------------------------------------


async def test_handshake_welcomes_matching_version() -> None:
    async with running() as (port, _, _):
        socket, answer = await handshake(port)
        assert answer == Welcome(protocol_version=PROTOCOL_VERSION)
        await socket.close()


async def test_handshake_rejects_version_mismatch() -> None:
    async with running() as (port, _, _):
        socket, answer = await handshake(port, version=PROTOCOL_VERSION + 1)
        assert isinstance(answer, Rejected)
        assert answer.server_version == PROTOCOL_VERSION
        # Ret sonrası bağlantı kapanır; sessizce açık bırakılmaz.
        with pytest.raises(ConnectionClosed):
            async with asyncio.timeout(TIMEOUT):
                await socket.recv()


async def test_handshake_rejects_when_first_frame_is_not_hello() -> None:
    async with running() as (port, _, _):
        socket = await connect(f"ws://127.0.0.1:{port}")
        await socket.send(encode(Ping()))
        answer = await recv(socket)
        assert isinstance(answer, Rejected)
        await socket.close()


async def test_handshake_rejects_empty_device_id() -> None:
    async with running() as (port, _, _):
        socket, answer = await handshake(port, device_id="")
        assert isinstance(answer, Rejected)
        await socket.close()


async def test_handshake_rejects_unreadable_frame() -> None:
    async with running() as (port, _, _):
        socket = await connect(f"ws://127.0.0.1:{port}")
        await socket.send("bu JSON değil")
        answer = await recv(socket)
        assert isinstance(answer, Rejected)
        await socket.close()


# --- tur akışı --------------------------------------------------------------------------


async def test_text_segment_runs_a_turn_and_frames_come_back() -> None:
    async with running() as (port, _, runner), client(port) as socket:
        await socket.send(encode(TextSegment(segment_id="s1", text="saat kaç")))

        transcript = await expect(socket, Transcript)
        assert transcript.segment_id == "s1"
        assert transcript.text == "saat kaç"
        assert transcript.turn_id == runner.turn_ids[0]

        chunk = await expect(socket, AudioChunk)
        assert chunk.turn_id == transcript.turn_id
        assert chunk.seq == 0
        assert chunk.data == b"\x00\x01"
        assert chunk.format == FORMAT

        end = await expect(socket, AudioEnd)
        assert end.turn_id == transcript.turn_id


async def test_speech_segment_reaches_the_turn_as_audio() -> None:
    async with running() as (port, session, runner), client(port) as socket:
        await socket.send(
            encode(SpeechSegment(segment_id="s1", format=FORMAT, data=b"\x02\x03"))
        )
        await expect(socket, AudioEnd)
        assert len(runner.turn_ids) == 1
        assert session.state is State.IDLE


async def test_tool_running_is_announced() -> None:
    async with running(tool="weather") as (port, _, _), client(port) as socket:
        await socket.send(encode(TextSegment(segment_id="s1", text="hava")))
        assert (await expect(socket, ToolRunning)).tool_name == "weather"


async def test_state_changes_are_broadcast_but_audio_is_not() -> None:
    """Durum sistem geneli (§5: tek tur), ses turun cihazına ait."""
    async with (
        running() as (port, _, _),
        client(port, "dev1") as first,
        client(port, "dev2") as second,
    ):
        await first.send(encode(TextSegment(segment_id="s1", text="merhaba")))
        await expect(first, AudioEnd)

        seen = await drain(second)
        assert [frame.state for frame in seen if isinstance(frame, StateChanged)] == [
            State.COZUMLUYOR,
            State.DUSUNUYOR,
            State.KONUSUYOR,
            State.IDLE,
        ]
        assert not [frame for frame in seen if isinstance(frame, AudioChunk | Transcript)]


# --- söz kesme --------------------------------------------------------------------------


async def test_interrupt_cancels_the_turn_and_announces_it() -> None:
    async with running(chunks=1) as (port, _, runner):
        runner.release.clear()
        async with client(port) as socket:
            await socket.send(encode(TextSegment(segment_id="s1", text="uzun cevap")))
            await expect(socket, Transcript)
            await asyncio.wait_for(runner.started.wait(), TIMEOUT)

            turn_id = runner.turn_ids[-1]
            await socket.send(encode(Interrupt(turn_id=turn_id)))
            assert (await expect(socket, Cancelled)).turn_id == turn_id


async def test_barge_in_while_thinking_cancels_the_turn() -> None:
    """`DÜŞÜNÜYOR`'da söz kesme 2026-08-10'da §5 tabloya eklendi (Kural 12)."""
    async with running() as (port, _, runner):
        runner.thinking.clear()
        async with client(port) as socket:
            await socket.send(encode(TextSegment(segment_id="s1", text="uzun cevap")))
            async with asyncio.timeout(TIMEOUT):
                while (await expect(socket, StateChanged)).state is not State.DUSUNUYOR:
                    pass

            turn_id = runner.turn_ids[-1]
            await socket.send(encode(Interrupt(turn_id=turn_id)))
            assert (await expect(socket, Cancelled)).turn_id == turn_id
            runner.thinking.set()


async def test_undefined_transition_is_reported_without_killing_the_link() -> None:
    """`ÇÖZÜMLÜYOR`'da söz kesme §5'te tanımsız. Tablo yükseltiyor; sunucu bunu hataya
    çeviriyor ve bağlantıyı düşürmüyor."""
    async with running() as (port, _, runner):
        runner.resolving.clear()
        async with client(port) as socket:
            await socket.send(encode(TextSegment(segment_id="s1", text="uzun cevap")))
            await expect(socket, Transcript)

            await socket.send(encode(Interrupt(turn_id=runner.turn_ids[-1])))
            error = await expect(socket, ErrorFrame)
            assert error.code == "InvalidTransitionError"

            await socket.send(encode(Ping()))
            assert isinstance(await expect(socket, Pong), Pong)
            runner.resolving.set()


async def test_interrupt_for_an_unknown_turn_is_ignored() -> None:
    async with running() as (port, _, _), client(port) as socket:
        await socket.send(encode(Interrupt(turn_id="yok")))
        await socket.send(encode(Ping()))
        assert isinstance(await expect(socket, Pong), Pong)


# --- protokol kuralları -----------------------------------------------------------------


async def test_ping_is_answered() -> None:
    async with running() as (port, _, _), client(port) as socket:
        await socket.send(encode(Ping()))
        assert isinstance(await expect(socket, Pong), Pong)


async def test_malformed_frame_is_reported_and_connection_survives() -> None:
    async with running() as (port, _, _), client(port) as socket:
        await socket.send("{}")
        error = await expect(socket, ErrorFrame)
        assert error.code == "protocol"
        await socket.send(encode(Ping()))
        assert isinstance(await expect(socket, Pong), Pong)


async def test_server_frame_from_client_is_refused() -> None:
    """Yön doğrulanmasaydı istemci sunucunun sözlüğünü karşısına koyabilirdi."""
    async with running() as (port, _, _), client(port) as socket:
        await socket.send(encode(Welcome(protocol_version=PROTOCOL_VERSION)))
        error = await expect(socket, ErrorFrame)
        assert "welcome" in error.message


async def test_second_hello_is_refused() -> None:
    async with running() as (port, _, _), client(port) as socket:
        await socket.send(encode(Hello(protocol_version=PROTOCOL_VERSION, device_id="dev1")))
        error = await expect(socket, ErrorFrame)
        assert "El sıkışma" in error.message


async def test_reconnect_replaces_the_previous_connection() -> None:
    async with running() as (port, _, _):
        first, _ = await handshake(port, "dev1")
        async with client(port, "dev1") as second:
            await second.send(encode(TextSegment(segment_id="s1", text="merhaba")))
            assert (await expect(second, Transcript)).segment_id == "s1"
        await first.close()


# --- yönlendirme birim testleri ---------------------------------------------------------


async def test_frames_of_a_dead_turn_are_dropped() -> None:
    """§13: iptalden sonra ağda ölü turun parçaları kalır; sunucu onları yönlendirmez."""
    connections = Connections()
    sink = FrameSink(connections)
    runner = ScriptedRunner(sink)
    session = Session(runner, sink)
    sink.attach(session)
    # Aktif tur yok: hiçbir bağlantı olmadığı hâlde çağrı patlamamalı, sessiz de olmamalı.
    await sink.audio_chunk("t99", 0, FORMAT, b"\x00")
    await sink.audio_end("t99")
    assert session.active_turn is None


class FailingRunner(ScriptedRunner):
    """Turu patlatan koşucu: hatanın istemciye ulaşıp ulaşmadığı ölçülüyor."""

    async def run(self, turn: ActiveTurn, report: TurnReport) -> None:
        self.turn_ids.append(turn.turn_id)
        raise RuntimeError("tur patladı")


async def test_a_failing_turn_reaches_the_client() -> None:
    """§14/Kural 13: sessizlik de bir cevap ve yanlış olanı — hata ayrı kanaldan gider."""
    async with running(FailingRunner) as (port, _, _), client(port) as socket:
        await socket.send(encode(TextSegment(segment_id="s1", text="selam")))
        error = await expect(socket, ErrorFrame)
        assert error.code == "turn_failed"
        assert "tur patladı" in error.message
        # Sebep önce, durum sonra: `IDLE` hatadan sonra geliyor.
        assert (await expect(socket, StateChanged)).state is State.IDLE


async def test_sink_without_a_session_raises() -> None:
    """Kural 13: bağlanmamış sink sessizce çerçeve yutmaz."""
    sink = FrameSink(Connections())
    with pytest.raises(RuntimeError):
        await sink.audio_end("t1")
