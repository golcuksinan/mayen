"""Sesli oturumun ekran yayını (§7): istemciye oturumun durumu, sözleri ve tool sonuçları.

Durum ve sözler kaydın canlı yayınından, yalnızca bu oturumunkiler alınır. Tool sonucu
olaydan alınmaz: olaydaki sonuç yetki süzgecinden öncedir (§5.5); ekrana modele giden hâli
gider. Ortak cihazda `PERSONAL` bir tool'un sonucu ekrana gitmez: önünde kimin olduğu
bilinmez.
"""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from mayen.core.feed import Feed
from mayen.ports.events import Event, EventKind, SessionState
from mayen.ports.screen import encode_state, encode_tool, encode_utterance
from mayen.ports.tools import Sensitivity, ToolResult, ToolSpec
from mayen.ports.transcript import Utterance

type Send = Callable[[str], Awaitable[None]]

log = logging.getLogger(__name__)


class Screen:
    def __init__(self, session: str, send: Send, personal: Callable[[], bool]) -> None:
        self._session = session
        self._send = send
        self._personal = personal

    async def tool(
        self, spec: ToolSpec[Any], arguments: Mapping[str, Any], result: ToolResult
    ) -> None:
        if spec.sensitivity is Sensitivity.PERSONAL and not self._personal():
            return
        await self._send(encode_tool(spec.name, arguments, result))

    async def follow(self, feed: Feed) -> None:
        """Bağlantı kapanana kadar sürer. Geride kalan istemci kaydı bekletmez: aboneliği
        yenilenir, kaçırdıkları ekrandan eksik kalır ve bu loga yazılır."""
        subscription = feed.subscribe()
        try:
            while True:
                try:
                    item = await subscription.next()
                except OverflowError:
                    log.warning("screen of %s fell behind the feed", self._session)
                    subscription = feed.subscribe()
                    continue
                message = self._message(item)
                if message is not None:
                    await self._send(message)
        finally:
            subscription.close()

    def _message(self, item: Event | Utterance) -> str | None:
        if isinstance(item, Utterance):
            return encode_utterance(item) if item.session == self._session else None
        header = item.header
        if header.session != self._session or header.kind is not EventKind.STATE_CHANGED:
            return None
        return encode_state(SessionState(item.body["state"]))
