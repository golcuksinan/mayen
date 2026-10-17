"""İstemcinin ekranı (§7): yalnızca kendi oturumu, süzülmüş tool sonucu, ortak cihaz kuralı."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from mayen.app.screen import Screen
from mayen.core.feed import Feed
from mayen.ports.devices import Capability, Command
from mayen.ports.events import Event, EventId, EventKind, Header, SessionState
from mayen.ports.screen import SCHEMA_VERSION, screen_message
from mayen.ports.tools import (
    Effect,
    Record,
    Sensitivity,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
)
from mayen.ports.transcript import Party, Utterance, UtteranceId

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)


class Empty(BaseModel):
    pass


async def _body(args: BaseModel, ctx: ToolContext) -> ToolResult:
    return ToolResult(Status.OK)


def spec(sensitivity: Sensitivity) -> ToolSpec[Any]:
    return ToolSpec(
        name="window",
        description="",
        args=Empty,
        effect=Effect.EXTERNAL,
        sensitivity=sensitivity,
        sends_outside=False,
        timeout_s=1.0,
        run=_body,
    )


class Sent(list[dict[str, Any]]):
    async def __call__(self, message: str) -> None:
        self.append(json.loads(message))


def state(session: str, value: SessionState) -> Event:
    header = Header(EventId(uuid.uuid4()), EventKind.STATE_CHANGED, "x", NOW, session)
    return Event(header, {"state": value.value, "previous": "idle"})


def said(session: str, text: str) -> Utterance:
    return Utterance(
        UtteranceId(uuid.uuid4()), NOW, session, None, Party.PERSON, None, None, text
    )


async def test_a_personal_result_reaches_only_a_personal_device() -> None:
    result = ToolResult(Status.OK, {"windows": []}, [Record(Sensitivity.GENERAL, {"a": 1})])
    for personal, expected in ((True, 1), (False, 0)):
        sent = Sent()
        await Screen("s1", sent, lambda p=personal: p).tool(  # type: ignore[misc]
            spec(Sensitivity.PERSONAL), {"action": "list"}, result
        )
        assert len(sent) == expected
    sent = Sent()
    await Screen("s1", sent, lambda: False).tool(spec(Sensitivity.GENERAL), {}, result)
    [message] = sent
    assert message["schema_version"] == SCHEMA_VERSION and message["type"] == "tool"
    assert message["tool"] == "window" and message["status"] == "ok"
    assert message["records"] == [{"sensitivity": "GENERAL", "data": {"a": 1}}]


async def test_only_this_sessions_state_and_words_are_followed() -> None:
    feed, sent = Feed(), Sent()
    following = asyncio.create_task(Screen("s1", sent, lambda: True).follow(feed))
    await asyncio.sleep(0)
    for item in (
        state("s2", SessionState.THINKING),
        said("s2", "başkası"),
        state("s1", SessionState.LISTENING),
        Event(Header(EventId(uuid.uuid4()), EventKind.TOOL_FINISHED, "x", NOW, "s1"), {}),
        said("s1", "hava nasıl"),
    ):
        feed.publish(item)
    await asyncio.sleep(0.01)
    following.cancel()
    assert [(m["type"], m.get("state") or m.get("text")) for m in sent] == [
        ("state", "listening"),
        ("utterance", "hava nasıl"),
    ]


def test_a_command_is_not_a_screen_message() -> None:
    command = Command("c-1", Capability.MEDIA, "status", {}).encode()
    assert screen_message(command) is None
    assert screen_message("not json") is None
    assert screen_message(json.dumps({"type": "state", "state": "idle"})) is not None
