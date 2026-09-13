"""§6'nın sıralı TTS kuyruğu."""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import pytest

from mayen.adapters.audio import AudioFormat
from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.fakes.tts import FAKE_FORMAT, FakeTTS
from mayen.turn.speech import SpeechQueue


@dataclass
class RecordingSink:
    delay: float = 0
    chunks: list[tuple[str, int, bytes]] = field(default_factory=list)
    ended: list[str] = field(default_factory=list)
    replies: list[tuple[str, str]] = field(default_factory=list)

    async def reply(self, turn_id: str, text: str) -> None:
        self.replies.append((turn_id, text))

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        assert audio_format == FAKE_FORMAT
        if self.delay:
            await asyncio.sleep(self.delay)
        self.chunks.append((turn_id, seq, data))

    async def audio_end(self, turn_id: str) -> None:
        self.ended.append(turn_id)

    @property
    def spoken(self) -> str:
        # Sahte TTS her cümlenin sonuna bir boşluk koyuyor (ayıraç, gerekçesi
        # `adapters/fakes/tts.py`'de); son cümleninki kuyrukta kalıyor.
        return b"".join(data for _, _, data in self.chunks).decode("utf-8").strip()


async def pieces(*texts: str, delay: float = 0) -> AsyncGenerator[str]:
    for text in texts:
        if delay:
            await asyncio.sleep(delay)
        yield text


async def test_pieces_are_sent_in_order() -> None:
    sink = RecordingSink()
    queue = SpeechQueue(FakeTTS(chunk_size=3), sink)
    await queue.speak("t1", pieces("Bir.", "İki.", "Üç."))
    await queue.end("t1")
    assert sink.spoken == "Bir. İki. Üç."
    assert sink.ended == ["t1"]


async def test_seq_increases_across_the_whole_turn() -> None:
    """§13: `seq` ne cümlede ne de `speak` çağrısında sıfırlanır — tur boyunca artar."""
    sink = RecordingSink()
    queue = SpeechQueue(FakeTTS(chunk_size=2), sink)
    await queue.speak("t1", pieces("Bir."))
    await queue.speak("t1", pieces("İki."))
    assert [seq for _, seq, _ in sink.chunks] == list(range(len(sink.chunks)))
    assert {turn_id for turn_id, _, _ in sink.chunks} == {"t1"}


async def test_next_piece_is_not_synthesized_before_the_previous_is_sent() -> None:
    """Paralellik yok: sıra zamanlamaya emanet edilmiyor."""
    tts = FakeTTS(chunk_size=2)
    sink = RecordingSink(delay=0.01)
    task = asyncio.create_task(
        SpeechQueue(tts, sink).speak("t1", pieces("Birinci.", "İkinci."))
    )
    await asyncio.sleep(0.005)
    assert tts.calls == ["Birinci."]
    await task
    assert tts.calls == ["Birinci.", "İkinci."]


async def test_cancellation_writes_no_audio_end() -> None:
    """İptalde turu bitiren çerçeve `Cancelled`, `AudioEnd` değil (Kural 12, §13)."""
    sink = RecordingSink()
    task = asyncio.create_task(
        SpeechQueue(FakeTTS(), sink).speak("t1", pieces("Bir.", "İki.", delay=0.05))
    )
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert sink.ended == []


async def test_tts_failure_is_not_swallowed() -> None:
    """Kural 13: sessiz bir sessizlik yok; hata yukarı çıkar (§14 ayrı kanaldan bildirir)."""
    sink = RecordingSink()
    with pytest.raises(ServiceUnavailableError):
        await SpeechQueue(FakeTTS(available=False), sink).speak("t1", pieces("Bir."))
    assert sink.ended == []


async def test_empty_stream_still_ends_the_turn() -> None:
    sink = RecordingSink()
    queue = SpeechQueue(FakeTTS(), sink)
    await queue.speak("t1", pieces())
    await queue.end("t1")
    assert sink.chunks == []
    assert sink.ended == ["t1"]
