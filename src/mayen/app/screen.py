"""Sesli oturumun ekran yayını (§7): istemciye oturumun durumu, sözleri ve tool sonuçları.

Durum ve sözler kaydın canlı yayınından, yalnızca bu oturumunkiler alınır; sözlerden yalnızca
bir turun içindekiler. Tool sonucu
olaydan alınmaz: olaydaki sonuç yetki süzgecinden öncedir (§5.5); ekrana modele giden hâli
gider. Ortak cihazda `PERSONAL` bir tool'un sonucu ekrana gitmez: önünde kimin olduğu
bilinmez.
"""

import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from mayen.core.feed import Feed
from mayen.ports.events import Event, EventKind, SessionState, ref
from mayen.ports.screen import encode_reminder, encode_state, encode_tool, encode_utterance
from mayen.ports.timers import TimerStore
from mayen.ports.tools import Sensitivity, ToolResult, ToolSpec
from mayen.ports.transcript import Utterance
from mayen.ports.triggers import TriggerSource

type Send = Callable[[str], Awaitable[None]]

log = logging.getLogger(__name__)


class Screen:
    def __init__(
        self,
        session: str,
        send: Send,
        personal: Callable[[], bool],
        timers: TimerStore | None = None,
    ) -> None:
        self._session = session
        self._send = send
        self._personal = personal
        self._timers = timers  # çalan hatırlatmanın kaydı buradan okunur

    async def tool(
        self, spec: ToolSpec[Any], arguments: Mapping[str, Any], result: ToolResult
    ) -> None:
        if spec.sensitivity is Sensitivity.PERSONAL and not self._personal():
            return
        await self._show(encode_tool(spec.name, arguments, result))

    async def _show(self, message: str) -> None:
        """Ekran hatası turu bozmaz (§13): yazılır, mesaj düşer."""
        try:
            await self._send(message)
        except Exception as e:  # gönderim taşımanın içindedir, türü bilinmez
            log.warning("screen of %s: %s: %s", self._session, type(e).__name__, e)

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
                    await self._show(message)
        finally:
            subscription.close()

    def _message(self, item: Event | Utterance) -> str | None:
        if isinstance(item, Utterance):
            # Tur dışında duyulan söz kayda girer (§6, sürekli STT) ama Mayen'e söylenmemiştir.
            mine = item.session == self._session and item.turn_id is not None
            return encode_utterance(item) if mine else None
        header = item.header
        if header.session != self._session:
            return None
        if header.kind is EventKind.TURN_STARTED:
            return self._reminder(item)
        if header.kind is not EventKind.STATE_CHANGED:
            return None
        return encode_state(SessionState(item.body["state"]))

    def _reminder(self, started: Event) -> str | None:
        """Turu bir hatırlatma açtıysa onun kaydı; ortak cihazda `PERSONAL` olanı gitmez."""
        if self._timers is None or started.body.get("source") != TriggerSource.TIMER.value:
            return None
        prefix = ref("timer", "")
        for related in started.header.related:
            if not related.startswith(prefix):
                continue
            timer = self._timers.get(related.removeprefix(prefix))
            if timer is None:
                continue
            if timer.sensitivity is Sensitivity.PERSONAL and not self._personal():
                return None
            return encode_reminder(timer)
        return None
