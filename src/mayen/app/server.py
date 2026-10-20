"""Çekirdeğin sunucusu (§7, §13, §14): yazılı ve sesli kanal, panelin ucu.

Yazılı kanalda her bağlantı kendi oturumunu alır (§5.2).

Taşıma çerçevenin çok istemcili WebSocket taşımasıdır. Bağlanan cihazın kimliği taşımadan
okunur (§10.1); istemci kimliğini beyan etmez. Sesli istemcinin bildirdiği yetenekler
kimlik değildir (§9.7).
"""

import asyncio
import ipaddress
import logging
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket
from pipecat.frames.frames import OutputTransportMessageUrgentFrame
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.workers.runner import WorkerRunner

from mayen.app.panel import add_panel
from mayen.app.screen import Screen
from mayen.app.wiring import Core, Session, Voice, text_session, voice_session
from mayen.core.devices import DeviceLink
from mayen.pipeline.text import WireSerializer
from mayen.pipeline.voice import VoiceSerializer
from mayen.ports.channels import AudioInput, DeviceIdentity, VoiceHello
from mayen.ports.people import LOCAL_DEVICE, DeviceId

TEXT_PATH = "/text"
VOICE_PATH = "/voice"

# Sesli kanalın biçimi: girişte VAD ve STT'nin hızı, çıkışta TTS servisinin hızı. İkisi de
# istemciye selamla bildirilir; çekirdek başka hızı kabul etmez, istemci kendisi çevirir.
VOICE_INPUT_RATE = 16_000
VOICE_OUTPUT_RATE = 24_000

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


def core_app(core: Core, identity: DeviceIdentity) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Hatırlatmalar sunucuyla birlikte yaşar; hedefi bağlı oturumlardan seçilir (§12).
        timers = asyncio.create_task(core.timer_trigger.run())
        try:
            yield
        finally:
            timers.cancel()

    app = FastAPI(lifespan=lifespan)
    add_panel(app, core, identity)

    async def serve(
        websocket: WebSocket,
        kind: str,
        params: FastAPIWebsocketParams,
        build: Callable[[str, FastAPIWebsocketTransport, DeviceId | None], Session],
        hello: str | None = None,
        alongside: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        if "origin" in websocket.headers:
            # Tarayıcı her isteğe Origin ekler; sahibin tarayıcısında açık herhangi bir sayfa
            # onun cihazından bağlanıp onun yetkisiyle konuşabilirdi. Henüz web istemcisi yok.
            await websocket.close(code=1008)
            return
        await websocket.accept()
        if hello is not None:
            await websocket.send_text(hello)
        client = websocket.client
        device = None if client is None else await identity.device(client.host)
        session = f"{kind}-{uuid.uuid4()}"
        transport = FastAPIWebsocketTransport(websocket, params)
        built = build(session, transport, device)

        async def gone(_: FastAPIWebsocketTransport, __: WebSocket) -> None:
            await built.worker.cancel()

        transport.add_event_handler("on_client_disconnected", gone)

        log.info("%s session %s from device %s", kind, session, device or "unverified")
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(built.worker)
        # Oturumla birlikte yaşayan iş (sesli kanalda ekran yayını); oturum bitince kesilir.
        beside = None if alongside is None else asyncio.create_task(alongside())
        try:
            await runner.run()
        finally:
            if beside is not None:
                beside.cancel()
            await core.disconnect(session)

    @app.websocket(TEXT_PATH)
    async def text(websocket: WebSocket) -> None:
        params = FastAPIWebsocketParams(
            serializer=WireSerializer(),
            audio_in_enabled=False,
            audio_out_enabled=False,
            allowed_origins=[],
        )

        def build(
            session: str, transport: FastAPIWebsocketTransport, device: DeviceId | None
        ) -> Session:
            return text_session(core, session, transport, device)

        await serve(websocket, "text", params, build)

    if core.config.stt is not None and core.config.tts is not None:

        @app.websocket(VOICE_PATH)
        async def voice(websocket: WebSocket) -> None:
            # Cihaz komutları ve ekran mesajları sesle aynı bağlantıdan gider (§9.7, §7).
            link = DeviceLink()
            screens: list[Screen] = []  # oturum kurulunca tek ekran
            microphone: AudioInput | None = None  # istemcinin son bildirdiği

            def receive(raw: str) -> None:
                nonlocal microphone
                try:
                    heard = AudioInput.decode(raw)
                except ValueError as e:
                    log.warning("dropped a client message: %s", e)
                    return
                if heard is None:
                    link.receive(raw)
                    return
                log.info("audio input: %s", heard.source)
                microphone = heard

            params = FastAPIWebsocketParams(
                serializer=VoiceSerializer(VOICE_INPUT_RATE, receive),
                audio_in_enabled=True,
                audio_in_sample_rate=VOICE_INPUT_RATE,
                audio_out_enabled=True,
                audio_out_sample_rate=VOICE_OUTPUT_RATE,
                allowed_origins=[],
            )

            def build(
                session: str, transport: FastAPIWebsocketTransport, device: DeviceId | None
            ) -> Session:
                output = transport.output()

                async def send(message: str) -> None:
                    await output.send_message(
                        OutputTransportMessageUrgentFrame(message=message)
                    )

                link.attach(send)
                core.attach_device(session, link)
                screens.append(
                    Screen(
                        session,
                        send,
                        lambda: core.presence.personal(session) is not None,
                        core.timers,
                    )
                )
                stt, tts, vad, turn = core.speech(lambda: microphone)
                # Konuşmacı tanıma config'te yoksa söz cihazın kişisinindir.
                parts = Voice(
                    transport.input(),
                    stt,
                    tts,
                    transport.output(),
                    vad,
                    turn,
                    core.recognizer(),
                    device,
                    core.wake(),
                    core.turn_recognizer(),
                )
                return voice_session(core, session, parts, screens[0].tool)

            async def follow() -> None:
                await screens[0].follow(core.feed)

            hello = VoiceHello(VOICE_INPUT_RATE, VOICE_OUTPUT_RATE).encode()
            await serve(websocket, "voice", params, build, hello, follow)

    return app
