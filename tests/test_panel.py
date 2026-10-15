"""Panelin ucu (§14): yalnızca sahibin cihazı ve izinli adres; önce geçmiş, sonra canlı."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.typing import Origin

from mayen.adapters.storage.sqlite import Database
from mayen.app.config import ConfigError, load
from mayen.app.panel import EVENTS_PATH
from mayen.app.server import text_app
from mayen.app.wiring import Core
from mayen.core.feed import Feed
from mayen.ports.events import EventKind, stamp
from mayen.ports.panel import SCHEMA_VERSION
from mayen.ports.people import DeviceId, Person
from mayen.ports.tools import Caller, Role, Status
from test_app import FixedIdentity, config_dir, until

PANEL_ORIGIN = "http://localhost:5173"


@asynccontextmanager
async def serving(tmp_path: Path) -> AsyncIterator[tuple[Core, FixedIdentity, str]]:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    config.storage_path.parent.mkdir(parents=True)
    with Database(config.storage_path) as db:
        core = Core(config, db)
        core.people.create_owner("Sinan", "tr", None, (DeviceId("nPhone"),))
        identity = FixedIdentity()
        server = uvicorn.Server(
            uvicorn.Config(text_app(core, identity), host="127.0.0.1", port=0, log_config=None)
        )
        task = asyncio.create_task(server.serve())
        await until(lambda: server.started)
        port = server.servers[0].sockets[0].getsockname()[1]
        try:
            yield core, identity, f"ws://127.0.0.1:{port}{EVENTS_PATH}"
        finally:
            server.should_exit = True
            await task


async def received(ws: ClientConnection) -> dict[str, Any]:
    message = json.loads(await asyncio.wait_for(ws.recv(), 2))
    assert message["schema_version"] == SCHEMA_VERSION
    return message  # type: ignore[no-any-return]


async def test_owner_gets_history_then_live(tmp_path: Path) -> None:
    async with serving(tmp_path) as (core, identity, url):
        before = core.recorder.clock.now() - timedelta(seconds=1)
        core.recorder.emit(EventKind.TURN_STARTED, "test", {"source": "text"}, session="s1")
        owner = Caller(Role.OWNER, "1", has_personal_device=True)
        core.transcript.heard("s1", None, owner, "merhaba")
        identity.next = DeviceId("nPhone")
        async with connect(f"{url}?since={stamp(before)}", origin=Origin(PANEL_ORIGIN)) as ws:
            first, second, live = [await received(ws) for _ in range(3)]
            assert (first["type"], first["kind"], first["session"]) == (
                "event",
                "turn.started",
                "s1",
            )
            assert first["body"] == {"source": "text"}
            assert (second["type"], second["text"], second["role"]) == (
                "utterance",
                "merhaba",
                "owner",
            )
            assert live["type"] == "live"
            core.recorder.emit(
                EventKind.STATE_CHANGED,
                "test",
                {"state": "thinking", "previous": "idle"},
                session="s1",
                status=Status.OK,
            )
            event = await received(ws)
            assert (event["kind"], event["body"]["state"], event["status"]) == (
                "state.changed",
                "thinking",
                "ok",
            )
        await until(lambda: not core.feed._subscribers)


async def test_without_since_only_live_arrives(tmp_path: Path) -> None:
    async with serving(tmp_path) as (core, identity, url):
        core.recorder.emit(EventKind.TURN_STARTED, "test", {}, session="old")
        identity.next = DeviceId("nPhone")
        async with connect(url) as ws:  # tarayıcı dışı bağlantıda Origin yok
            assert (await received(ws))["type"] == "live"
            core.recorder.emit(EventKind.TURN_FINISHED, "test", {}, session="new")
            assert (await received(ws))["session"] == "new"


@pytest.mark.parametrize(
    ("device", "origin", "query"),
    [
        (None, PANEL_ORIGIN, ""),  # doğrulanmamış cihaz
        ("nLaptop", PANEL_ORIGIN, ""),  # kimseye eşleşmemiş, ortak cihaz
        ("nPhone", "http://example.com", ""),  # sahibin tarayıcısında başka bir sayfa
        ("nPhone", PANEL_ORIGIN, "?since=yesterday"),
    ],
)
async def test_refused(tmp_path: Path, device: str | None, origin: str, query: str) -> None:
    async with serving(tmp_path) as (core, identity, url):
        identity.next = None if device is None else DeviceId(device)
        with pytest.raises(InvalidStatus):
            async with connect(f"{url}{query}", origin=Origin(origin)):
                pass
        assert not core.feed._subscribers


async def test_acquaintance_device_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with serving(tmp_path) as (core, identity, url):
        ali = Person("2", "Ali", Role.ACQUAINTANCE, "tr", None, (DeviceId("nAli"),))
        monkeypatch.setattr(core.people, "by_device", lambda _: ali)
        identity.next = DeviceId("nAli")
        with pytest.raises(InvalidStatus):
            async with connect(url):
                pass


def test_missing_panel_build_is_a_config_error(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    text = path.read_text(encoding="utf-8").replace(
        "  # dist: ../panel/dist", "  dist: nowhere"
    )
    path.write_text(text, encoding="utf-8")
    config = load(path, {"MAYEN_MODEL": "local"})
    config.storage_path.parent.mkdir(parents=True)
    with Database(config.storage_path) as db, pytest.raises(ConfigError, match="nowhere"):
        text_app(Core(config, db), FixedIdentity())


async def test_slow_subscriber_is_dropped_and_sees_it() -> None:
    feed = Feed(limit=2)
    subscription = feed.subscribe()
    for _ in range(3):
        feed.publish(object())  # type: ignore[arg-type]
    assert subscription.overflowed
    assert feed._subscribers == []
    await subscription.next()
    await subscription.next()
    with pytest.raises(OverflowError):
        await subscription.next()


async def test_slow_panel_is_closed(tmp_path: Path) -> None:
    async with serving(tmp_path) as (core, identity, url):
        identity.next = DeviceId("nPhone")
        async with connect(url) as ws:
            assert (await received(ws))["type"] == "live"
            event = core.recorder.emit(EventKind.TURN_STARTED, "test", {}, session="s1")
            assert (await received(ws))["type"] == "event"
            # Panel okuyamadan kuyruk taşar: elindekileri alır, sonra bağlantı kapanır.
            for _ in range(1001):
                core.feed.publish(event)
            count = 0
            with pytest.raises(ConnectionClosed) as closed:
                while True:
                    await asyncio.wait_for(ws.recv(), 2)
                    count += 1
            assert count == 1000
            assert closed.value.rcvd is not None and closed.value.rcvd.code == 1011
