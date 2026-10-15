"""Oturumun durumu (§5.4): parçaların bildirdiğinden tek değer, değişince bir kez."""

import pytest

from mayen.core.state import StateTracker, state_of
from mayen.ports.events import SessionState
from mayen.ports.triggers import TriggerSource

S = SessionState


@pytest.mark.parametrize(
    ("turn", "awaiting", "listening", "speaking", "expected"),
    [
        (None, False, False, False, S.IDLE),
        (None, False, True, False, S.IDLE),  # duyulmayan söz tur açmadı
        (TriggerSource.VOICE, False, True, False, S.LISTENING),
        (TriggerSource.TEXT, False, True, False, S.THINKING),  # yazı dinlemeden geçmez
        (TriggerSource.TEXT, False, False, False, S.THINKING),
        (TriggerSource.TIMER, False, False, True, S.SPEAKING),
        # Soru okunurken ve söze girilince de onay beklenir.
        (TriggerSource.VOICE, True, False, True, S.AWAITING_CONFIRMATION),
        (TriggerSource.VOICE, True, True, False, S.AWAITING_CONFIRMATION),
    ],
)
def test_state_of(
    turn: TriggerSource | None,
    awaiting: bool,
    listening: bool,
    speaking: bool,
    expected: SessionState,
) -> None:
    assert state_of(turn, awaiting=awaiting, listening=listening, speaking=speaking) is expected


def test_tracker_reports_only_changes() -> None:
    seen: list[tuple[SessionState, SessionState]] = []
    tracker = StateTracker(lambda previous, current: seen.append((previous, current)))
    tracker.listening(True)  # tur yok: değişmez
    tracker.turn(TriggerSource.TEXT)
    tracker.speaking(True)
    tracker.speaking(True)
    tracker.awaiting(True)
    tracker.speaking(False)  # onay beklerken: değişmez
    tracker.awaiting(False)
    tracker.turn(None)
    assert seen == [
        (S.IDLE, S.THINKING),
        (S.THINKING, S.SPEAKING),
        (S.SPEAKING, S.AWAITING_CONFIRMATION),
        (S.AWAITING_CONFIRMATION, S.THINKING),
        (S.THINKING, S.IDLE),
    ]
    assert tracker.state is S.IDLE
