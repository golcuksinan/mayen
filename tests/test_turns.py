"""Kesme ve kuyruk politikası (§5.2, §5.3)."""

import pytest

from mayen.core.turns import Interrupt, Start, TurnConfigError, Turns, interrupts, new_turn
from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import Fate, Priority, Trigger, TriggerSource

OWNER = Caller(Role.OWNER, "p1", has_personal_device=True)
GUEST = Caller(Role.ACQUAINTANCE, "p2", has_personal_device=True)
SYSTEM = Caller(Role.SYSTEM, "p1", has_personal_device=True)

CANCEL_ALL = dict.fromkeys(TriggerSource, Fate.CANCEL)


def trig(
    priority: Priority = Priority.NORMAL,
    source: TriggerSource = TriggerSource.TEXT,
    requester: Caller = OWNER,
    session: str = "s1",
    content: str = "",
) -> Trigger:
    return Trigger(session, priority, source, content, requester)


def started(actions: list[Interrupt | Start]) -> list[str]:
    return [a.turn.trigger.content for a in actions if isinstance(a, Start)]


# --- interrupts: §5.3'ün kesme kuralı ---


@pytest.mark.parametrize("incoming", list(Priority))
def test_equal_or_lower_priority_never_interrupts(incoming: Priority) -> None:
    current = new_turn(trig(Priority.URGENT if incoming is Priority.URGENT else incoming))
    assert not interrupts(current, incoming)
    if incoming is not Priority.URGENT:
        assert not interrupts(new_turn(trig(Priority.URGENT)), incoming)


@pytest.mark.parametrize(
    ("incoming", "cuts"),
    [(Priority.HIGH, False), (Priority.URGENT, True)],
)
def test_owner_speaking_is_cut_only_by_urgent(incoming: Priority, cuts: bool) -> None:
    current = new_turn(trig(Priority.LOW, TriggerSource.VOICE, OWNER))
    assert interrupts(current, incoming) is cuts


def test_someone_else_speaking_is_cut_by_any_higher_priority() -> None:
    current = new_turn(trig(Priority.LOW, TriggerSource.VOICE, GUEST))
    assert interrupts(current, Priority.NORMAL)


def test_owner_written_turn_is_not_protected_like_speech() -> None:
    # Kural ses turu içindir; yazılı tur genel öncelik kuralına uyar.
    current = new_turn(trig(Priority.NORMAL, TriggerSource.TEXT, OWNER))
    assert interrupts(current, Priority.HIGH)


# --- Turns: config ---


def test_missing_fate_is_a_config_error() -> None:
    fates = dict(CANCEL_ALL)
    del fates[TriggerSource.EVENT]
    with pytest.raises(TurnConfigError, match="event"):
        Turns(fates)


def test_resume_is_a_config_error() -> None:
    # Çerçevenin karşılamadığı akıbet açılışta hata verir (§5.3).
    with pytest.raises(TurnConfigError, match="voice"):
        Turns({**CANCEL_ALL, TriggerSource.VOICE: Fate.RESUME})


def test_max_running_must_be_positive() -> None:
    with pytest.raises(TurnConfigError):
        Turns(CANCEL_ALL, max_running=0)


# --- Turns: kuyruk ---


def test_first_trigger_starts_and_the_next_waits() -> None:
    turns = Turns(CANCEL_ALL)
    assert started(turns.submit(trig(content="a"))) == ["a"]
    assert turns.submit(trig(content="b")) == []
    assert [t.trigger.content for t in turns.waiting("s1")] == ["b"]


def test_waiting_starts_by_priority_then_arrival() -> None:
    turns = Turns(CANCEL_ALL)
    first = turns.submit(trig(Priority.URGENT, content="running"))[0].turn
    for p, c in [(Priority.LOW, "low"), (Priority.HIGH, "h1"), (Priority.HIGH, "h2")]:
        turns.submit(trig(p, content=c))
    order = []
    turn = first
    while True:
        actions = turns.finished(turn.id)
        if not actions:
            break
        turn = actions[0].turn
        order.append(turn.trigger.content)
    assert order == ["h1", "h2", "low"]


def test_cancel_scope_is_the_turn_not_the_queue() -> None:
    # Bir turu kesmek kuyrukta bekleyen hatırlatmayı çöpe atmaz (§5.3).
    turns = Turns(CANCEL_ALL)
    running = turns.submit(trig(Priority.LOW, content="chat"))[0].turn
    turns.submit(trig(Priority.LOW, TriggerSource.TIMER, SYSTEM, content="reminder"))
    actions = turns.submit(trig(Priority.URGENT, content="stop"))
    assert actions[0] == Interrupt(running, Fate.CANCEL)
    assert started(actions) == ["stop"]
    assert [t.trigger.content for t in turns.waiting("s1")] == ["reminder"]


def test_fate_comes_from_the_interrupted_turns_source() -> None:
    turns = Turns({**CANCEL_ALL, TriggerSource.TIMER: Fate.RESTART})
    turns.submit(trig(Priority.LOW, TriggerSource.TIMER, SYSTEM, content="reminder"))
    actions = turns.submit(trig(Priority.HIGH, TriggerSource.TEXT, content="question"))
    assert isinstance(actions[0], Interrupt)
    assert actions[0].fate is Fate.RESTART


def test_restarted_turn_goes_first_in_its_priority_with_a_new_id() -> None:
    turns = Turns({**CANCEL_ALL, TriggerSource.TIMER: Fate.RESTART})
    old = turns.submit(trig(Priority.LOW, TriggerSource.TIMER, SYSTEM, content="reminder"))
    turns.submit(trig(Priority.LOW, content="waiting"))
    interrupting = turns.submit(trig(Priority.HIGH, content="question"))[1].turn
    assert [t.trigger.content for t in turns.waiting("s1")] == ["reminder", "waiting"]
    restarted = turns.finished(interrupting.id)[0].turn
    assert restarted.trigger.content == "reminder"
    # Eski koşunun geç gelen parçaları yeni koşuya karışmasın (§5.3).
    assert restarted.id != old[0].turn.id


def test_queued_trigger_does_not_interrupt() -> None:
    turns = Turns(CANCEL_ALL)
    turns.submit(trig(Priority.LOW, TriggerSource.VOICE, OWNER, content="talk"))
    assert turns.submit(trig(Priority.HIGH, TriggerSource.TIMER, SYSTEM)) == []


# --- Turns: oturumlar ve eşzamanlılık (§5.2) ---


def test_sessions_are_isolated() -> None:
    turns = Turns(CANCEL_ALL, max_running=2)
    a = turns.submit(trig(Priority.LOW, session="s1", content="a"))
    b = turns.submit(trig(Priority.URGENT, session="s2", content="b"))
    assert started(a) == ["a"]
    assert started(b) == ["b"]  # başka oturumun turunu kesmez
    assert turns.running("s1") == a[0].turn


def test_running_limit_spans_sessions() -> None:
    turns = Turns(CANCEL_ALL)
    first = turns.submit(trig(session="s1", content="a"))[0].turn
    assert turns.submit(trig(session="s2", content="b")) == []
    assert started(turns.finished(first.id)) == ["b"]


def test_waiting_turn_of_a_busy_session_does_not_block_another_session() -> None:
    turns = Turns(CANCEL_ALL, max_running=2)
    turns.submit(trig(session="s1", content="a"))
    turns.submit(trig(Priority.URGENT, TriggerSource.VOICE, session="s1", content="a2"))
    assert started(turns.submit(trig(Priority.LOW, session="s2", content="b"))) == ["b"]


# --- Turns: ses (§5.3, sesli tetikleyici sıraya alınmaz) ---


def test_speech_is_heard_in_an_idle_session() -> None:
    assert Turns(CANCEL_ALL).hears("s1", Priority.NORMAL)


def test_speech_is_not_heard_over_a_higher_priority_turn() -> None:
    turns = Turns(CANCEL_ALL)
    turns.submit(trig(Priority.URGENT, TriggerSource.TIMER, SYSTEM))
    assert not turns.hears("s1", Priority.NORMAL)


def test_speech_is_heard_over_a_lower_priority_turn() -> None:
    turns = Turns(CANCEL_ALL)
    turns.submit(trig(Priority.LOW, TriggerSource.TIMER, SYSTEM))
    assert turns.hears("s1", Priority.NORMAL)


def test_speech_inside_a_voice_turn_is_the_conversation() -> None:
    turns = Turns(CANCEL_ALL)
    turns.submit(trig(Priority.NORMAL, TriggerSource.VOICE, OWNER))
    assert turns.hears("s1", Priority.NORMAL)


def test_speech_is_not_heard_when_no_turn_slot_is_free() -> None:
    turns = Turns(CANCEL_ALL)
    turns.submit(trig(session="s2"))
    assert not turns.hears("s1", Priority.URGENT)


def test_identified_owner_is_protected_from_high_priority() -> None:
    turns = Turns(CANCEL_ALL)
    unknown = Caller(Role.UNKNOWN, None, has_personal_device=False)
    turns.submit(trig(Priority.NORMAL, TriggerSource.VOICE, unknown))
    turns.identify("s1", OWNER)
    assert turns.submit(trig(Priority.HIGH, TriggerSource.TIMER, SYSTEM)) == []


def test_dropped_session_takes_its_turns_and_frees_the_slot() -> None:
    turns = Turns(CANCEL_ALL)
    turns.submit(trig(session="s1", content="a"))
    turns.submit(trig(session="s1", content="b"))
    turns.submit(trig(session="s2", content="c"))
    assert started(turns.drop("s1")) == ["c"]
    assert turns.running("s1") is None and turns.waiting("s1") == []
