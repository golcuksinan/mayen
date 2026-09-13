"""Bağlam penceresi, bütçe ve olgu bloğu (§11.1, §11.3)."""

from pathlib import Path

import pytest

from mayen.adapters.fakes.llm import FakeLLM
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.people import PeopleRepository, Tier
from mayen.memory.budget import Budget
from mayen.memory.recall import Recall
from mayen.memory.window import ContextWindow


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    return database


def build(
    db: Database, llm: FakeLLM, *, max_facts: int = 10, reserved: int = 10
) -> ContextWindow:
    return ContextWindow(
        llm=llm,
        messages=MessageRepository(db),
        summaries=SummaryRepository(db),
        recall=Recall(FactRepository(db), PeopleRepository(db), max_facts=max_facts),
        reserved_output=reserved,
        max_messages=50,
    )


# --- bütçe ----------------------------------------------------------------------------


def test_budget_leaves_room_for_the_answer() -> None:
    assert Budget(context_size=100, reserved_output=20).history_limit(30) == 50


def test_budget_reports_a_negative_limit_rather_than_hiding_it() -> None:
    """Sabit kısım tek başına bağlamı aşıyorsa sorun geçmiş değil bütçedir (§11.1);
    sıfıra yuvarlamak o gerçeği çağırandan gizlerdi."""
    assert Budget(context_size=100, reserved_output=20).history_limit(90) == -10


def test_budget_refuses_to_spend_the_whole_context_on_the_prompt() -> None:
    with pytest.raises(ValueError):
        Budget(context_size=100, reserved_output=100)


# --- pencere --------------------------------------------------------------------------


async def test_history_comes_back_oldest_first(db: Database) -> None:
    window = build(db, FakeLLM(context_tokens=10_000))
    window.record("t1", "user", "selam")
    window.record("t1", "assistant", "merhaba")
    built = await window.build(fixed_text="SISTEM")
    assert [m.content for m in built.history] == ["selam", "merhaba"]
    assert built.trimmed == 0


async def test_token_counts_are_asked_once_and_cached(db: Database) -> None:
    """Kural 10 + §11.1: sayı sunucudan gelir ve mesaj başına önbelleklenir."""
    llm = FakeLLM(context_tokens=10_000)
    messages = MessageRepository(db)
    window = build(db, llm)
    message = window.record("t1", "user", "bir iki üç")
    assert messages.recent(1)[0].token_count is None

    await window.build(fixed_text="SISTEM")
    assert messages.recent(1)[0].token_count == 3

    asked = []
    original = llm.count_tokens

    async def counting(text: str) -> int:
        asked.append(text)
        return await original(text)

    llm.count_tokens = counting  # type: ignore[method-assign]
    built = await window.build(fixed_text="SISTEM")
    # Yalnızca sabit kısım soruldu; mesajın sayısı satırdan okundu.
    assert asked == ["SISTEM"]
    assert [m.content for m in built.history] == [message.content]


async def test_budget_overflow_trims_the_oldest_and_says_so(db: Database) -> None:
    """§11.1'in sert kırpması: en eskiler pencereden çıkar, satırlar yerinde kalır."""
    llm = FakeLLM(context_tokens=20)
    window = build(db, llm, reserved=5)
    for index in range(6):
        window.record("t1", "user", f"mesaj{index} dolgu dolgu")

    built = await window.build(fixed_text="SISTEM promptu")
    assert built.trimmed > 0
    assert window.trims == 1
    assert [m.content for m in built.history] == [
        f"mesaj{index} dolgu dolgu" for index in (2, 3, 4, 5)
    ]
    # Kırpılan satır silinmedi; özetlemenin iş listesinde duruyor (§11.1, §11.2).
    assert len(MessageRepository(db).unsummarized()) == 6


async def test_a_summary_enters_the_window_and_costs_budget(db: Database) -> None:
    llm = FakeLLM(context_tokens=10_000)
    summaries = SummaryRepository(db)
    window = build(db, llm)
    message = window.record("t1", "user", "selam")
    summary = summaries.create([message.id], "önceki konuşma")

    built = await window.build(fixed_text="SISTEM")
    assert built.summary == "önceki konuşma"
    assert summaries.latest() is not None
    # Özetin token'ı da bir kez sorulup satıra yazılıyor.
    assert summaries.latest().token_count == 2  # type: ignore[union-attr]
    assert summary.token_count is None


# --- olgular --------------------------------------------------------------------------


def test_fact_block_carries_source_date_and_the_staleness_warning(db: Database) -> None:
    """§11.3 üçünü birden istiyor; biri eksikse blok işini yapmıyor demektir."""
    people = PeopleRepository(db)
    facts = FactRepository(db)
    ali = people.create("Ali", Tier.KAYITLI_KISI)
    facts.create("kahveyi sade içer", person_id=ali.id)

    block = Recall(facts, people, max_facts=5).block()
    assert block is not None
    assert "kahveyi sade içer" in block
    assert "Ali" in block
    assert "bayat" in block


def test_no_facts_means_no_block(db: Database) -> None:
    assert Recall(FactRepository(db), PeopleRepository(db), max_facts=5).block() is None


def test_the_speakers_own_facts_come_first(db: Database) -> None:
    people = PeopleRepository(db)
    facts = FactRepository(db)
    ali = people.create("Ali", Tier.KAYITLI_KISI)
    veli = people.create("Veli", Tier.KAYITLI_KISI)
    facts.create("Veli'nin olgusu", person_id=veli.id)
    facts.create("Ali'nin olgusu", person_id=ali.id)
    facts.create("Veli'nin ikinci olgusu", person_id=veli.id)

    block = Recall(facts, people, max_facts=1).block(person_id=ali.id)
    assert block is not None
    assert "Ali'nin olgusu" in block


async def test_facts_reach_the_window(db: Database) -> None:
    people = PeopleRepository(db)
    FactRepository(db).create(
        "kahveyi sade içer", person_id=people.create("Ali", Tier.SAHIP).id
    )
    built = await build(db, FakeLLM(context_tokens=10_000)).build(fixed_text="SISTEM")
    assert built.facts is not None
    assert "kahveyi sade içer" in built.facts
