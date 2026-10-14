"""Bağlam bloğu (§8.3, §8.6, §11.1): içeriği, yeri ve geçmişe yazılmaması."""

import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pipecat.processors.aggregators.llm_context import LLMContext

from fakes import FakeClock
from mayen.adapters.storage.sqlite import Database, SqlitePersonStore
from mayen.core.context import ContextBlock, when
from mayen.core.presence import Presence
from mayen.core.timers import SYSTEM
from mayen.pipeline.llm import StepCap, Steps, count_steps, llm_service, with_block
from mayen.pipeline.session import UNIDENTIFIED
from mayen.ports.models import Endpoint, ModelRole
from mayen.ports.people import DeviceId
from mayen.ports.tools import Caller, Role

PHONE = DeviceId("phone")
RULE = "Answer in {language}."


@pytest.fixture(autouse=True)
def istanbul(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("TZ", "Europe/Istanbul")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.fixture
def people(tmp_path: Path) -> Iterator[SqlitePersonStore]:
    with Database(tmp_path / "m.db") as db:
        yield SqlitePersonStore(db)


def test_date_is_written_with_the_month_name_in_local_time() -> None:
    # 5 Mart: sayıyla yazılsa 03-05 ile 05-03 karışırdı.
    assert when(datetime(2026, 3, 5, 6, 30, tzinfo=UTC)) == "Thursday, 5 March 2026, 09:30"


def block_for(people: SqlitePersonStore, presence: Presence | None = None) -> ContextBlock:
    clock = FakeClock(datetime(2026, 10, 14, 17, 41, tzinfo=UTC))
    return ContextBlock(people, presence or Presence(), clock, RULE, "English")


def test_known_speaker_gets_their_profile_and_language(people: SqlitePersonStore) -> None:
    owner = people.create_owner("Sinan", "Turkish", "efendim", (PHONE,))
    caller = Caller(Role.OWNER, owner.id, has_personal_device=True)
    assert block_for(people).render("s1", caller) == (
        "[context]\n"
        "date/time: Wednesday, 14 October 2026, 20:41\n"
        'speaker: {"name": "Sinan", "role": "owner", "language": "Turkish", '
        '"address_as": "efendim"}\n'
        "Answer in Turkish."
    )


def test_unknown_speaker_gets_only_a_role_and_the_default_language(
    people: SqlitePersonStore,
) -> None:
    people.create_owner("Sinan", "Turkish", None, (PHONE,))
    rendered = block_for(people).render("s1", UNIDENTIFIED)
    assert 'speaker: {"role": "unknown"}' in rendered
    assert "Sinan" not in rendered
    assert rendered.endswith("Answer in English.")


def test_system_turn_speaks_the_language_of_the_device_person(
    people: SqlitePersonStore,
) -> None:
    owner = people.create_owner("Sinan", "Turkish", None, (PHONE,))
    presence = Presence()
    presence.connected("phone-session", PHONE, owner.id)
    presence.connected("shared-session", DeviceId("kitchen"), None)
    block = block_for(people, presence)
    assert block.language("phone-session", SYSTEM) == "Turkish"
    assert block.language("shared-session", SYSTEM) == "English"
    assert 'speaker: {"role": "system"}' in block.render("phone-session", SYSTEM)


def test_block_goes_before_the_message_that_opened_the_turn() -> None:
    history: list[Any] = [
        {"role": "user", "content": "add a note"},
        {"role": "assistant", "content": "done"},
        {"role": "developer", "content": '{"trigger": "timer"}'},
        {"role": "assistant", "tool_calls": []},
        {"role": "tool", "content": "{}"},
    ]
    sent = with_block(history, "[context]")
    assert sent[:2] == history[:2]  # geçmiş önekte aynen durur
    assert sent[2] == {"role": "developer", "content": "[context]"}
    assert sent[3:] == history[2:]  # tur içinde sonradan gelenler bloğun arkasında


class Captured:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    async def create(self, **params: Any) -> None:  # noqa: ANN401
        self.requests.append(params)


async def test_block_is_rebuilt_per_request_and_never_written_to_history() -> None:
    endpoint = Endpoint(ModelRole.TALKER, "http://127.0.0.1:1/v1", "m", 4096, True)
    blocks = iter(["[context] 1", "[context] 2"])
    service = llm_service(
        endpoint, "You are Mayen.", lambda: next(blocks), StepCap(5, 2), lambda _: False
    )
    captured = Captured()
    service._client.chat.completions.create = captured.create
    context = LLMContext(messages=[{"role": "user", "content": "hi"}])

    await service.get_chat_completions(context)
    context.add_message({"role": "assistant", "content": "hello"})
    context.add_message({"role": "user", "content": "and now?"})
    await service.get_chat_completions(context)

    history: list[Any] = context.get_messages()
    assert [m["content"] for m in history] == ["hi", "hello", "and now?"]
    first, second = (r["messages"] for r in captured.requests)
    assert first[0] == second[0] == {"role": "system", "content": "You are Mayen."}
    assert [m["content"] for m in first[1:]] == ["[context] 1", "hi"]
    assert [m["content"] for m in second[1:]] == ["hi", "hello", "[context] 2", "and now?"]


def calls(*ids: str) -> dict[str, Any]:
    return {
        "role": "assistant",
        "tool_calls": [
            {"id": i, "type": "function", "function": {"name": "f", "arguments": "{}"}}
            for i in ids
        ],
    }


def results(*ids: str) -> list[dict[str, Any]]:
    return [{"role": "tool", "tool_call_id": i, "content": "{}"} for i in ids]


def test_steps_are_counted_in_the_current_turn_and_corrections_apart() -> None:
    history: list[Any] = [
        {"role": "user", "content": "earlier"},
        calls("old"),
        *results("old"),
        {"role": "user", "content": "now"},
        calls("a", "bad1"),  # biri geçerli: adım
        *results("a", "bad1"),
        calls("bad2"),  # hepsi bozuk: düzeltme
        *results("bad2"),
        calls("b"),
        *results("b"),
    ]
    steps = count_steps(history, lambda i: i.startswith("bad"))
    assert steps == Steps(taken=2, corrections=1)
    assert not StepCap(3, 1).reached(steps)
    assert StepCap(2, 1).reached(steps)
    assert StepCap(3, 0).reached(steps)


async def test_capped_request_goes_without_tools_and_says_why() -> None:
    endpoint = Endpoint(ModelRole.TALKER, "http://127.0.0.1:1/v1", "m", 4096, True)
    service = llm_service(endpoint, "S", lambda: "[context]", StepCap(2, 0), lambda _: False)
    captured = Captured()
    service._client.chat.completions.create = captured.create
    history: list[Any] = [{"role": "user", "content": "find it"}, calls("a"), *results("a")]
    await service.get_chat_completions(LLMContext(messages=history))
    history += [calls("b"), *results("b")]
    context = LLMContext(messages=history)
    await service.get_chat_completions(context)

    free, capped = captured.requests
    assert free.get("tool_choice") != "none"
    assert capped["tool_choice"] == "none"
    last = capped["messages"][-1]
    assert last["role"] == "developer"
    assert json.loads(last["content"]) == {"step_cap": {"steps": 2, "corrections": 0}}
    # Tavan notu geçmişe yazılmaz.
    assert len(context.get_messages()) == 5
