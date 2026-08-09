"""§5 geçiş tablosu testleri."""

import pytest

from mayen.session.state import (
    TRANSITIONS,
    Event,
    InvalidTransitionError,
    State,
    is_closed,
    transition,
)


def test_segment_goes_straight_to_resolving() -> None:
    # Sunucuda DİNLİYOR yok (§5): tamamlanmış segment doğrudan ÇÖZÜMLÜYOR'a götürür.
    assert transition(State.IDLE, Event.SEGMENT_ALINDI) is State.COZUMLUYOR


def test_happy_path_reaches_idle_again() -> None:
    state = State.IDLE
    for event in (
        Event.SEGMENT_ALINDI,
        Event.COZUMLEME_BITTI,
        Event.ILK_SES_HAZIR,
        Event.SES_BITTI,
    ):
        state = transition(state, event)
    assert state is State.IDLE


def test_barge_in_while_speaking_cancels_turn() -> None:
    assert transition(State.KONUSUYOR, Event.SOZ_KESILDI) is State.IDLE


def test_barge_in_while_reading_approval_keeps_state() -> None:
    # B3: ses durur, durum değişmez, plan yaşar.
    assert transition(State.ONAY_BEKLIYOR, Event.SOZ_KESILDI) is State.ONAY_BEKLIYOR


def test_approval_and_rejection_both_resume_the_agent() -> None:
    assert transition(State.ONAY_BEKLIYOR, Event.ONAY_VERILDI) is State.DUSUNUYOR
    assert transition(State.ONAY_BEKLIYOR, Event.ONAY_REDDEDILDI) is State.DUSUNUYOR


def test_approval_timeout_drops_the_plan() -> None:
    assert transition(State.ONAY_BEKLIYOR, Event.ONAY_ZAMAN_ASIMI) is State.IDLE


def test_recording_returns_to_thinking() -> None:
    assert transition(State.KAYIT, Event.KAYIT_BITTI) is State.DUSUNUYOR


def test_undefined_pair_raises() -> None:
    # Sessizce aynı durumda kalmak Kural 13 ihlali olurdu.
    with pytest.raises(InvalidTransitionError):
        transition(State.IDLE, Event.SES_BITTI)


def test_closed_states_are_exactly_approval_and_recording() -> None:
    closed = {state for state in State if is_closed(state)}
    assert closed == {State.ONAY_BEKLIYOR, State.KAYIT}


def test_every_state_is_reachable_from_idle() -> None:
    # Ulaşılamayan bir durum ya tabloda eksik bir satır ya da ölü bir durumdur.
    reachable = {State.IDLE}
    frontier = [State.IDLE]
    while frontier:
        current = frontier.pop()
        for (source, _event), target in TRANSITIONS.items():
            if source is current and target not in reachable:
                reachable.add(target)
                frontier.append(target)
    assert reachable == set(State)


def test_identifiers_carry_no_turkish_diacritics() -> None:
    # Semboller aksansız; aksan yalnızca değerde (adlandırma kuralı).
    for member in (*State, *Event):
        assert member.name.isascii()
