"""Unut (§11.4): neyin seçildiği, kararın nereye yazıldığı, kimin haber aldığı."""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from fakes import FakeClock
from mayen.adapters.storage.sqlite import Database, SqliteEventLog, SqliteTranscript
from mayen.adapters.storage.tombstones import FileTombstones, beside
from mayen.core.events import Recorder
from mayen.core.forgetting import ForgetError, Forgetter
from mayen.core.transcript import Transcript
from mayen.ports.events import EventKind, ref
from mayen.ports.forget import Forgotten
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
    heard: list[Forgotten] = field(default_factory=list)

    def forgetter(self) -> Forgetter:
        f = Forgetter(
            self.utterances,
            self.events,
            self.recorder,
            self.tombstones,
            lambda: self.events.related_of(EventKind.RECORD_FORGOTTEN),
        )
        f.attach("s1", self.heard.append)
        return f

    def turn(self, said: str | None = "soru", answer: str | None = "cevap") -> TurnId:
        """Bir tur: başlangıç olayı, kişinin sözü ve Mayen'in cevabı, aralarında saniyeler."""
        t = TurnId(uuid.uuid4())
        self.recorder.emit(EventKind.TURN_STARTED, "test", session="s1", turn_id=t)
        self.clock.advance(1)
        if said is not None:
            self.transcript.heard("s1", t, OWNER, said)
            self.clock.advance(1)
        if answer is not None:
            self.transcript.said("s1", t, answer, interrupted=False)
            self.clock.advance(1)
        return t

    def outside(self, text: str) -> str:
        """Tur dışında duyulan söz; kaydının kimliği."""
        u = self.transcript.heard("s1", None, OWNER, text)
        self.clock.advance(1)
        return ref("utterance", u.id)


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
        )


def test_last_is_the_previous_turn_not_a_missed_wake_word(world: World) -> None:
    # Komuttan hemen önce kaçırılan "Hey Mayen" tur dışı bir sözdür; unutulan, ondan önceki tur.
    asked = world.turn("İzmir'de hava nasıl?")
    world.outside("Hey Mayen.")
    current = world.turn("son söylediğimi unut", None)
    forgotten = world.forgetter().last("s1", current)
    assert forgotten == Forgotten(turns=(asked,))


def test_last_skips_turns_already_forgotten_and_turns_nobody_spoke_in(world: World) -> None:
    first = world.turn("birinci")
    world.turn(None, "hatırlatma")  # kimse konuşmadan açılan tur (§12)
    since = world.clock.now()
    second = world.turn("ikinci")
    forgetter = world.forgetter()
    assert forgetter.period("s1", None, since, world.clock.now()).turns == (second,)
    current = world.turn("unut", None)
    assert forgetter.last("s1", current).turns == (first,)


def test_saying_forget_twice_forgets_the_first_request_to_forget(world: World) -> None:
    # Kişinin söz söylediği son tur bir önceki unut isteğidir; onun içinde unutulan bir şey yok.
    world.turn("soru")
    first = world.turn("unut", None)
    forgetter = world.forgetter()
    forgetter.last("s1", first)
    again = world.turn("yine unut", None)
    assert forgetter.last("s1", again).turns == (first,)


def test_last_with_nothing_before_forgets_nothing(world: World) -> None:
    current = world.turn("unut", None)
    assert not world.forgetter().last("s1", current)
    assert world.events.related_of(EventKind.RECORD_FORGOTTEN) == []


def test_period_takes_turns_silent_turns_and_speech_outside_turns(world: World) -> None:
    before = world.turn("eski")
    since = world.clock.now()
    spoke = world.turn("içerde")
    silent = world.turn(None, None)  # sözü olmayan tur da aralıktadır
    aside = world.outside("birine söylenen")
    current = world.turn("son beş dakikayı unut", None)
    forgotten = world.forgetter().period("s1", current, since, world.clock.now())
    assert set(forgotten.turns) == {spoke, silent}
    assert forgotten.records()[-1] == aside
    assert before not in forgotten.turns and current not in forgotten.turns


def test_the_decision_goes_to_the_list_then_the_log_and_to_live_sessions(world: World) -> None:
    asked = world.turn()
    current = world.turn("unut", None)
    forgetter = world.forgetter()
    forgotten = forgetter.last("s1", current)
    assert world.tombstones.read() == [ref("turn", asked)]
    assert world.events.related_of(EventKind.RECORD_FORGOTTEN) == [ref("turn", asked)]
    assert world.heard == [forgotten]
    assert forgetter.turn_forgotten(asked)
    # Karar içerik taşımaz: yalnızca kimlikler ve sayılar.
    (event,) = [e for e in world.events.read() if e.header.kind is EventKind.RECORD_FORGOTTEN]
    assert event.body == {"turns": 1, "utterances": 0}
    assert event.header.turn_id == current


def test_a_failing_session_does_not_stop_the_others_but_is_reported(world: World) -> None:
    world.turn()
    current = world.turn("unut", None)
    forgetter = world.forgetter()

    def broken(_: Forgotten) -> None:
        raise ValueError("boom")

    forgetter.attach("s0", broken)
    with pytest.raises(ForgetError):
        forgetter.last("s1", current)
    assert len(world.heard) == 1


def test_an_older_database_gets_the_decisions_back_from_the_list(world: World) -> None:
    # Veritabanı eski bir yedeğe döndü: liste kararı biliyor, olay kaydı bilmiyor (§11.4).
    lost = TurnId(uuid.uuid4())
    world.tombstones.add([ref("turn", lost)])
    forgetter = world.forgetter()
    assert forgetter.turn_forgotten(lost)
    assert world.events.related_of(EventKind.RECORD_FORGOTTEN) == [ref("turn", lost)]


def test_a_lost_list_is_rebuilt_from_the_log(world: World) -> None:
    asked = world.turn()
    current = world.turn("unut", None)
    world.forgetter().last("s1", current)
    world.tombstones.path.unlink()
    world.forgetter()
    assert world.tombstones.read() == [ref("turn", asked)]


def test_the_list_lives_beside_the_database_not_inside_it(world: World) -> None:
    assert world.tombstones.path.parent == world.db.path.parent
    assert world.tombstones.path != world.db.path
