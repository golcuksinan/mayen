"""Mikrofon istemcisi (§13): çalma tamponu ve bozuk mesaj."""

from collections.abc import AsyncIterator
from typing import Any

from mayen.clients.mic import Playback, Traffic, _receive


def test_playback_pads_with_silence_and_keeps_the_rest() -> None:
    playback = Playback()
    playback.add(b"\x01\x02\x03\x04")
    out = bytearray(2)
    playback.fill(out, 1, None, None)
    assert out == b"\x01\x02"
    out = bytearray(4)
    playback.fill(out, 2, None, None)
    assert out == b"\x03\x04\x00\x00"


class Messages:
    def __init__(self, *messages: str | bytes) -> None:
        self._messages = messages

    async def __aiter__(self) -> AsyncIterator[str | bytes]:
        for message in self._messages:
            yield message


async def test_a_message_that_is_not_pcm_is_dropped_not_fatal() -> None:
    playback, traffic = Playback(), Traffic()
    ws: Any = Messages("hello", b"\x00", b"\x05\x06")
    await _receive(ws, playback, traffic)
    out = bytearray(2)
    playback.fill(out, 1, None, None)
    assert out == b"\x05\x06" and traffic.received == 2
