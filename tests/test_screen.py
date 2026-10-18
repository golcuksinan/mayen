"""İstemcinin ekranı (§7): yalnızca kendi oturumu, süzülmüş tool sonucu, ortak cihaz kuralı."""

import asyncio
import json
import threading
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
import sounddevice as sd  # type: ignore[import-untyped]  # tip bilgisi yok
from pydantic import BaseModel

from mayen.app.screen import Screen
from mayen.clients import screen as desktop_screen
from mayen.core.feed import Feed
from mayen.ports.devices import Capability, Command
from mayen.ports.events import Event, EventId, EventKind, Header, SessionState
from mayen.ports.screen import SCHEMA_VERSION, encode_utterance, screen_message
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
from mayen.ports.triggers import TurnId

NOW = datetime(2026, 10, 17, 22, 0, tzinfo=UTC)
TURN = TurnId(uuid.uuid4())


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


def said(session: str, text: str, turn: TurnId | None = TURN) -> Utterance:
    return Utterance(
        UtteranceId(uuid.uuid4()), NOW, session, turn, Party.PERSON, None, None, text
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


async def test_only_this_sessions_state_and_words_said_in_a_turn_are_followed() -> None:
    feed, sent = Feed(), Sent()
    following = asyncio.create_task(Screen("s1", sent, lambda: True).follow(feed))
    await asyncio.sleep(0)
    for item in (
        state("s2", SessionState.THINKING),
        said("s2", "başkası"),
        state("s1", SessionState.LISTENING),
        Event(Header(EventId(uuid.uuid4()), EventKind.TOOL_FINISHED, "x", NOW, "s1"), {}),
        said("s1", "televizyondaki ses", turn=None),
        said("s1", "hava nasıl"),
    ):
        feed.publish(item)
    await asyncio.sleep(0.01)
    following.cancel()
    assert [(m["type"], m.get("state") or m.get("text")) for m in sent] == [
        ("state", "listening"),
        ("utterance", "hava nasıl"),
    ]


def test_the_language_tags_of_what_mayen_said_are_not_shown() -> None:
    text = encode_utterance(said("s1", "Merhaba <tr>Sinan</tr>, ses <tr>yüzde elli</tr>."))
    assert json.loads(text)["text"] == "Merhaba Sinan, ses yüzde elli."


def test_a_command_is_not_a_screen_message() -> None:
    command = Command("c-1", Capability.MEDIA, "status", {}).encode()
    assert screen_message(command) is None
    assert screen_message("not json") is None
    assert screen_message(json.dumps({"type": "state", "state": "idle"})) is not None


async def test_a_screen_that_cannot_send_never_breaks_the_turn() -> None:
    async def broken(message: str) -> None:
        raise RuntimeError("transport closed")

    screen = Screen("s1", broken, lambda: True)
    await screen.tool(spec(Sensitivity.GENERAL), {}, ToolResult(Status.OK))
    feed = Feed()
    following = asyncio.create_task(screen.follow(feed))
    await asyncio.sleep(0)
    feed.publish(state("s1", SessionState.THINKING))
    await asyncio.sleep(0.01)
    assert not following.done()  # takip sürer; düşen yalnızca o mesaj
    following.cancel()


class FakePage:
    def __init__(self) -> None:
        self.connections: list[str] = []

    def screen(self, message: dict[str, Any]) -> None:
        pass

    def connection(self, state: str) -> None:
        self.connections.append(state)


def test_any_failure_of_a_connection_attempt_reaches_the_screen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for error in (OSError("refused"), sd.PortAudioError("no microphone"), RuntimeError("bug")):

        async def failing(*_: Any, error: BaseException = error) -> None:  # noqa: ANN401
            raise error

        monkeypatch.setattr(desktop_screen, "run", failing)
        page = FakePage()
        desktop_screen.attempt("ws://x", cast(desktop_screen.Page, page))
        assert page.connections == ["lost"]


class FakeWindow:
    def __init__(self) -> None:
        self.events = SimpleNamespace(loaded=threading.Event())
        self.ran: list[str] = []
        self.done = threading.Event()

    def evaluate_js(self, script: str) -> None:
        self.ran.append(script)
        if len(self.ran) == 2:
            self.done.set()
        if len(self.ran) == 1:
            raise RuntimeError("page threw")


def test_a_failing_page_call_does_not_stop_the_screen() -> None:
    window = FakeWindow()
    page = desktop_screen.Page(cast(Any, window))
    page.connection("live")
    page.screen({"type": "state", "state": "idle"})
    window.events.loaded.set()
    assert window.done.wait(2)
    assert window.ran[1].startswith("window.mayenScreen(")
