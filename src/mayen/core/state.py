"""Oturumun durumu (§5.4): hattın parçalarının bildirdiklerinden tek bir değer.

Durumu istemci ve panel olay sırasından kendisi çıkarmaz; çekirdek yayınlar. Aynı çıkarımı
her istemci ayrıca yazsaydı istemciler zamanla ayrışırdı.
"""

from collections.abc import Callable

from mayen.ports.events import SessionState
from mayen.ports.triggers import TriggerSource


def state_of(
    turn: TriggerSource | None, *, awaiting: bool, listening: bool, speaking: bool
) -> SessionState:
    """Kapalı durum her şeyin önündedir: onay sorusu okunurken de, söze girilince de onay
    beklenir (§5.4). Yazılı tur dinlemeden geçmez."""
    if turn is None:
        return SessionState.IDLE
    if awaiting:
        return SessionState.AWAITING_CONFIRMATION
    if speaking:
        return SessionState.SPEAKING
    if listening and turn is TriggerSource.VOICE:
        return SessionState.LISTENING
    return SessionState.THINKING


class StateTracker:
    """Parçaların bildirdiği durumu tutar; değer değişince `changed`'i çağırır."""

    def __init__(self, changed: Callable[[SessionState, SessionState], None]) -> None:
        self._changed = changed
        self._turn: TriggerSource | None = None
        self._awaiting = False
        self._listening = False
        self._speaking = False
        self.state = SessionState.IDLE

    def turn(self, source: TriggerSource | None) -> None:
        self._turn = source
        self._update()

    def awaiting(self, value: bool) -> None:
        self._awaiting = value
        self._update()

    def listening(self, value: bool) -> None:
        self._listening = value
        self._update()

    def speaking(self, value: bool) -> None:
        self._speaking = value
        self._update()

    def _update(self) -> None:
        state = state_of(
            self._turn,
            awaiting=self._awaiting,
            listening=self._listening,
            speaking=self._speaking,
        )
        if state is not self.state:
            previous, self.state = self.state, state
            self._changed(previous, state)
