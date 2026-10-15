"""Panelin ucu (§14): olay kaydı ve transkript, önce geçmiş sonra canlı.

Panel herkesin konuşmasını gösterir; bu yüzden yalnızca sahibin cihazından açılır. Cihaz
taşımadan okunur (§10.1). Tarayıcıda açık herhangi bir sayfa da sahibin cihazından
bağlanabileceği için tarayıcının Origin başlığı config'teki adreslerden biri olmalıdır.
Sözleşme `ports.panel`'dadır.
"""

import asyncio
import logging
from collections.abc import Sequence

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from mayen.app.config import ConfigError
from mayen.app.wiring import Core
from mayen.core.feed import Item, Subscription
from mayen.ports.channels import DeviceIdentity
from mayen.ports.events import Event, parse_stamp
from mayen.ports.panel import encode_event, encode_live, encode_utterance
from mayen.ports.tools import Role

EVENTS_PATH = "/events"
PANEL_PATH = "/panel"

# Reddin kodu: ilke ihlali (RFC 6455 §7.4.1). Kabulden önce kapatmak HTTP 403 olarak döner.
POLICY = 1008
TOO_SLOW = 1011

log = logging.getLogger(__name__)


def _encode(item: Item) -> str:
    return encode_event(item) if isinstance(item, Event) else encode_utterance(item)


def _id(item: Item) -> str:
    return str(item.header.id) if isinstance(item, Event) else str(item.id)


def _time(item: Item) -> str:
    moment = item.header.time if isinstance(item, Event) else item.time
    return moment.isoformat()


def add_panel(app: FastAPI, core: Core, identity: DeviceIdentity) -> None:
    panel = core.config.panel
    if panel.dist is not None:
        if not panel.dist.is_dir():
            # Verilip bulunmayan panel sessizce atlanırsa sahip boş bir sayfa görür.
            raise ConfigError(f"panel.dist: no such directory: {panel.dist}")
        app.mount(PANEL_PATH, StaticFiles(directory=panel.dist, html=True), name="panel")

    @app.websocket(EVENTS_PATH)
    async def events(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin is not None and origin not in panel.origins:
            await websocket.close(code=POLICY)
            return
        client = websocket.client
        device = None if client is None else await identity.device(client.host)
        person = None if device is None else core.people.by_device(device)
        if person is None or person.role is not Role.OWNER:
            log.warning("panel refused: device %s is not the owner's", device or "unverified")
            await websocket.close(code=POLICY)
            return
        raw = websocket.query_params.get("since")
        try:
            since = None if raw is None else parse_stamp(raw)
        except ValueError:
            await websocket.close(code=POLICY)
            return
        await websocket.accept()
        # Abonelik geçmişten önce: arada kayda girenler kaçmaz, iki kez gelenler atlanır.
        subscription = core.feed.subscribe()
        try:
            history: Sequence[Item] = ()
            if since is not None:
                history = sorted(
                    [*core.events.read(since=since), *core.utterances.read(since=since)],
                    key=_time,
                )
            sent = {_id(item) for item in history}
            for item in history:
                await websocket.send_text(_encode(item))
            await websocket.send_text(encode_live())
            await _stream(websocket, subscription, sent)
        except OverflowError:
            log.warning("panel fell behind the feed; closing")
            await websocket.close(code=TOO_SLOW)
        except WebSocketDisconnect:
            pass
        finally:
            subscription.close()


async def _stream(websocket: WebSocket, subscription: Subscription, sent: set[str]) -> None:
    """Canlı kayıtları panel kopana kadar gönderir. Panel mesaj göndermez; gelen her şey
    yalnızca bağlantının durumunu gösterir."""
    receiving = asyncio.ensure_future(websocket.receive())
    try:
        while True:
            item_task = asyncio.ensure_future(subscription.next())
            done, _ = await asyncio.wait(
                {receiving, item_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if item_task in done:
                item = item_task.result()
                if _id(item) not in sent:
                    await websocket.send_text(_encode(item))
            else:
                item_task.cancel()  # kuyruğun beklemesi iptal edilince kayıt kaybolmaz
            if receiving in done:
                if receiving.result()["type"] == "websocket.disconnect":
                    return
                receiving = asyncio.ensure_future(websocket.receive())
    finally:
        receiving.cancel()
