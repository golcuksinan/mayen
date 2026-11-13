"""Unut ve sil (§11.4): neyin seçildiği, kararın nereye yazıldığı, neyin gerçekten gittiği,
kimin haber aldığı."""

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest

from fakes import FakeClock
from mayen.adapters.storage.recordings import FileRecordings
from mayen.adapters.storage.sqlite import (
    Database,
    SqliteEventLog,
    SqliteRecordEraser,
    SqliteTranscript,
)
from mayen.adapters.storage.tombstones import FileTombstones, TombstoneFormatError, beside
from mayen.core.erasure import EraseError, Erasure
from mayen.core.events import Recorder
from mayen.core.transcript import Transcript
from mayen.ports.events import EventKind, ref
from mayen.ports.forget import RECORDING_NAME, Action, Chosen, Tombstone
from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import TurnId

OWNER = Caller(Role.OWNER, "1", has_personal_device=True)


@dataclass
class World:
    db: Database
    clock: FakeClock
    events: SqliteEventLog
    utterances: SqliteTranscript
    recorder: Recorder
    transcript: Transcript
    tombstones: FileTombstones
    recordings: Path
    heard: list[Chosen] = field(default_factory=list)

    def erasure(self) -> Erasure:
        e = Erasure(
            self.utterances,
            self.events,
            self.recorder,
            self.tombstones,
            self.events.related_of,
            SqliteRecordEraser(self.db),
            FileRecordings(self.recordings),
        )
        e.attach("s1", self.heard.append)
        return e

    def turn(
        self, said: str | None = "soru", answer: str | None = "cevap", recorded: bool = False
    ) -> TurnId:
        """Bir tur: başlangıç olayı, kişinin sözü ve Mayen'in cevabı, aralarında saniyeler.
        `recorded`: sözün ses kaydı da yazılır ve STT olayına bağlanır, hattaki gibi."""
        t = TurnId(uuid.uuid4())
        self.recorder.emit(EventKind.TURN_STARTED, "test", session="s1", turn_id=t)
        self.clock.advance(1)
        if said is not None:
            u = self.transcript.heard("s1", t, OWNER, said)
            related = [ref("utterance", u.id)]
            if recorded:
                related.append(ref("recording", self.record(said)))
            self.recorder.emit(
                EventKind.STT_SEGMENT, "test", session="s1", turn_id=t, related=related
            )
            self.recorder.emit(
                EventKind.TOOL_FINISHED,
                "test",
                {"tool": "weather", "arguments": {"place": said}},
                session="s1",
                turn_id=t,
            )
            self.clock.advance(1)
        if answer is not None:
            self.transcript.said("s1", t, answer, interrupted=False)
            self.clock.advance(1)
        return t

    def outside(self, text: str) -> str:
        """Tur dışında duyulan söz; kaydının kimliği."""
        u = self.transcript.heard("s1", None, OWNER, text)
        self.recorder.emit(
            EventKind.STT_SEGMENT, "test", session="s1", related=[ref("utterance", u.id)]
        )
        self.clock.advance(1)
        return ref("utterance", u.id)

    def record(self, text: str, at: datetime | None = None) -> str:
        name = (at or self.clock.now()).astimezone().strftime(RECORDING_NAME)
        self.recordings.mkdir(exist_ok=True)
        (self.recordings / f"{name}.wav").write_bytes(b"RIFF")
        (self.recordings / f"{name}.txt").write_text(text, encoding="utf-8")
        return name

    def said(self) -> list[str]:
        return [u.text for u in self.utterances.read()]

    def raw(self) -> bytes:
        """Veritabanı dosyalarının baytları: silinen metin hiçbirinde kalmamalı."""
        path = self.db.path
        files = [path, path.with_name(path.name + "-wal")]
        return b"".join(f.read_bytes() for f in files if f.exists())


@pytest.fixture
def world(tmp_path: Path) -> Iterator[World]:
    with Database(tmp_path / "m.db") as db:
        clock = FakeClock()
        events = SqliteEventLog(db)
        utterances = SqliteTranscript(db)
        recorder = Recorder(events, clock)
        yield World(
            db,
            clock,
            events,
            utterances,
            recorder,
            Transcript(utterances, clock),
            FileTombstones(beside(db.path)),
            tmp_path / "sozler",
        )


# --- seçim ---


def test_last_is_the_previous_turn_not_a_missed_wake_word(world: World) -> None:
    # Komuttan hemen önce kaçırılan "Hey Mayen" tur dışı bir sözdür; unutulan, ondan önceki tur.
    asked = world.turn("İzmir'de hava nasıl?")
    world.outside("Hey Mayen.")
    current = world.turn("son söylediğimi unut", None)
    forgotten = world.erasure().forget_last("s1", current)
    assert forgotten == Chosen(turns=(asked,))


def test_last_skips_turns_already_forgotten_and_turns_nobody_spoke_in(world: World) -> None:
    first = world.turn("birinci")
    world.turn(None, "hatırlatma")  # kimse konuşmadan açılan tur (§12)
    since = world.clock.now()
    second = world.turn("ikinci")
    erasure = world.erasure()
    assert erasure.forget_period("s1", None, since, world.clock.now()).turns == (second,)
    current = world.turn("unut", None)
    assert erasure.forget_last("s1", current).turns == (first,)


def test_saying_forget_twice_forgets_the_first_request_to_forget(world: World) -> None:
    # Kişinin söz söylediği son tur bir önceki unut isteğidir; onun içinde unutulan bir şey yok.
    world.turn("soru")
    first = world.turn("unut", None)
    erasure = world.erasure()
    erasure.forget_last("s1", first)
    again = world.turn("yine unut", None)
    assert erasure.forget_last("s1", again).turns == (first,)


def test_last_with_nothing_before_forgets_nothing(world: World) -> None:
    current = world.turn("unut", None)
    assert not world.erasure().forget_last("s1", current)
    assert world.events.related_of(EventKind.RECORD_FORGOTTEN) == []


def test_period_takes_turns_silent_turns_and_speech_outside_turns(world: World) -> None:
    before = world.turn("eski")
    since = world.clock.now()
    spoke = world.turn("içerde")
    silent = world.turn(None, None)  # sözü olmayan tur da aralıktadır
    aside = world.outside("birine söylenen")
    current = world.turn("son beş dakikayı unut", None)
    forgotten = world.erasure().forget_period("s1", current, since, world.clock.now())
    assert set(forgotten.turns) == {spoke, silent}
    assert forgotten.records()[-1] == aside
    assert before not in forgotten.turns and current not in forgotten.turns


def test_a_forgotten_turn_can_still_be_deleted(world: World) -> None:
    # Unut kaydı bırakır, sil götürür: unutulmuş tur da silinebilir.
    asked = world.turn("gizli")
    erasure = world.erasure()
    erasure.forget_last("s1", world.turn("unut", None))
    assert erasure.delete_last("s1", world.turn("sil", None)).turns != (asked,)
    since = world.clock.now()
    hidden = world.turn("ikinci gizli")
    erasure.forget_last("s1", world.turn("unut", None))
    deleted = erasure.delete_period("s1", world.turn("sil", None), since, world.clock.now())
    assert hidden in deleted.turns


# --- unut ---


def test_forgetting_goes_to_the_list_then_the_log_and_to_live_sessions(world: World) -> None:
    asked = world.turn()
    current = world.turn("unut", None)
    erasure = world.erasure()
    forgotten = erasure.forget_last("s1", current)
    assert world.tombstones.read() == [Tombstone(Action.FORGET, ref("turn", asked))]
    assert world.events.related_of(EventKind.RECORD_FORGOTTEN) == [ref("turn", asked)]
    assert world.heard == [forgotten]
    assert erasure.turn_forgotten(asked)
    # Unut silmez: söz kayıtta durur.
    assert "soru" in world.said()
    # Karar içerik taşımaz: yalnızca kimlikler ve sayılar.
    (event,) = [e for e in world.events.read() if e.header.kind is EventKind.RECORD_FORGOTTEN]
    assert event.body == {"turns": 1, "utterances": 0}
    assert event.header.turn_id == current


def test_a_failing_session_does_not_stop_the_others_but_is_reported(world: World) -> None:
    world.turn()
    current = world.turn("unut", None)
    erasure = world.erasure()

    def broken(_: Chosen) -> None:
        raise ValueError("boom")

    erasure.attach("s0", broken)
    with pytest.raises(EraseError):
        erasure.forget_last("s1", current)
    assert len(world.heard) == 1


# --- sil ---


def test_deleting_a_turn_takes_its_words_events_and_recordings(world: World) -> None:
    asked = world.turn("Erzurum'da hava nasıl?", "Erzurum'da 3 derece.", recorded=True)
    kept = world.record("başka bir söz")
    current = world.turn("son söylediğimi sil", None)
    deleted = world.erasure().delete_last("s1", current)
    assert deleted == Chosen(turns=(asked,))
    assert world.said() == ["son söylediğimi sil"]
    assert world.events.read(turn_id=asked) == []
    assert sorted(p.name for p in world.recordings.iterdir()) == [f"{kept}.txt", f"{kept}.wav"]
    (event,) = [e for e in world.events.read() if e.header.kind is EventKind.RECORD_DELETED]
    assert event.header.related == (ref("turn", asked),)
    assert event.body == {"turns": 1, "utterances": 2, "events": 3, "files": 2}
    assert world.heard == [deleted]
    assert world.tombstones.read() == [Tombstone(Action.DELETE, ref("turn", asked))]


def test_deleted_words_leave_no_bytes_in_the_database_files(world: World) -> None:
    # Silinen satırın baytları dosyada kalmaz; WAL da boşaltılır (§11.4: sil gerçekten siler).
    world.turn("Sinop'ta hava nasıl?", "Sinop'ta 17 derece.")
    assert b"Sinop" in world.raw()
    world.erasure().delete_last("s1", world.turn("sil", None))
    assert b"Sinop" not in world.raw()


def test_deleting_a_period_takes_speech_outside_turns_and_older_recordings(
    world: World,
) -> None:
    since = world.clock.now()
    aside = world.outside("birine söylenen")
    old = world.record("söze bağlanmamış eski kayıt")  # adı zamanıdır, aralıkla bulunur
    current = world.turn("son beş dakikayı sil", None)
    world.clock.advance(1)
    later = world.record("aralıktan sonra")
    deleted = world.erasure().delete_period("s1", current, since, world.clock.now())
    assert deleted.records() == [aside]
    assert "birine söylenen" not in world.said()
    names = {p.stem for p in world.recordings.iterdir()}
    assert old not in names and later in names
    # Silinen sözün STT olayı da gider: söze bağlı kopya kalmaz.
    assert not [
        e
        for e in world.events.read()
        if aside in e.header.related and e.header.kind is EventKind.STT_SEGMENT
    ]


def test_deleting_keeps_the_decisions_which_carry_only_ids(world: World) -> None:
    asked = world.turn()
    erasure = world.erasure()
    erasure.forget_last("s1", world.turn("unut", None))
    erasure.delete_last("s1", world.turn("sil", None))
    since = datetime.min.replace(tzinfo=world.clock.now().tzinfo)
    erasure.delete_period("s1", world.turn("hepsini sil", None), since, world.clock.now())
    assert ref("turn", asked) in world.events.related_of(EventKind.RECORD_FORGOTTEN)
    assert world.events.related_of(EventKind.RECORD_DELETED)


# --- mezar taşı ---


def test_an_older_database_gets_the_decisions_back_from_the_list(world: World) -> None:
    # Veritabanı eski bir yedeğe döndü: liste kararı biliyor, olay kaydı bilmiyor (§11.4).
    lost = TurnId(uuid.uuid4())
    world.tombstones.add([Tombstone(Action.FORGET, ref("turn", lost))])
    erasure = world.erasure()
    assert erasure.turn_forgotten(lost)
    assert world.events.related_of(EventKind.RECORD_FORGOTTEN) == [ref("turn", lost)]


def test_deleted_records_that_came_back_are_deleted_again_at_startup(world: World) -> None:
    back = world.turn("geri gelen", "cevap")
    world.tombstones.add([Tombstone(Action.DELETE, ref("turn", back))])
    world.erasure()
    assert world.said() == []
    assert world.events.related_of(EventKind.RECORD_DELETED) == [ref("turn", back)]


def test_a_lost_list_is_rebuilt_from_the_log(world: World) -> None:
    asked = world.turn()
    world.erasure().forget_last("s1", world.turn("unut", None))
    world.tombstones.path.unlink()
    world.erasure()
    assert world.tombstones.read() == [Tombstone(Action.FORGET, ref("turn", asked))]


def test_the_list_lives_beside_the_database_and_refuses_a_line_it_cannot_read(
    world: World,
) -> None:
    assert world.tombstones.path.parent == world.db.path.parent
    assert world.tombstones.path != world.db.path
    world.tombstones.path.write_text("turn:abc\n", encoding="utf-8")
    with pytest.raises(TombstoneFormatError):
        world.tombstones.read()


def test_recordings_without_a_folder_delete_nothing(tmp_path: Path) -> None:
    none = FileRecordings(None)
    assert none.delete(["x"]) == 0
    assert none.delete_between(datetime.now().astimezone(), datetime.now().astimezone()) == 0
    missing = FileRecordings(tmp_path / "yok")
    assert missing.delete_between(datetime.now().astimezone(), datetime.now().astimezone()) == 0
    (tmp_path / "not-a-recording.txt").write_text(json.dumps({}))
    folder = FileRecordings(tmp_path)
    assert (
        folder.delete_between(datetime(2000, 1, 1).astimezone(), datetime.now().astimezone())
        == 0
    )
