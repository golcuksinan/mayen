"""§6'nın cümle bölücüsü."""

import asyncio
from collections.abc import AsyncGenerator

import pytest

from mayen.turn.sentences import SentenceSplitter, split


async def stream(*chunks: str, delay: float = 0) -> AsyncGenerator[str]:
    for chunk in chunks:
        if delay:
            await asyncio.sleep(delay)
        yield chunk


def test_splits_on_sentence_end() -> None:
    splitter = SentenceSplitter(min_chars=3)
    assert splitter.feed("Merhaba. ") == ["Merhaba."]
    assert splitter.feed("Nasılsın? Ben iyiyim.") == ["Nasılsın?"]
    assert splitter.flush() == "Ben iyiyim."


def test_punctuation_needs_a_following_character() -> None:
    """Akışın sonundaki nokta bölmez: arkasından ne geleceği henüz bilinmiyor."""
    splitter = SentenceSplitter(min_chars=1)
    assert splitter.feed("Merhaba.") == []
    assert splitter.flush() == "Merhaba."


def test_decimal_point_is_not_a_sentence_end() -> None:
    splitter = SentenceSplitter(min_chars=1)
    assert splitter.feed("Sıcaklık 18.5 derece ve ") == []


def test_short_piece_waits_for_the_minimum_length() -> None:
    splitter = SentenceSplitter(min_chars=10)
    assert splitter.feed("Evet. Hava bugün güzel. ") == ["Evet. Hava bugün güzel."]


def test_repeated_punctuation_is_one_cut() -> None:
    splitter = SentenceSplitter(min_chars=1)
    assert splitter.feed("Gerçekten mi?! Evet. ") == ["Gerçekten mi?!", "Evet."]


def test_flush_empties_the_buffer() -> None:
    splitter = SentenceSplitter(min_chars=1)
    splitter.feed("yarım")
    assert splitter.pending is True
    assert splitter.flush() == "yarım"
    assert splitter.pending is False
    assert splitter.flush() is None


def test_min_chars_below_one_is_rejected() -> None:
    with pytest.raises(ValueError):
        SentenceSplitter(min_chars=0)


async def test_split_yields_first_sentence_before_the_stream_ends() -> None:
    """§6'nın amacı: ilk parça mümkün olan en erken anda."""
    pieces = split(
        stream("Merhaba. ", "Nasılsın? ", "Ben iyiyim."),
        min_chars=3,
        max_wait_seconds=10,
    )
    assert await anext(pieces) == "Merhaba."
    await pieces.aclose()


async def test_split_emits_everything_in_order() -> None:
    pieces = [
        piece
        async for piece in split(
            stream("Merhaba. Nasılsın? ", "Ben iyiyim."), min_chars=3, max_wait_seconds=10
        )
    ]
    assert pieces == ["Merhaba.", "Nasılsın?", "Ben iyiyim."]


async def test_max_wait_flushes_a_half_sentence() -> None:
    """Noktalama gelmiyorsa ses eşik kadar bekler, sonsuza kadar değil."""
    pieces = [
        piece
        async for piece in split(
            stream("noktalaması olmayan ", "uzun bir metin", delay=0.05),
            min_chars=3,
            max_wait_seconds=0.01,
        )
    ]
    assert pieces == ["noktalaması olmayan", "uzun bir metin"]


async def test_no_wait_while_the_buffer_is_empty() -> None:
    """Elde bir şey yokken eşik işlemez: boş parça üretilmez."""
    pieces = [
        piece
        async for piece in split(
            stream("Merhaba. ", delay=0.05), min_chars=3, max_wait_seconds=0.01
        )
    ]
    assert pieces == ["Merhaba."]
