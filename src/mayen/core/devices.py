"""Oturumların cihazlarına giden komut yolu (§9.7).

Komut istemcinin açık bağlantısından gider ve sonucu aynı bağlantıdan, aynı `id` ile döner.
Bekleme süresini tool'un zaman aşımı sınırlar (§9.1); bağlantı koparsa bekleyen komutlar
beklemeden `timeout` alır, tur takılı kalmaz.
"""

import asyncio
import itertools
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from mayen.ports.devices import Capabilities, Capability, Command, CommandResult, decode_client
from mayen.ports.tools import Status, ToolResult

log = logging.getLogger(__name__)


class DeviceLink:
    """Bir oturumun istemcisi. Yetenekleri beyan gelene kadar boştur (§9.7)."""

    def __init__(self) -> None:
        self._send: Callable[[str], Awaitable[None]] | None = None
        self._capabilities: frozenset[Capability] = frozenset()
        self._pending: dict[str, asyncio.Future[ToolResult]] = {}
        self._ids = itertools.count(1)

    def attach(self, send: Callable[[str], Awaitable[None]]) -> None:
        """Bağlantının yazma yolu; taşıma kurulunca verilir."""
        self._send = send

    @property
    def capabilities(self) -> frozenset[Capability]:
        return self._capabilities

    def receive(self, raw: str | bytes) -> None:
        """İstemcinin metin mesajı. Bozuk ya da beklenmeyen mesaj bağlantıyı kapatmaz (§13)."""
        try:
            message = decode_client(raw)
        except ValueError as e:
            log.warning("dropped a client message: %s", e)
            return
        if isinstance(message, Capabilities):
            self._capabilities = message.names
            return
        self._resolve(message)

    def _resolve(self, message: CommandResult) -> None:
        future = self._pending.pop(message.id, None)
        if future is None:
            # Zaman aşımından sonra gelen sonuç: tool sonucu çoktan modele döndü.
            log.warning("result for unknown or expired command %s", message.id)
            return
        if not future.done():
            future.set_result(message.result())

    async def run(
        self, capability: Capability, action: str, args: Mapping[str, Any]
    ) -> ToolResult:
        if capability not in self._capabilities or self._send is None:
            return ToolResult(
                Status.UNSUPPORTED, error=f"this device has no {capability.value} capability"
            )
        command = Command(f"c-{next(self._ids)}", capability, action, args)
        future: asyncio.Future[ToolResult] = asyncio.get_running_loop().create_future()
        self._pending[command.id] = future
        try:
            await self._send(command.encode())
            return await future
        finally:
            # Zaman aşımında tool'un gövdesi iptal edilir (§9.1); bekleyen kayıt da düşer.
            self._pending.pop(command.id, None)

    def close(self) -> None:
        """Bağlantı koptu: bekleyen her komut `timeout` alır."""
        self._send = None
        self._capabilities = frozenset()
        for future in self._pending.values():
            if not future.done():
                future.set_result(ToolResult(Status.TIMEOUT, error="the device disconnected"))
        self._pending.clear()


class Devices:
    """Oturum → cihaz bağlantısı. Bağlantısı olmayan oturumun (yazılı kanal) yeteneği yoktur."""

    def __init__(self) -> None:
        self._links: dict[str, DeviceLink] = {}

    def attach(self, session: str, link: DeviceLink) -> None:
        self._links[session] = link

    def get(self, session: str) -> DeviceLink:
        link = self._links.get(session)
        return NO_DEVICE if link is None else link

    def capabilities(self, session: str) -> frozenset[Capability]:
        return self.get(session).capabilities

    def detach(self, session: str) -> None:
        link = self._links.pop(session, None)
        if link is not None:
            link.close()


# Hiç yeteneği olmayan, hiçbir şey göndermeyen bağlantı.
NO_DEVICE = DeviceLink()
