"""Boştaki bellek işi ve preemption (§11.2, §11.3, Kural 11)."""

import asyncio
from collections.abc import AsyncGenerator, Sequence
from pathlib import Path

import pytest

from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.llm import PromptMessage
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.facts import FactRepository
from mayen.memory.background import BackgroundWork
from mayen.memory.digest import Digest


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    return database


def digest(db: Database, llm: FakeLLM, *, keep_recent: int = 1, batch_size: int = 40) -> Digest:
    return Digest(
        llm=llm,
        messages=MessageRepository(db),
        summaries=SummaryRepository(db),
        facts=FactRepository(db),
        keep_recent=keep_recent,
        batch_size=batch_size,
        max_tokens=128,
    )


def conversation(db: Database, count: int = 4) -> None:
    messages = MessageRepository(db)
    for index in range(count):
        messages.append("t1", "user", f"cümle{index}")


# --- digest ---------------------------------------------------------------------------


async def test_facts_and_summary_come_from_one_batch(db: Database) -> None:
    """Aynı yığın: `summary_id` ikisinin birden filigranı (bkz. modül başlığı)."""
    conversation(db, 4)
    llm = FakeLLM(["- Ali kahveyi sade içer", "Ali kahveden konuştu."])
    result = await digest(db, llm).run()

    assert result.messages == 3  # sonuncusu `keep_recent` yüzünden dışarıda
    assert result.summarized
    assert [fact.content for fact in FactRepository(db).list_all()] == ["Ali kahveyi sade içer"]
    assert SummaryRepository(db).latest().content == "Ali kahveden konuştu."  # type: ignore[union-attr]
    assert [m.content for m in MessageRepository(db).unsummarized()] == ["cümle3"]


async def test_nothing_pending_means_no_generation(db: Database) -> None:
    llm = FakeLLM()  # sıraya yanıt konmadı: çağrılırsa test patlar
    assert (await digest(db, llm).run()).messages == 0


async def test_no_fact_worth_keeping_is_a_valid_answer(db: Database) -> None:
    conversation(db, 2)
    result = await digest(db, FakeLLM(["YOK", "Kısa bir sohbet."])).run()
    assert result.facts == 0
    assert result.summarized


async def test_the_same_fact_is_not_written_twice(db: Database) -> None:
    """Çıkarım ile özet arasında iptal olursa yığın tekrar işlenir; kopya olmamalı."""
    conversation(db, 2)
    facts = FactRepository(db)
    facts.create("Ali kahveyi sade içer")
    await digest(db, FakeLLM(["- Ali kahveyi sade içer", "Özet."])).run()
    assert len(facts.list_all()) == 1


async def test_the_previous_summary_is_carried_into_the_new_one(db: Database) -> None:
    conversation(db, 4)
    summaries = SummaryRepository(db)
    summaries.create([1], "eski özet")
    llm = FakeLLM(["YOK", "yeni özet"])
    await digest(db, llm).run()
    assert "eski özet" in llm.calls[-1][0].content


async def test_an_empty_summary_is_refused(db: Database) -> None:
    conversation(db, 2)
    with pytest.raises(ValueError):
        await digest(db, FakeLLM(["YOK", "   "])).run()


# --- arka plan koşucusu ---------------------------------------------------------------


class SlowLLM(FakeLLM):
    """Üretimi bir olay salıverene kadar süren LLM: preemption'ın görülebildiği tek yer."""

    def __init__(self) -> None:
        super().__init__(["- olgu", "özet"])
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def stream(
        self,
        messages: Sequence[PromptMessage],
        *,
        grammar: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str]:
        self.started.set()
        await self.release.wait()
        async for chunk in super().stream(messages, grammar=grammar, max_tokens=max_tokens):
            yield chunk


async def test_a_turn_preempts_a_running_job_and_nothing_is_written(db: Database) -> None:
    """§11.3: boşta başlamış iş, tur kuyruğa girer girmez iptal edilir; yarım kalan
    sonuç yazılmaz."""
    conversation(db, 3)
    llm = SlowLLM()
    work = BackgroundWork([digest(db, llm).run], delay_seconds=0)
    await work.start()
    await asyncio.wait_for(llm.started.wait(), timeout=1)

    work.turn_started()
    await asyncio.sleep(0)
    assert work.preempted == 1
    assert FactRepository(db).list_all() == []
    assert SummaryRepository(db).latest() is None
    await work.stop()


async def test_the_job_runs_again_at_the_next_idle_moment(db: Database) -> None:
    conversation(db, 3)
    llm = SlowLLM()
    work = BackgroundWork([digest(db, llm).run], delay_seconds=0)
    await work.start()
    await asyncio.wait_for(llm.started.wait(), timeout=1)
    work.turn_started()
    await asyncio.sleep(0)

    llm.release.set()
    work.turn_finished()
    for _ in range(100):
        await asyncio.sleep(0)
        if SummaryRepository(db).latest() is not None:
            break
    assert SummaryRepository(db).latest() is not None
    await work.stop()


async def test_a_failing_job_does_not_kill_the_runner(db: Database) -> None:
    """Kural 13: patlayan bellek işi kayda geçer, koşucuyu öldürmez."""
    calls = []

    async def explode() -> None:
        calls.append(1)
        raise RuntimeError("patladı")

    work = BackgroundWork([explode], delay_seconds=0)
    await work.start()
    for _ in range(50):
        await asyncio.sleep(0)
        if calls:
            break
    work.turn_started()
    work.turn_finished()
    for _ in range(100):
        await asyncio.sleep(0)
        if len(calls) > 1:
            break
    assert len(calls) > 1
    await work.stop()
