"""Yazılı kanalın sunucusu (§7, §13): her bağlantı kendi oturumunu alır (§5.2).

Taşıma çerçevenin çok istemcili WebSocket taşımasıdır. Bağlanan cihazın kimliği taşımadan
okunur (§10.1); istemci kendisi hakkında hiçbir şey beyan etmez.
"""

import asyncio
import ipaddress
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.workers.runner import WorkerRunner

from mayen.app.wiring import Core, text_session
from mayen.pipeline.text import WireSerializer
from mayen.ports.channels import DeviceIdentity
from mayen.ports.people import LOCAL_DEVICE, DeviceId

TEXT_PATH = "/text"

log = logging.getLogger(__name__)


class LoopbackIsLocal:
    """Bu makineden gelen bağlantı, bu makinenin cihazıdır (`LOCAL_DEVICE`); gerisi `inner`.

    Geliştirme istisnasıdır (sahip, 17. ve 19. oturum): mimaride bu makine ortak cihazdır
    (§10.1). Tailnet'ten bağlanan kişisel bir istemci olunca kalkar.
    """

    def __init__(self, inner: DeviceIdentity) -> None:
        self._inner = inner

    async def device(self, address: str) -> DeviceId | None:
        try:
            if ipaddress.ip_address(address).is_loopback:
                return LOCAL_DEVICE
        except ValueError:
            pass  # adres değil (örneğin bir soket yolu); doğrulamayı içteki yapar
        return await self._inner.device(address)


def text_app(core: Core, identity: DeviceIdentity) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Hatırlatmalar sunucuyla birlikte yaşar; hedefi bağlı oturumlardan seçilir (§12).
        timers = asyncio.create_task(core.timer_trigger.run())
        try:
            yield
        finally:
            timers.cancel()

    app = FastAPI(lifespan=lifespan)

    @app.websocket(TEXT_PATH)
    async def text(websocket: WebSocket) -> None:
        if "origin" in websocket.headers:
            # Tarayıcı her isteğe Origin ekler; sahibin tarayıcısında açık herhangi bir sayfa
            # onun cihazından bağlanıp onun yetkisiyle yazabilirdi. Henüz web istemcisi yok.
            await websocket.close(code=1008)
            return
        await websocket.accept()
        client = websocket.client
        device = None if client is None else await identity.device(client.host)
        session = f"text-{uuid.uuid4()}"
        transport = FastAPIWebsocketTransport(
            websocket,
            FastAPIWebsocketParams(
                serializer=WireSerializer(),
                audio_in_enabled=False,
                audio_out_enabled=False,
                allowed_origins=[],
            ),
        )
        built = text_session(core, session, transport, device)

        async def gone(_: FastAPIWebsocketTransport, __: WebSocket) -> None:
            await built.worker.cancel()

        transport.add_event_handler("on_client_disconnected", gone)

        log.info("text session %s from device %s", session, device or "unverified")
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(built.worker)
        try:
            await runner.run()
        finally:
            await core.disconnect(session)

    return app
