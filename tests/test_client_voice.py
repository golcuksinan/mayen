"""Endpointing ve ses çıkışı (§7, §18). Ses kartı yok: mikrofon da hoparlör de sahte.

Ölçülen şey donanım değil, karar: konuşma nerede başlıyor, segment nerede kapanıyor, ilk
hece korunuyor mu, iptal sesi gerçekten kesiyor mu ve yarım dubleks kendi sesini duymuyor
mu. Hepsi saf mantık; gerçek PortAudio yolu (`client/portaudio.py`) elle koşuluyor.
"""

import math

from client.audio import FRAME_BYTES, FakeMicrophone, FakePlayer, rms
from client.core import Client
from client.endpointing import Endpointer, Settings
from client.output import Output
from client.portaudio import Speaker
from client.voice import VoiceOutput, listen

from mayen.adapters.audio import AudioFormat
from mayen.transport.frames import Cancelled, Transcript

SETTINGS = Settings(threshold=500.0, start_frames=2, end_frames=3, pre_roll_frames=2)


def tone(amplitude: int) -> bytes:
    """Sabit genlikte bir kare dalga çerçevesi: RMS'i genliğin kendisi."""
    return (amplitude.to_bytes(2, "little", signed=True)) * (FRAME_BYTES // 2)


LOUD = tone(3000)
QUIET = tone(10)


class Sender:
    """Segmenti ve söz kesmeyi kaydeden sahte istemci."""

    def __init__(self, *, has_turn: bool = True) -> None:
        self.segments: list[bytes] = []
        self.interrupts = 0
        self._has_turn = has_turn

    async def send_speech(self, audio_format: AudioFormat, data: bytes) -> str:
        self.segments.append(data)
        return f"s{len(self.segments)}"

    async def interrupt(self) -> bool:
        self.interrupts += 1
        return self._has_turn


def _listener(sender: Sender) -> Client:
    return sender  # type: ignore[return-value]


# --- enerji ------------------------------------------------------------------------------


def test_rms_matches_a_known_amplitude() -> None:
    assert math.isclose(rms(LOUD), 3000.0)
    assert rms(b"") == 0.0


def test_odd_length_frame_is_an_error() -> None:
    """Yarım örneği sessizce kırpmak sıralamayı bozar ve hatayı çok uzakta gösterir."""
    try:
        rms(b"\x00")
    except ValueError:
        return
    raise AssertionError("tek sayıda bayt kabul edildi")


# --- endpointing -------------------------------------------------------------------------


def test_speech_is_closed_by_silence() -> None:
    endpointer = Endpointer(SETTINGS)
    frames = [QUIET, LOUD, LOUD, LOUD, QUIET, QUIET, QUIET]
    segments = [segment for frame in frames if (segment := endpointer.feed(frame))]
    assert len(segments) == 1
    # Ön tampon dâhil: kararın öncesindeki sessiz çerçeve de segmentin başında.
    assert len(segments[0]) == 7 * FRAME_BYTES
    assert not endpointer.speaking


def test_a_single_loud_frame_is_not_speech() -> None:
    """Kapı çarpması konuşma değil: eşiği bir kere aşmak yetmiyor."""
    endpointer = Endpointer(SETTINGS)
    assert endpointer.feed(LOUD) is None
    assert endpointer.feed(QUIET) is None
    assert not endpointer.speaking


def test_pre_roll_keeps_the_first_syllable() -> None:
    """İlk hece atılsaydı transkript 'elam' diye başlardı."""
    endpointer = Endpointer(Settings(start_frames=2, end_frames=2, pre_roll_frames=1))
    for frame in (QUIET, QUIET, LOUD, LOUD):
        endpointer.feed(frame)
    segment = endpointer.flush()
    assert segment is not None
    assert len(segment) == 3 * FRAME_BYTES  # 1 ön tampon + 2 konuşma


def test_a_segment_cannot_grow_forever() -> None:
    """Sessizliğin gelmediği ortamda tavan segmenti kapatıyor."""
    endpointer = Endpointer(Settings(start_frames=1, end_frames=99, max_seconds=0.1))
    segments = [segment for _ in range(20) if (segment := endpointer.feed(LOUD))]
    assert segments
    assert len(segments[0]) == 5 * FRAME_BYTES  # 100 ms / 20 ms


def test_flush_does_not_swallow_a_half_segment() -> None:
    endpointer = Endpointer(SETTINGS)
    endpointer.feed(LOUD)
    endpointer.feed(LOUD)
    assert endpointer.speaking
    assert endpointer.flush() is not None
    assert endpointer.flush() is None


def test_wrong_frame_size_is_an_error() -> None:
    """Değişken boy, eşiği çerçeveden çerçeveye başka bir şeye çevirirdi."""
    endpointer = Endpointer(SETTINGS)
    try:
        endpointer.feed(LOUD + b"\x00\x00")
    except ValueError:
        return
    raise AssertionError("yanlış boyda çerçeve kabul edildi")


# --- dinleme döngüsü ---------------------------------------------------------------------


async def test_listen_sends_a_completed_segment() -> None:
    sender = Sender()
    output = VoiceOutput(FakePlayer(), Recorder())
    microphone = FakeMicrophone([QUIET, LOUD, LOUD, LOUD, QUIET, QUIET, QUIET])
    await listen(_listener(sender), microphone, output, settings=SETTINGS)
    assert len(sender.segments) == 1


async def test_half_duplex_ignores_the_microphone_while_speaking() -> None:
    """AEC yok: asistan konuşurken mikrofonun duyduğu şey asistanın kendisi."""
    sender = Sender()
    output = VoiceOutput(FakePlayer(), Recorder())
    await output.chunk("t1", 0, b"\x00\x00")  # konuşmaya başladı
    microphone = FakeMicrophone([LOUD] * 10 + [QUIET] * 5)
    await listen(_listener(sender), microphone, output, settings=SETTINGS)
    assert sender.segments == []
    assert sender.interrupts == 0


async def test_barge_in_interrupts_at_the_start_of_speech() -> None:
    """Segmentin sonunu beklemek, kullanıcı sustuktan sonra kesmek olurdu."""
    sender = Sender()
    output = VoiceOutput(FakePlayer(), Recorder())
    await output.chunk("t1", 0, b"\x00\x00")
    microphone = FakeMicrophone([LOUD, LOUD, LOUD, QUIET, QUIET, QUIET])
    await listen(_listener(sender), microphone, output, settings=SETTINGS, barge_in=True)
    assert sender.interrupts == 1
    assert len(sender.segments) == 1  # kesme segmenti iptal etmiyor, o da gidiyor


# --- ses çıkışı --------------------------------------------------------------------------


class Recorder:
    """Bilgilendirme satırlarını yutan sessiz `Output`."""

    async def state(self, state: object, turn_id: str | None) -> None: ...

    async def transcript(self, turn_id: str, text: str) -> None: ...

    async def tool_running(self, turn_id: str, tool_name: str) -> None: ...

    async def announcement(self, turn_id: str, text: str) -> None: ...

    async def reply(self, turn_id: str, text: str) -> None: ...

    async def chunk(self, turn_id: str, seq: int, data: bytes) -> None: ...

    async def end(self, turn_id: str) -> None: ...

    async def cancelled(self, turn_id: str) -> None: ...

    async def failed(self, code: str, message: str) -> None: ...


_contract: Output = VoiceOutput(FakePlayer())


async def test_chunks_reach_the_player_and_end_stops_speaking() -> None:
    player = FakePlayer()
    output = VoiceOutput(player, Recorder())
    await output.chunk("t1", 0, b"\x01\x02")
    assert output.speaking
    await output.end("t1")
    assert player.played == [b"\x01\x02"]
    assert not output.speaking


async def test_cancel_drops_the_buffer() -> None:
    """§13: iptali duyulur yapan şey tampondakini çalmamak."""
    player = FakePlayer()
    output = VoiceOutput(player, Recorder())
    await output.chunk("t1", 0, b"\x01\x02")
    await output.cancelled("t1")
    assert player.stops == 1
    assert player.played == []
    assert not output.speaking


async def test_the_client_drives_the_voice_output() -> None:
    """Protokol tarafı değişmedi: aynı `Client`, farklı `Output`."""
    player = FakePlayer()
    output = VoiceOutput(player, Recorder())
    client = Client(None, "dev1", output)  # type: ignore[arg-type]
    await client._handle(Transcript(segment_id="s1", turn_id="t1", text="merhaba"))
    await client._handle(Cancelled(turn_id="t1"))
    assert player.stops == 1


# --- PortAudio hoparlörü ----------------------------------------------------------------


class FakeStream:
    """`sounddevice.RawOutputStream`'in yerine: yazılanı biriktirir, tek baytı reddeder."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.aborts = 0

    def write(self, data: bytes) -> None:
        # PortAudio'nun kendi davranışı; hatanın metni de oradan.
        if len(data) % 2:
            raise ValueError("len(data) not divisible by samplesize")
        self.written.append(data)

    def abort(self) -> None:
        self.aborts += 1

    def start(self) -> None:
        pass


def _speaker() -> tuple[Speaker, FakeStream]:
    """Ses kartsız hoparlör: akış elle takılıyor, `_open()` hazır bulduğunu döndürüyor."""
    speaker = Speaker()
    stream = FakeStream()
    speaker._stream = stream
    return speaker, stream


async def test_an_odd_chunk_carries_its_last_byte_to_the_next_one() -> None:
    """Çerçeve sınırı örnek sınırı değil: servis ffmpeg'i sabit boyutta okuyor ve tek
    uzunlukta parça gelebiliyor. Yakalandığı yer gerçek bir turdu: PortAudio hata veriyor,
    ses cümlenin ortasında kesiliyordu."""
    speaker, stream = _speaker()
    await speaker.play(b"\x01\x02\x03")
    await speaker.play(b"\x04\x05")
    assert b"".join(stream.written) == b"\x01\x02\x03\x04"


async def test_no_sample_is_dropped_across_chunks() -> None:
    """Artığı atmak da olmazdı: akış bir bayt kayar ve kalan ses gürültüye dönerdi."""
    speaker, stream = _speaker()
    audio = bytes(range(64))
    for start in range(0, len(audio), 7):
        await speaker.play(audio[start : start + 7])
    written = b"".join(stream.written)
    assert written == audio[: len(written)]
    assert len(audio) - len(written) < 2


async def test_stop_drops_the_half_sample_too() -> None:
    """Yarım örnek sonraki cevabın ilk baytıyla birleşseydi onu kaydırırdı."""
    speaker, stream = _speaker()
    await speaker.play(b"\x01")
    await speaker.stop()
    await speaker.play(b"\x02\x03")
    assert stream.aborts == 1
    assert b"".join(stream.written) == b"\x02\x03"
