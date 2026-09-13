"""Başsız istemci (§13). Gerçek soketin iki ucu da gerçek.

Sunucu tarafı `mayen.main.build`'in kurduğu sistemin kendisi — istemciyi elle kurulmuş
bir sunucuya konuşturmak, montajın da protokolün de yalnızca yarısını ölçerdi. Sahte olan
tek şey LLM (§19.2 açık, §4 GPU'suz koşmayı şart koşuyor); STT ve TTS zaten sahte ve metin
istemcisi tam olarak o yolu kullanıyor (P1).

Tur takibinin asıl kuralı — ölü turun parçası çalınmaz — sunucuya ihtiyaç duymadan da
ölçülüyor: `Client._handle` çerçeveyi doğrudan alıyor.
"""

import asyncio
import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from client.core import Client, HandshakeError, connect
from client.output import Output, TextOutput

from mayen.adapters.audio import AudioFormat, Codec
from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.fakes.tts import FakeTTS
from mayen.config import Config
from mayen.main import App, build
from mayen.session.state import State
from mayen.transport.frames import (
    Announcement,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ErrorFrame,
    StateChanged,
    ToolRunning,
    Transcript,
    Welcome,
)

ANSWER = "It is sunny today. Nothing else to report."
FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)
TIMEOUT = 5.0


class Recorder:
    """Duyulan her şeyi sırasıyla toplar."""

    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []
        self.text: list[str] = []
        self.ended = asyncio.Event()
        self.cancels = asyncio.Event()

    async def state(self, state: State, turn_id: str | None) -> None:
        self.events.append(("state", state))

    async def transcript(self, turn_id: str, text: str) -> None:
        self.events.append(("transcript", text))

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        self.events.append(("tool", tool_name))

    async def announcement(self, turn_id: str, text: str) -> None:
        self.events.append(("announcement", text))

    async def reply(self, turn_id: str, text: str) -> None:
        self.events.append(("reply", text))

    async def chunk(self, turn_id: str, seq: int, data: bytes) -> None:
        self.events.append(("chunk", seq))
        self.text.append(data.decode("utf-8"))

    async def end(self, turn_id: str) -> None:
        self.events.append(("end", turn_id))
        self.ended.set()

    async def cancelled(self, turn_id: str) -> None:
        self.events.append(("cancelled", turn_id))
        self.cancels.set()

    async def failed(self, code: str, message: str) -> None:
        self.events.append(("failed", code))


_contract: Output = Recorder()
"""Sözleşme kontrolü: `Recorder` gerçekten `Output` mu (mypy'nin işi, testin değil)."""


def _config(tmp_path: Path) -> Config:
    role = Path(__file__).parent.parent / "config" / "rol.txt"
    return Config(db_path=tmp_path / "mayen.db", role_path=role, host="127.0.0.1", port=0)


@asynccontextmanager
async def server(tmp_path: Path) -> AsyncIterator[tuple[str, App]]:
    async with build(_config(tmp_path), llm=FakeLLM([ANSWER]), tts=FakeTTS()) as app:
        socket = await app.server.serve("127.0.0.1", 0)
        try:
            port = socket.sockets[0].getsockname()[1]
            yield f"ws://127.0.0.1:{port}", app
        finally:
            socket.close()
            await socket.wait_closed()


def _client(output: Output) -> Client:
    """Soketsiz istemci: yalnızca çerçeve işleme yolunu ölçen testler için."""
    return Client(None, "dev1", output)  # type: ignore[arg-type]


# --- uçtan uca --------------------------------------------------------------------------


async def test_text_turn_reaches_the_client(tmp_path: Path) -> None:
    recorder = Recorder()
    async with server(tmp_path) as (url, _), connect(url, "dev1", recorder) as client:
        await client.say("Hava nasıl?")
        async with asyncio.timeout(TIMEOUT):
            await recorder.ended.wait()
    assert ("transcript", "Hava nasıl?") in recorder.events
    assert "".join(recorder.text).strip() == ANSWER
    assert client.active_turn is None
    assert client.dropped == 0


async def test_states_are_seen(tmp_path: Path) -> None:
    recorder = Recorder()
    async with server(tmp_path) as (url, _), connect(url, "dev1", recorder) as client:
        await client.say("selam")
        async with asyncio.timeout(TIMEOUT):
            await recorder.ended.wait()
    seen = [value for name, value in recorder.events if name == "state"]
    assert State.COZUMLUYOR in seen
    assert seen[-1] is State.IDLE


async def test_handshake_failure_raises(tmp_path: Path) -> None:
    recorder = Recorder()
    async with server(tmp_path) as (url, _):
        with pytest.raises(HandshakeError):
            async with connect(url, "", recorder):
                pass  # pragma: no cover - el sıkışma zaten patladı


# --- tur takibi -------------------------------------------------------------------------


async def test_chunk_of_an_unknown_turn_is_dropped() -> None:
    """§13'ün asıl kuralı: iptal sonrası yolda kalan parça yeni cevabın üstüne çalmaz."""
    recorder = Recorder()
    client = _client(recorder)
    await client._handle(Transcript(segment_id="s1", turn_id="t2", text="merhaba"))
    await client._handle(AudioChunk(turn_id="t1", seq=0, format=FORMAT, data=b"eski"))
    assert recorder.text == []
    assert client.dropped == 1


async def test_end_of_an_unknown_turn_does_not_close_the_active_one() -> None:
    recorder = Recorder()
    client = _client(recorder)
    await client._handle(Transcript(segment_id="s1", turn_id="t2", text="merhaba"))
    await client._handle(AudioEnd(turn_id="t1"))
    assert client.active_turn == "t2"
    assert not recorder.ended.is_set()


async def test_cancel_closes_the_turn() -> None:
    recorder = Recorder()
    client = _client(recorder)
    await client._handle(Transcript(segment_id="s1", turn_id="t1", text="merhaba"))
    await client._handle(Cancelled(turn_id="t1"))
    assert client.active_turn is None
    assert recorder.cancels.is_set()


async def test_sequence_gap_is_reported_not_swallowed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Eksik parça kaybolmuş ses; atmak kaybı ikiye katlardı, susmak Kural 13'e aykırı."""
    recorder = Recorder()
    client = _client(recorder)
    await client._handle(Transcript(segment_id="s1", turn_id="t1", text="merhaba"))
    await client._handle(AudioChunk(turn_id="t1", seq=0, format=FORMAT, data=b"a"))
    await client._handle(AudioChunk(turn_id="t1", seq=2, format=FORMAT, data=b"c"))
    assert recorder.text == ["a", "c"]
    assert "sıra atlandı" in capsys.readouterr().out


async def test_tool_notice_and_error_reach_the_output() -> None:
    recorder = Recorder()
    client = _client(recorder)
    await client._handle(Transcript(segment_id="s1", turn_id="t1", text="merhaba"))
    await client._handle(ToolRunning(turn_id="t1", tool_name="weather"))
    await client._handle(ErrorFrame(code="protocol", message="bozuk"))
    assert ("tool", "weather") in recorder.events
    assert ("failed", "protocol") in recorder.events


async def test_state_frame_updates_the_client() -> None:
    client = _client(Recorder())
    await client._handle(StateChanged(state=State.DUSUNUYOR, turn_id="t1"))
    assert client.state is State.DUSUNUYOR


async def test_unexpected_welcome_is_ignored_not_fatal() -> None:
    client = _client(Recorder())
    await client._handle(Welcome(protocol_version=1))
    assert client.active_turn is None


async def test_announcement_opens_the_turn_so_its_audio_is_played() -> None:
    """§12'nin proaktif sesi: turu kullanıcı açmadı, ama §13'ün filtresi onu düşürmemeli."""
    recorder = Recorder()
    client = _client(recorder)

    await client._handle(Announcement(turn_id="t9", text="Time for your medicine."))
    await client._handle(AudioChunk(turn_id="t9", seq=0, format=FORMAT, data=b"Time"))
    await client._handle(AudioEnd(turn_id="t9"))

    assert ("announcement", "Time for your medicine.") in recorder.events
    assert "".join(recorder.text).strip() == "Time"
    assert client.dropped == 0
    assert client.active_turn is None


async def test_interrupt_without_a_turn_sends_nothing() -> None:
    client = _client(Recorder())
    assert await client.interrupt() is False


# --- metin çıktısı ----------------------------------------------------------------------


async def test_a_failing_output_is_reported_and_the_client_keeps_reading(
    tmp_path: Path,
) -> None:
    """Çıkışın arızası okuma döngüsünü öldürmüyor (Kural 13).

    Yutulduğu sürümde hoparlör tek bir parçada patlıyor, okuma görevi ölüyor ve istemci o
    andan sonra sessizce sağır kalıyordu: kullanıcı yazıyor, hiçbir cevap gelmiyor.
    """

    class Broken(Recorder):
        async def chunk(self, turn_id: str, seq: int, data: bytes) -> None:
            raise RuntimeError("hoparlör")

    recorder = Broken()
    async with server(tmp_path) as (url, _), connect(url, "dev1", recorder) as client:
        await client.say("Hava nasıl?")
        async with asyncio.timeout(TIMEOUT):
            await recorder.ended.wait()
    assert ("failed", "client") in recorder.events
    # Tur yine de kapandı: hata bir çerçevede kaldı, döngü sonrakileri işlemeye devam etti.
    assert client.active_turn is None


async def test_text_output_writes_the_answer_as_it_arrives() -> None:
    """Cevap `Reply`'dan geliyor: cümle cümle, sesinden önce."""
    stream = io.StringIO()
    output = TextOutput(stream)
    await output.transcript("t1", "Hava nasıl?")
    await output.reply("t1", "Sunny today.")
    await output.reply("t1", "Nothing else.")
    await output.end("t1")
    assert "[anlaşılan] Hava nasıl?" in stream.getvalue()
    assert "[cevap] Sunny today." in stream.getvalue()
    assert "[cevap] Nothing else." in stream.getvalue()


async def test_text_output_reports_the_audio_it_cannot_play_by_size() -> None:
    """Metin uçbiriminin hoparlörü yok. Gelen sesi sessizce atmak, hiç gelmemesinden
    ayırt edilemezdi (Kural 13)."""
    stream = io.StringIO()
    output = TextOutput(stream)
    await output.chunk("t1", 0, b"\xff\xfe\x00")
    await output.end("t1")
    assert "[ses] 3 bayt" in stream.getvalue()


async def test_text_output_does_not_try_to_read_audio_as_text() -> None:
    """Eski yol (yükü UTF-8 çözmek) sahte TTS'e dayanıyordu; gerçek PCM ekrana çöp basardı."""
    stream = io.StringIO()
    output = TextOutput(stream)
    await output.chunk("t1", 0, "Şimdi".encode())
    await output.end("t1")
    assert "Şimdi" not in stream.getvalue()
    assert "[ses] 6 bayt" in stream.getvalue()
