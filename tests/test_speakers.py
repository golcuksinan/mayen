"""Konuşmacı tanıma (§6, §10.5): izden kişiye karar, ses izi deposu, söze etiket (§8.1)."""

import struct
import wave
from collections.abc import Iterator
from pathlib import Path

import pytest
from pipecat.frames.frames import TranscriptionFrame
from pipecat.tests.utils import run_test

from mayen.adapters.storage.sqlite import Database, SqlitePersonStore, SqliteVoiceprintStore
from mayen.app import voice
from mayen.app.voice import VoiceError, read_pcm
from mayen.core.speakers import (
    UNKNOWN_LABEL,
    Identified,
    SpeakerMatcher,
    VoiceprintModelError,
    best,
    cosine,
    label,
    mean,
)
from mayen.pipeline.speaker import (
    SPEAKER,
    SpeakerLabel,
    recognized,
    recognized_turn,
    score,
    turn_voice,
)
from mayen.pipeline.speech import VOICE, VOICE_S
from mayen.ports.people import Voiceprint
from mayen.ports.speech import (
    SCHEMA_VERSION,
    Embedding,
    SpeechContractError,
    parse_embedding,
)
from mayen.ports.tools import Role

SINAN = Voiceprint("1", "ecapa", (1.0, 0.0))
AHMET = Voiceprint("2", "ecapa", (0.0, 1.0))


def test_cosine_is_scale_free_and_rejects_other_lengths() -> None:
    assert cosine((1.0, 0.0), (3.0, 0.0)) == pytest.approx(1.0)
    assert cosine((1.0, 0.0), (0.0, 2.0)) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        cosine((1.0,), (1.0, 0.0))


def test_the_best_score_wins_only_above_the_threshold() -> None:
    near_sinan = Embedding("ecapa", (0.9, 0.3))
    found = best(near_sinan, [SINAN, AHMET], threshold=0.5)
    assert found.person_id == "1" and found.score == pytest.approx(0.9 / (0.9**2 + 0.09) ** 0.5)
    # Puan aynı kalır, eşik yükselince kimse tanınmaz: karar eşiğindir, puanın değil.
    strict = best(near_sinan, [SINAN, AHMET], threshold=0.99)
    assert strict == Identified(None, found.score)


def test_no_voiceprint_means_nobody_and_no_score() -> None:
    assert best(Embedding("ecapa", (1.0, 0.0)), [], 0.5) == Identified(None, None)


def test_a_voiceprint_of_another_model_fails_loudly() -> None:
    with pytest.raises(VoiceprintModelError):
        best(Embedding("other", (1.0, 0.0)), [SINAN], 0.5)


def test_threshold_must_be_a_cosine_between_zero_and_one(db: Database) -> None:
    for wrong in (0.0, 1.0, 1.5):
        with pytest.raises(ValueError):
            SpeakerMatcher(SqliteVoiceprintStore(db), wrong)


def test_mean_weighs_every_sample_alike_and_is_a_unit_vector() -> None:
    # Uzun (büyük) bir örnek kısasını bastırmaz.
    joined = mean([(10.0, 0.0), (0.0, 1.0)])
    assert joined == pytest.approx((2**-0.5, 2**-0.5))
    with pytest.raises(ValueError):
        mean([])


def test_label_is_the_name_or_unknown() -> None:
    assert label(None) == UNKNOWN_LABEL == "unknown"


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    with Database(tmp_path / "m.db") as db:
        yield db


def test_voiceprint_is_stored_replaced_and_needs_a_person(db: Database) -> None:
    people, prints = SqlitePersonStore(db), SqliteVoiceprintStore(db)
    owner = people.create_owner("Sinan", "English", None, ())
    prints.set(owner.id, "ecapa", (0.25, -0.5))
    prints.set(owner.id, "ecapa", (0.5, 0.75))
    assert prints.all() == [Voiceprint(owner.id, "ecapa", (0.5, 0.75))]
    for nobody in ("99", "x"):
        with pytest.raises(KeyError):
            prints.set(nobody, "ecapa", (1.0,))


def test_embedding_contract() -> None:
    body = {"schema_version": SCHEMA_VERSION, "model": "ecapa", "vector": [0.5, 1]}
    assert parse_embedding(body) == Embedding("ecapa", (0.5, 1.0))
    for broken in ({**body, "vector": []}, {**body, "schema_version": 9}, {"x": 1}):
        with pytest.raises(SpeechContractError):
            parse_embedding(broken)


def _frame(embedding: Embedding | None) -> TranscriptionFrame:
    frame = TranscriptionFrame("evet", "u", "")
    frame.metadata[VOICE] = embedding
    return frame


def test_recognized_caller_comes_from_the_voice_and_is_decided_once(db: Database) -> None:
    people, prints = SqlitePersonStore(db), SqliteVoiceprintStore(db)
    owner = people.create_owner("Sinan", "English", None, ())
    prints.set(owner.id, "ecapa", (1.0, 0.0))
    source = recognized(SpeakerMatcher(prints, 0.5), people)
    frame = _frame(Embedding("ecapa", (1.0, 0.1)))
    assert source(frame).role is Role.OWNER
    assert score(frame) == pytest.approx(1 / 1.01**0.5)
    # Karar karede kalır: iz değişse de aynı söz yeniden tanınmaz.
    frame.metadata[VOICE] = Embedding("ecapa", (0.0, 1.0))
    assert source(frame).person_id == owner.id
    assert isinstance(frame.metadata[SPEAKER], Identified)


def test_without_a_voice_or_with_a_foreign_model_the_speaker_is_unknown(db: Database) -> None:
    people, prints = SqlitePersonStore(db), SqliteVoiceprintStore(db)
    owner = people.create_owner("Sinan", "English", None, ())
    prints.set(owner.id, "ecapa", (1.0, 0.0))
    source = recognized(SpeakerMatcher(prints, 0.5), people)
    assert source(_frame(None)).role is Role.UNKNOWN
    assert source(_frame(Embedding("other", (1.0, 0.0)))).role is Role.UNKNOWN
    assert source(_frame(Embedding("ecapa", (0.0, 1.0)))).role is Role.UNKNOWN


def _said(vector: tuple[float, float], seconds: float) -> TranscriptionFrame:
    frame = _frame(Embedding("ecapa", vector))
    frame.metadata[VOICE_S] = seconds
    return frame


def test_weighted_mean_leans_to_the_longer_sample() -> None:
    assert mean([(1.0, 0.0), (0.0, 1.0)], [3.0, 1.0]) == pytest.approx((0.948683, 0.316228))
    with pytest.raises(ValueError):
        mean([(1.0, 0.0)], [0.0])


def test_the_turn_is_recognized_from_all_its_words(db: Database) -> None:
    people, prints = SqlitePersonStore(db), SqliteVoiceprintStore(db)
    owner = people.create_owner("Sinan", "English", None, ())
    prints.set(owner.id, "ecapa", (1.0, 0.0))
    source = recognized_turn(SpeakerMatcher(prints, 0.6), people)
    wake = _said((0.5, 0.866), 0.8)  # "Hey Mayen" tek başına: 0,5, eşiğin altında
    command = _said((0.9, 0.436), 2.5)  # komut: 0,9
    assert source([wake]).role is Role.UNKNOWN
    assert source([wake, command]).role is Role.OWNER
    voice = turn_voice([wake, command])
    assert voice is not None and 0.6 < cosine(voice.vector, (1.0, 0.0)) < 0.9
    assert source([_frame(None)]).role is Role.UNKNOWN


async def test_speaker_label_names_the_speaker_in_front_of_the_words() -> None:
    down, _ = await run_test(
        SpeakerLabel(lambda frame: "Ahmet"),
        frames_to_send=[TranscriptionFrame("yarın neyim var", "u", "")],
    )
    [frame] = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert frame.text == "Ahmet: yarın neyim var"


def _wav(path: Path, rate: int, channels: int, samples: list[int]) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return path


def test_samples_are_mono_16_bit_at_the_services_rate(tmp_path: Path) -> None:
    stereo = _wav(tmp_path / "s.wav", 16000, 2, [1, 2, 3, 4])
    assert read_pcm(stereo, 16000) == struct.pack("<2h", 1, 3)
    # Sessizce yeniden örneklenmez.
    with pytest.raises(VoiceError, match="16000 Hz"):
        read_pcm(_wav(tmp_path / "f.wav", 44100, 1, [0]), 16000)


def test_owner_voiceprint_is_the_mean_of_the_samples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replies = iter([[1.0, 0.0], [0.0, 1.0]])

    def fake(url: str, data: bytes | None = None) -> object:
        if url.endswith("/health"):
            return {"schema_version": SCHEMA_VERSION, "sample_rate": 16000, "voices": []}
        return {"schema_version": SCHEMA_VERSION, "model": "ecapa", "vector": next(replies)}

    monkeypatch.setattr(voice, "_request", fake)
    files = [_wav(tmp_path / f"{i}.wav", 16000, 1, [0, 1]) for i in range(2)]
    print_ = voice.voiceprint("http://speaker", files)
    assert print_.model == "ecapa"
    assert print_.vector == pytest.approx((2**-0.5, 2**-0.5))
