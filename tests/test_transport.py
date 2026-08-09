"""Protokol: çerçeveler, el sıkışma, backpressure (§13)."""

import asyncio

import pytest

from mayen.adapters.audio import AudioFormat, Codec
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
from mayen.transport.handshake import negotiate
from mayen.transport.queue import SendQueue
from mayen.transport.wire import ProtocolError, decode, encode

FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)

TEXT_FRAMES: list[Frame] = [
    Hello(protocol_version=PROTOCOL_VERSION, device_id="salon"),
    TextSegment(segment_id="s1", text="yarın hava nasıl"),
    Interrupt(turn_id="t1"),
    Ping(),
    Welcome(protocol_version=PROTOCOL_VERSION),
    Rejected(reason="sürüm", server_version=PROTOCOL_VERSION),
    Transcript(segment_id="s1", turn_id="t1", text="yarın hava nasıl"),
    StateChanged(state="COZUMLUYOR", turn_id="t1"),
    ToolRunning(turn_id="t1", tool_name="weather"),
    AudioEnd(turn_id="t1"),
    Cancelled(turn_id="t1"),
    ErrorFrame(code="tts_yok", message="TTS yanıt vermiyor"),
    Pong(),
]


@pytest.mark.parametrize("frame", TEXT_FRAMES, ids=lambda frame: frame.TYPE)
def test_text_frame_round_trip(frame: Frame) -> None:
    encoded = encode(frame)
    assert isinstance(encoded, str)
    assert decode(encoded) == frame


@pytest.mark.parametrize(
    "frame",
    [
        SpeechSegment(segment_id="s1", format=FORMAT, data=b"\x00\x01\xff"),
        AudioChunk(turn_id="t1", seq=3, format=FORMAT, data=b"\x00\x01\xff"),
    ],
    ids=lambda frame: frame.TYPE,
)
def test_binary_frame_round_trip(frame: Frame) -> None:
    encoded = encode(frame)
    assert isinstance(encoded, bytes)
    assert decode(encoded) == frame


def test_audio_payload_is_carried_raw_not_base64() -> None:
    """Kararın kendisi: ses %33 şişmiyor, yük tele olduğu gibi giriyor."""
    payload = bytes(range(256)) * 8
    encoded = encode(AudioChunk(turn_id="t1", seq=1, format=FORMAT, data=payload))
    assert isinstance(encoded, bytes)
    assert payload in encoded
    assert len(encoded) - len(payload) < 200


def test_turn_id_and_seq_survive_the_wire() -> None:
    """§13: `turn_id` tel formatının parçası, sonradan eklenemez."""
    decoded = decode(encode(AudioChunk(turn_id="t9", seq=42, format=FORMAT, data=b"ses")))
    assert isinstance(decoded, AudioChunk)
    assert (decoded.turn_id, decoded.seq) == ("t9", 42)


def test_unknown_frame_type_is_rejected_not_ignored() -> None:
    """Kural 13: sessizce yok saymak, sürüm farkını tur ortasında gizli davranışa çevirir."""
    with pytest.raises(ProtocolError, match="Tanınmayan"):
        decode('{"type": "gelecekteki_cerceve", "x": 1}')


def test_missing_field_is_rejected() -> None:
    with pytest.raises(ProtocolError, match="eksik"):
        decode('{"type": "interrupt"}')


def test_extra_field_is_rejected() -> None:
    with pytest.raises(ProtocolError, match="fazla"):
        decode('{"type": "ping", "sürpriz": 1}')


def test_audio_frame_sent_as_text_is_rejected() -> None:
    with pytest.raises(ProtocolError, match="ikili çerçeve olarak"):
        decode('{"type": "audio_chunk", "turn_id": "t1", "seq": 1, "format": {}}')


def test_truncated_binary_frame_is_rejected() -> None:
    encoded = encode(AudioChunk(turn_id="t1", seq=1, format=FORMAT, data=b"ses"))
    assert isinstance(encoded, bytes)
    with pytest.raises(ProtocolError):
        decode(encoded[:6])


def test_absurd_header_length_is_rejected() -> None:
    with pytest.raises(ProtocolError, match="makul değil"):
        decode((2**31).to_bytes(4, "big") + b"{}")


def test_unknown_codec_is_rejected() -> None:
    """§19.5 açık olan **hangi** kodek; kodek alanına ne yazılırsa yazılsın kabul edilmesi
    değil."""
    header = '{"type": "speech_segment", "segment_id": "s1", "format": {"codec": "mp3", '
    header += '"sample_rate": 16000, "channels": 1}}'
    payload = header.encode("utf-8")
    with pytest.raises(ProtocolError, match="format"):
        decode(len(payload).to_bytes(4, "big") + payload + b"ses")


# --- el sıkışma ------------------------------------------------------------------------


def test_matching_version_is_welcomed() -> None:
    reply = negotiate(Hello(protocol_version=PROTOCOL_VERSION, device_id="salon"))
    assert reply == Welcome(protocol_version=PROTOCOL_VERSION)


def test_version_mismatch_is_rejected_with_a_reason() -> None:
    reply = negotiate(Hello(protocol_version=PROTOCOL_VERSION + 1, device_id="salon"))
    assert isinstance(reply, Rejected)
    assert str(PROTOCOL_VERSION) in reply.reason
    assert reply.server_version == PROTOCOL_VERSION


def test_first_frame_must_be_the_handshake() -> None:
    reply = negotiate(TextSegment(segment_id="s1", text="selam"))
    assert isinstance(reply, Rejected)
    assert "el sıkışma" in reply.reason


# --- backpressure ----------------------------------------------------------------------


async def test_queue_blocks_instead_of_dropping_when_full() -> None:
    """§6: sıra bozulması kabul edilemez, dolayısıyla taşmada çerçeve atılmaz."""
    queue = SendQueue(maxsize=1)
    await queue.put(AudioChunk(turn_id="t1", seq=1, format=FORMAT, data=b"a"))

    pending = asyncio.ensure_future(
        queue.put(AudioChunk(turn_id="t1", seq=2, format=FORMAT, data=b"b"))
    )
    await asyncio.sleep(0)
    assert not pending.done()

    first = await queue.get()
    await pending
    second = await queue.get()

    assert isinstance(first, AudioChunk)
    assert isinstance(second, AudioChunk)
    assert (first.seq, second.seq) == (1, 2)


async def test_cancelling_a_turn_leaves_other_turns_alone() -> None:
    """B1/B2: söz kesme, kuyrukta bekleyen proaktif hatırlatıcıyı düşürmez."""
    queue = SendQueue()
    await queue.put(AudioChunk(turn_id="t1", seq=1, format=FORMAT, data=b"a"))
    await queue.put(AudioChunk(turn_id="t1", seq=2, format=FORMAT, data=b"b"))
    reminder = AudioChunk(turn_id="proaktif", seq=1, format=FORMAT, data="hatırlatma".encode())
    await queue.put(reminder)
    await queue.put(Pong())

    dropped = await queue.cancel_turn("t1")

    assert dropped == 2
    assert len(queue) == 2
    assert await queue.get() == reminder
    assert await queue.get() == Pong()


async def test_waiting_writer_resumes_after_a_cancellation_frees_space() -> None:
    queue = SendQueue(maxsize=1)
    await queue.put(AudioChunk(turn_id="t1", seq=1, format=FORMAT, data=b"a"))
    pending = asyncio.ensure_future(queue.put(Pong()))
    await asyncio.sleep(0)
    assert not pending.done()

    await queue.cancel_turn("t1")
    await asyncio.wait_for(pending, timeout=1)

    assert await queue.get() == Pong()


def test_queue_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="maxsize"):
        SendQueue(maxsize=0)
