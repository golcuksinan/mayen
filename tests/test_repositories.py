"""Repository'ler: gidiş-dönüş ve şemanın gerçekten koruduğu şeyler."""

import sqlite3
from pathlib import Path

import pytest

from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.boot import BootRepository
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.courses import CourseRepository, CourseSession
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository, Tier, VoiceProfileRepository
from mayen.data.repositories.tasks import TaskRepository, TaskStatus
from mayen.data.repositories.traces import TraceRepository


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    return database


# --- kişiler ve ses profilleri ---------------------------------------------------------


def test_person_round_trip(db: Database) -> None:
    people = PeopleRepository(db)

    created = people.create("Ali", Tier.BEKLEYEN, phone="555")

    assert people.get(created.id) == created
    assert created.tier is Tier.BEKLEYEN


def test_missing_person_is_none_not_an_error(db: Database) -> None:
    assert PeopleRepository(db).get(404) is None


def test_update_leaves_unnamed_fields_alone(db: Database) -> None:
    people = PeopleRepository(db)
    created = people.create("Ali", Tier.KAYITLI_KISI, phone="555")

    updated = people.update(created.id, phone="666")

    assert updated is not None
    assert (updated.name, updated.phone) == ("Ali", "666")


def test_update_does_not_change_the_tier(db: Database) -> None:
    """Yetki yükseltme §10.4'e göre ayrı ve geri alınamaz bir iş; alan düzenlemesine
    karışmamalı."""
    people = PeopleRepository(db)
    created = people.create("Ali", Tier.BEKLEYEN)

    people.update(created.id, name="Ali Veli")

    after = people.get(created.id)
    assert after is not None and after.tier is Tier.BEKLEYEN


def test_set_tier_promotes(db: Database) -> None:
    people = PeopleRepository(db)
    created = people.create("Ali", Tier.BEKLEYEN)

    promoted = people.set_tier(created.id, Tier.KAYITLI_KISI)

    assert promoted is not None and promoted.tier is Tier.KAYITLI_KISI


def test_unknown_tier_is_rejected_by_the_schema(db: Database) -> None:
    with pytest.raises(sqlite3.IntegrityError), db.transaction() as conn:
        conn.execute(
            "INSERT INTO people (name, tier, created_at, updated_at) "
            "VALUES ('X', 'KRAL', '', '')"
        )


def test_voice_profile_is_one_per_person_and_overwrites(db: Database) -> None:
    people = PeopleRepository(db)
    profiles = VoiceProfileRepository(db)
    person = people.create("Ali", Tier.KAYITLI_KISI)

    profiles.save(person.id, b"\x01\x02", 3, "ecapa-v1")
    profiles.save(person.id, b"\x03\x04", 5, "ecapa-v1")

    stored = profiles.list_all()
    assert len(stored) == 1
    assert (stored[0].embedding, stored[0].sample_count) == (b"\x03\x04", 5)


def test_deleting_a_person_takes_the_voice_profile(db: Database) -> None:
    people = PeopleRepository(db)
    profiles = VoiceProfileRepository(db)
    person = people.create("Ali", Tier.KAYITLI_KISI)
    profiles.save(person.id, b"\x01", 1, "ecapa-v1")

    assert people.delete(person.id) is True
    assert profiles.list_all() == []


# --- konuşma geçmişi ve özetler --------------------------------------------------------


def test_message_round_trip_and_order(db: Database) -> None:
    messages = MessageRepository(db)
    messages.append("t1", "user", "merhaba")
    messages.append("t1", "assistant", "hello")

    recent = messages.recent(10)

    assert [(m.role, m.content) for m in recent] == [
        ("user", "merhaba"),
        ("assistant", "hello"),
    ]


def test_recent_returns_the_last_n_oldest_first(db: Database) -> None:
    messages = MessageRepository(db)
    for i in range(5):
        messages.append("t1", "user", str(i))

    assert [m.content for m in messages.recent(2)] == ["3", "4"]


def test_token_count_starts_empty_not_zero(db: Database) -> None:
    """Sayı sayaçtan gelir, tahmin edilmez (Kural 10). Sıfır bir tahmindir."""
    message = MessageRepository(db).append("t1", "user", "merhaba")

    assert message.token_count is None


def test_token_count_is_filled_in_later(db: Database) -> None:
    messages = MessageRepository(db)
    message = messages.append("t1", "user", "merhaba")

    messages.set_token_count(message.id, 7)

    assert messages.recent(1)[0].token_count == 7


def test_summarizing_marks_its_messages_in_the_same_step(db: Database) -> None:
    messages = MessageRepository(db)
    summaries = SummaryRepository(db)
    first = messages.append("t1", "user", "a")
    second = messages.append("t1", "assistant", "b")
    third = messages.append("t2", "user", "c")

    summary = summaries.create([first.id, second.id], "a ve b konuşuldu")

    assert (summary.from_message, summary.to_message) == (first.id, second.id)
    assert [m.id for m in messages.unsummarized()] == [third.id]
    assert summaries.latest() == summary


def test_summarized_messages_stay_in_the_database(db: Database) -> None:
    """Kırpma ve özetleme satır silmez (§11.1)."""
    messages = MessageRepository(db)
    message = messages.append("t1", "user", "a")

    SummaryRepository(db).create([message.id], "özet")

    assert [m.content for m in messages.recent(10)] == ["a"]


def test_empty_summary_is_rejected(db: Database) -> None:
    with pytest.raises(ValueError, match="Boş mesaj"):
        SummaryRepository(db).create([], "hiçbir şey")


# --- olgular ---------------------------------------------------------------------------


def test_facts_are_filterable_by_person(db: Database) -> None:
    people = PeopleRepository(db)
    facts = FactRepository(db)
    ali = people.create("Ali", Tier.KAYITLI_KISI)
    facts.create("kahveyi sade içer", person_id=ali.id)
    facts.create("tanınmayan birinden", person_id=None)

    assert [f.content for f in facts.list_all(person_id=ali.id)] == ["kahveyi sade içer"]
    assert len(facts.list_all()) == 2


def test_deleting_a_person_keeps_their_facts(db: Database) -> None:
    """Olgu ortak havuzda (§11.3); kişi silinince bilgi buharlaşmaz, etiketi düşer."""
    people = PeopleRepository(db)
    facts = FactRepository(db)
    ali = people.create("Ali", Tier.KAYITLI_KISI)
    facts.create("kahveyi sade içer", person_id=ali.id)

    people.delete(ali.id)

    remaining = facts.list_all()
    assert len(remaining) == 1
    assert remaining[0].person_id is None


def test_fact_delete(db: Database) -> None:
    facts = FactRepository(db)
    fact = facts.create("bir şey")

    assert facts.delete(fact.id) is True
    assert facts.delete(fact.id) is False


# --- notlar ----------------------------------------------------------------------------


def test_note_search_finds_substrings(db: Database) -> None:
    notes = NoteRepository(db)
    notes.create("süt almayı unutma")
    notes.create("araba muayenesi")

    assert [n.body for n in notes.search("süt")] == ["süt almayı unutma"]


def test_note_search_treats_wildcards_as_text(db: Database) -> None:
    """`%` LIKE'ın jokeri; kullanıcı metninde geçince arama sessizce her şeyi döndürürdü."""
    notes = NoteRepository(db)
    notes.create("indirim %20")
    notes.create("alakasız not")

    assert [n.body for n in notes.search("%")] == ["indirim %20"]


# --- ders programı ---------------------------------------------------------------------


def _lecture(code: str, day: int) -> CourseSession:
    return CourseSession(code, f"{code} dersi", day, "09:00", "10:50", "A101")


def test_replacing_a_term_swaps_only_that_term(db: Database) -> None:
    courses = CourseRepository(db)
    courses.replace_term("2025-guz", [_lecture("MAT101", 1)])
    courses.replace_term("2026-bahar", [_lecture("FIZ102", 2)])

    courses.replace_term("2026-bahar", [_lecture("FIZ102", 3), _lecture("KIM103", 3)])

    assert [c.course_code for c in courses.for_term("2025-guz")] == ["MAT101"]
    assert [c.course_code for c in courses.for_day("2026-bahar", 3)] == ["FIZ102", "KIM103"]
    assert courses.for_day("2026-bahar", 2) == []


def test_invalid_day_is_rejected_by_the_schema(db: Database) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        CourseRepository(db).replace_term("2026-bahar", [_lecture("MAT101", 8)])


# --- zamanlanmış görevler --------------------------------------------------------------


def test_task_round_trip_with_payload(db: Database) -> None:
    tasks = TaskRepository(db)

    task = tasks.create("hatirlatma", {"metin": "dersin var"}, "2026-08-09T15:00:00Z")

    assert task.status is TaskStatus.BEKLIYOR
    assert tasks.pending() == [task]
    assert tasks.pending()[0].payload == {"metin": "dersin var"}


def test_only_tasks_whose_time_has_come_are_due(db: Database) -> None:
    tasks = TaskRepository(db)
    soon = tasks.create("hatirlatma", {}, "2026-08-09T15:00:00Z")
    tasks.create("hatirlatma", {}, "2026-08-09T17:00:00Z")

    assert [t.id for t in tasks.due("2026-08-09T16:00:00Z")] == [soon.id]


def test_settling_a_task_takes_it_out_of_the_queue(db: Database) -> None:
    tasks = TaskRepository(db)
    task = tasks.create("hatirlatma", {}, "2026-08-09T15:00:00Z")

    settled = tasks.settle(task.id, TaskStatus.CALISTI)

    assert settled is not None and settled.status is TaskStatus.CALISTI
    assert tasks.pending() == []


def test_a_task_cannot_be_settled_twice(db: Database) -> None:
    """İki koşucunun aynı görevi çalıştırması, kullanıcının hatırlatıcıyı iki kez
    duyması demek."""
    tasks = TaskRepository(db)
    task = tasks.create("hatirlatma", {}, "2026-08-09T15:00:00Z")
    tasks.settle(task.id, TaskStatus.CALISTI)

    assert tasks.settle(task.id, TaskStatus.IPTAL) is None


def test_dropped_task_keeps_its_reason(db: Database) -> None:
    """§12: düşürülen görev sessizce kaybolmaz, düşürüldüğü kaydedilir."""
    tasks = TaskRepository(db)
    task = tasks.create("hatirlatma", {}, "2026-08-09T15:00:00Z")

    settled = tasks.settle(task.id, TaskStatus.DUSURULDU, outcome="tolerans aşıldı")

    assert settled is not None and settled.outcome == "tolerans aşıldı"


def test_pending_is_not_a_settlement(db: Database) -> None:
    tasks = TaskRepository(db)
    task = tasks.create("hatirlatma", {}, "2026-08-09T15:00:00Z")

    with pytest.raises(ValueError, match="sonuç değil"):
        tasks.settle(task.id, TaskStatus.BEKLIYOR)


# --- açılış kayıtları ------------------------------------------------------------------


def test_previous_boot_is_the_one_before_this_one(db: Database) -> None:
    boots = BootRepository(db)
    first = boots.start("0.1.0")
    boots.stop(first.id)
    boots.start("0.1.0")

    previous = boots.previous()

    assert previous is not None and previous.id == first.id
    assert previous.stopped_at is not None


def test_first_boot_has_no_previous(db: Database) -> None:
    boots = BootRepository(db)
    boots.start("0.1.0")

    assert boots.previous() is None


def test_a_crashed_run_has_no_stop_time(db: Database) -> None:
    boots = BootRepository(db)
    boots.start("0.1.0")
    boots.start("0.1.0")

    previous = boots.previous()
    assert previous is not None and previous.stopped_at is None


# --- tur izleri ------------------------------------------------------------------------


def test_trace_round_trip_with_stages(db: Database) -> None:
    traces = TraceRepository(db)
    traces.start("t1", "masaustu")
    traces.add_stage("t1", "stt", duration_ms=180)
    traces.add_stage("t1", "llm_ilk_token", duration_ms=420)
    traces.finish("t1", "tamamlandi")

    trace = traces.get("t1")

    assert trace is not None
    assert [(s.seq, s.name) for s in trace.stages] == [(1, "stt"), (2, "llm_ilk_token")]
    assert trace.outcome == "tamamlandi"
    assert trace.ended_at is not None


def test_stage_numbering_is_per_turn(db: Database) -> None:
    traces = TraceRepository(db)
    traces.start("t1", "masaustu")
    traces.start("t2", "masaustu")
    traces.add_stage("t1", "stt")
    traces.add_stage("t2", "stt")

    second = traces.get("t2")
    assert second is not None and [s.seq for s in second.stages] == [1]


def test_missing_trace_is_none(db: Database) -> None:
    assert TraceRepository(db).get("yok") is None
