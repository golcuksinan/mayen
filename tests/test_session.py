"""Tetikleyici kapısı (§5.1–§5.3) Pipecat'in test hattında."""

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import pytest
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    DataFrame,
    Frame,
    FunctionCallFromLLM,
    FunctionCallResultFrame,
    FunctionCallsStartedFrame,
    InterruptionFrame,
    LLMMessagesAppendFrame,
    LLMRunFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.tests.utils import SleepFrame, run_test

from fakes import MemoryEventLog, MemoryTranscript, session_transcript
from mayen.core.events import Recorder, SystemClock
from mayen.core.state import StateTracker
from mayen.core.turns import Turns
from mayen.pipeline.session import (
    UNIDENTIFIED,
    HeardOnly,
    RequesterSource,
    Sessions,
    TriggerGate,
)
from mayen.ports.events import EventKind, SessionState
from mayen.ports.tools import Caller, Role, Status
from mayen.ports.triggers import Fate, Priority, Trigger, TriggerSource

OWNER = Caller(Role.OWNER, "p1", has_personal_device=True)
SYSTEM = Caller(Role.SYSTEM, "p1", has_personal_device=True)

SETTLE_S = 0.1
TIMEOUT_S = 0.3


@dataclass
class Call(DataFrame):
    """Test hattında bir adım; kapıdan önceki kareler işlendikten sonra çalışır."""

    fn: Callable[[], Awaitable[None] | None]


class Steps(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, Call):
            out = frame.fn()
            if out is not None:
                await out
            return
        await self.push_frame(frame, direction)


def make(
    fates: dict[TriggerSource, Fate] | None = None,
    holds: Sequence[Callable[[], bool]] = (),
    log: MemoryEventLog | None = None,
    store: MemoryTranscript | None = None,
    state: StateTracker | None = None,
    label: Callable[[Caller], str] | None = None,
    requester: RequesterSource | None = None,
) -> tuple[Sessions, TriggerGate]:
    turns = Turns(fates or dict.fromkeys(TriggerSource, Fate.CANCEL))
    sessions = Sessions(turns, Priority.NORMAL)
    heard, memory = session_transcript(sessions)
    if store is not None:
        memory.utterances = store.utterances
    gate = TriggerGate(
        "s1",
        sessions,
        lambda _: OWNER,
        Recorder(log or MemoryEventLog(), SystemClock()),
        heard,
        settle_s=SETTLE_S,
        response_timeout_s=TIMEOUT_S,
        holds=holds,
        state=state,
        label=label,
        requester=requester,
    )
    return sessions, gate


def trig(
    priority: Priority, source: TriggerSource = TriggerSource.TIMER, content: str = "x"
) -> Trigger:
    return Trigger(
        "s1", priority, source, content, OWNER if source is TriggerSource.TEXT else SYSTEM
    )


async def run(gate: TriggerGate, frames: Sequence[Frame]) -> tuple[list[Frame], list[Frame]]:
    down, up = await run_test(Pipeline([gate, Steps()]), frames_to_send=frames)
    return list(down), list(up)


def appended(frames: Sequence[Frame]) -> list[dict[str, str]]:
    return [m for f in frames if isinstance(f, LLMMessagesAppendFrame) for m in f.messages]  # type: ignore[misc]


def interruptions(frames: Sequence[Frame]) -> int:
    return sum(isinstance(f, InterruptionFrame) for f in frames)


async def test_text_trigger_goes_to_the_model_as_the_users_message() -> None:
    sessions, gate = make()
    down, _ = await run(
        gate,
        [Call(lambda: sessions.submit(trig(Priority.NORMAL, TriggerSource.TEXT, "selam")))],
    )
    assert appended(down) == [{"role": "user", "content": "selam"}]
    assert next(f for f in down if isinstance(f, LLMMessagesAppendFrame)).run_llm


async def test_text_carries_the_name_of_who_wrote_it() -> None:
    sessions, gate = make(label=lambda requester: f"{requester.role.value}-adı")
    down, _ = await run(
        gate,
        [Call(lambda: sessions.submit(trig(Priority.NORMAL, TriggerSource.TEXT, "selam")))],
    )
    assert appended(down) == [{"role": "user", "content": "owner-adı: selam"}]


async def test_system_trigger_is_a_labelled_developer_message() -> None:
    sessions, gate = make()
    down, _ = await run(
        gate, [Call(lambda: sessions.submit(trig(Priority.HIGH, content="su iç")))]
    )
    [message] = appended(down)
    assert message["role"] == "developer"
    assert json.loads(message["content"]) == {
        "trigger": "timer",
        "priority": "high",
        "content": "su iç",
    }


async def test_trigger_details_go_to_the_model_as_data() -> None:
    sessions, gate = make()
    trigger = Trigger(
        "s1", Priority.NORMAL, TriggerSource.TIMER, "su iç", SYSTEM, {"due": "2026-10-13 15:00"}
    )
    down, _ = await run(gate, [Call(lambda: sessions.submit(trigger))])
    [message] = appended(down)
    assert json.loads(message["content"])["details"] == {"due": "2026-10-13 15:00"}
    assert sessions.names() == ["s1"]


async def test_waiting_trigger_starts_when_the_turn_goes_quiet() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="a"))),
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="b"))),
        Call(gate.response_started),
        SleepFrame(SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    # Model cevap yazarken tur sürer; ikinci tetikleyici beklemededir.
    assert [json.loads(m["content"])["content"] for m in appended(down)] == ["a"]

    sessions, gate = make()
    frames = [*frames, Call(gate.response_stopped), SleepFrame(SETTLE_S * 3)]
    down, _ = await run(gate, frames)
    assert [json.loads(m["content"])["content"] for m in appended(down)] == ["a", "b"]


async def test_turn_without_a_response_closes_after_the_timeout() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="a"))),
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="b"))),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    assert [json.loads(m["content"])["content"] for m in appended(down)] == ["a", "b"]


async def test_open_tool_call_and_holds_keep_the_turn_open() -> None:
    held = [True]
    sessions, gate = make(holds=[lambda: held[0]])
    call = FunctionCallFromLLM("note_add", "c1", {}, None)
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="a"))),
        Call(lambda: sessions.submit(trig(Priority.NORMAL, content="b"))),
        Call(gate.response_started),
        Call(gate.response_stopped),
        FunctionCallsStartedFrame(function_calls=[call]),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    assert len(appended(down)) == 1

    sessions, gate = make(holds=[lambda: held[0]])
    frames = [
        *frames,
        FunctionCallResultFrame("note_add", "c1", {}, None, None),
        SleepFrame(SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    assert len(appended(down)) == 1  # onay beklenirken de tur açıktır

    held[0] = False
    sessions, gate = make(holds=[lambda: held[0]])
    down, _ = await run(gate, frames)
    assert len(appended(down)) == 2


async def test_higher_priority_cuts_with_pipecats_interruption_and_a_note() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="chat"))),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
    ]
    down, up = await run(gate, frames)
    assert interruptions(down) == 1
    assert interruptions(up) == 1
    messages = appended(down)
    assert json.loads(messages[1]["content"]) == {"interrupted": "timer"}
    assert json.loads(messages[2]["content"])["content"] == "alarm"


async def test_restarted_trigger_is_delivered_again_without_a_note() -> None:
    sessions, gate = make(
        {**dict.fromkeys(TriggerSource, Fate.CANCEL), TriggerSource.TIMER: Fate.RESTART}
    )
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="reminder"))),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    down, _ = await run(gate, frames)
    contents = [json.loads(m["content"]).get("content") for m in appended(down)]
    assert contents == ["reminder", "alarm", "reminder"]


# --- ses ---


async def test_speech_opens_a_voice_turn_without_pushing_anything() -> None:
    _, gate = make()
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        TranscriptionFrame("selam", "u", "t"),
        UserStoppedSpeakingFrame(),
    ]
    seen: list[TriggerSource | None] = []

    def look() -> None:
        seen.append(gate.turn.trigger.source if gate.turn else None)

    down, _ = await run(gate, [*frames, Call(look)])
    assert seen == [TriggerSource.VOICE]
    assert appended(down) == []


async def test_identified_owner_is_cut_only_by_urgent() -> None:
    sessions, gate = make()
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        TranscriptionFrame("selam", "u", "t"),
        Call(lambda: sessions.submit(trig(Priority.HIGH, content="reminder"))),
    ]
    down, _ = await run(gate, frames)
    assert appended(down) == []


async def test_requester_is_found_from_all_words_until_mayen_answers() -> None:
    heard: list[list[str]] = []

    def requester(frames: Sequence[TranscriptionFrame]) -> Caller:
        heard.append([f.text for f in frames])
        return OWNER if len(frames) == 2 else UNIDENTIFIED

    log = MemoryEventLog()
    sessions, gate = make(requester=requester, log=log)
    seen: list[Caller | None] = []

    def look() -> None:
        turn = sessions.running("s1")
        seen.append(turn.trigger.requester if turn else None)

    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        TranscriptionFrame("Hey Mayen.", "u", "t"),
        Call(look),
        SleepFrame(0.05),
        TranscriptionFrame("dişçi notunu sil", "u", "t"),
        Call(look),
        SleepFrame(0.05),  # sistem karesi sıradaki sözlerin önüne geçmesin
        BotStartedSpeakingFrame(),
        TranscriptionFrame("evet", "u", "t"),  # cevaptan sonra: isteyen değişmez
        Call(look),
    ]
    end: list[Frame] = [UserStoppedSpeakingFrame(), BotStoppedSpeakingFrame()]
    await run(gate, [*frames, *end, SleepFrame(TIMEOUT_S + SETTLE_S * 3)])
    assert seen == [UNIDENTIFIED, OWNER, OWNER]
    # Tur açılırken isteyen bilinmez; turun sonunda kim sayıldığı bitiş olayındadır.
    [started] = [e for e in log.events if e.header.kind is EventKind.TURN_STARTED]
    [finished] = [e for e in log.events if e.header.kind is EventKind.TURN_FINISHED]
    assert started.body["requester"]["role"] == "unknown"
    assert finished.body["requester"] == {"role": "owner", "person_id": "p1"}
    assert heard == [["Hey Mayen."], ["Hey Mayen.", "dişçi notunu sil"]]


async def test_speech_over_a_lower_turn_is_not_cut_twice() -> None:
    # Söz başlayınca Pipecat zaten keser; kapı ikinci bir kesme yollamaz, akıbeti uygular.
    sessions, gate = make()
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="chat"))),
        SleepFrame(0.05),  # sistem karesi veri karesini geçmesin
        UserStartedSpeakingFrame(),
    ]
    down, up = await run(gate, frames)
    assert interruptions(down) == interruptions(up) == 0
    assert json.loads(appended(down)[1]["content"]) == {"interrupted": "timer"}


@pytest.mark.parametrize(
    ("priority", "muted"), [(Priority.URGENT, True), (Priority.LOW, False)]
)
async def test_user_is_muted_over_a_higher_priority_turn(
    priority: Priority, muted: bool
) -> None:
    sessions, gate = make()
    strategy = HeardOnly(gate)
    result: list[bool] = []

    async def check() -> None:
        result.append(await strategy.process_frame(UserStartedSpeakingFrame()))

    await run(gate, [Call(lambda: sessions.submit(trig(priority))), Call(check)])
    assert result == [muted]


async def test_restarted_voice_turn_runs_the_model_again() -> None:
    sessions, gate = make(
        {**dict.fromkeys(TriggerSource, Fate.CANCEL), TriggerSource.VOICE: Fate.RESTART}
    )
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
        UserStoppedSpeakingFrame(),
        SleepFrame(TIMEOUT_S * 2 + SETTLE_S * 6),
    ]
    down, _ = await run(gate, frames)
    assert any(isinstance(f, LLMRunFrame) for f in down)


async def test_turn_events_carry_session_turn_and_duration() -> None:
    log = MemoryEventLog()
    sessions, gate = make(log=log)
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.LOW, content="chat"))),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
        Call(gate.response_started),
        Call(gate.response_stopped),
        SleepFrame(SETTLE_S * 3),
    ]
    await run(gate, frames)

    assert log.kinds() == [
        EventKind.TURN_STARTED,
        EventKind.TURN_INTERRUPTED,
        EventKind.TURN_STARTED,
        EventKind.TURN_FINISHED,
    ]
    first, cut, second, done = (e.header for e in log.events)
    assert {h.session for h in (first, cut, second, done)} == {"s1"}
    assert cut.turn_id == first.turn_id != second.turn_id == done.turn_id
    system = {"role": "system", "person_id": "p1"}
    assert cut.status is Status.CANCELLED
    assert log.events[1].body == {"fate": "cancel", "requester": system}
    assert done.status is Status.OK and done.duration_s is not None
    assert done.duration_s >= SETTLE_S
    assert log.events[3].body == {"unanswered": False, "requester": system}


async def test_unanswered_turn_says_so_in_the_finish_event() -> None:
    log = MemoryEventLog()
    sessions, gate = make(log=log)
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL))),
        SleepFrame(TIMEOUT_S + SETTLE_S * 3),
    ]
    await run(gate, frames)
    [done] = log.of(EventKind.TURN_FINISHED)
    assert done.body == {"unanswered": True, "requester": {"role": "system", "person_id": "p1"}}


async def test_speech_answered_before_it_is_heard_to_end_expects_nothing() -> None:
    """Onay kapısının yuttuğu söz geç biter; cevap o arada geldiyse yeni cevap beklenmez."""
    log = MemoryEventLog()
    _, gate = make(log=log)
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        Call(gate.response_started),
        Call(gate.response_stopped),
        SleepFrame(0.05),  # adımlar kapıdan sonra çalışır; söz bitişi cevaptan sonra gelsin
        UserStoppedSpeakingFrame(),
        SleepFrame(SETTLE_S * 4),
    ]
    await run(gate, frames)
    [done] = log.of(EventKind.TURN_FINISHED)
    assert done.body["unanswered"] is False
    assert done.header.duration_s is not None and done.header.duration_s < TIMEOUT_S


async def test_turn_owner_is_reported_as_seen_and_detach_frees_the_session() -> None:
    seen: list[tuple[str, Caller]] = []
    turns = Turns(dict.fromkeys(TriggerSource, Fate.CANCEL))
    sessions = Sessions(turns, Priority.NORMAL, lambda s, c: seen.append((s, c)))
    gate = TriggerGate(
        "s1",
        sessions,
        lambda _: OWNER,
        Recorder(MemoryEventLog(), SystemClock()),
        session_transcript(sessions)[0],
        settle_s=SETTLE_S,
        response_timeout_s=TIMEOUT_S,
    )
    await run(gate, [Call(lambda: sessions.submit(trig(Priority.NORMAL, TriggerSource.TEXT)))])
    assert seen == [("s1", OWNER)]
    await sessions.detach("s1")
    assert sessions.names() == [] and sessions.running("s1") is None
    with pytest.raises(ValueError):
        await sessions.submit(trig(Priority.NORMAL))


async def test_heard_segment_is_written_and_tied_to_its_turn() -> None:
    log, store = MemoryEventLog(), MemoryTranscript()
    _, gate = make(log=log, store=store)
    segment = TranscriptionFrame("dişçi notunu sil", "p1", "")
    down, _ = await run(gate, [UserStartedSpeakingFrame(), segment])
    [started] = log.of(EventKind.TURN_STARTED)
    [utterance] = store.utterances
    assert (utterance.text, utterance.role) == ("dişçi notunu sil", Role.OWNER)
    assert utterance.turn_id == started.header.turn_id
    [stt] = log.of(EventKind.STT_SEGMENT)
    record = f"utterance:{utterance.id}"
    assert stt.header.related == (record,)
    assert stt.body["muted"] is False
    assert stt.body["speaker_score"] is None  # konuşmacı tanıma yok
    assert "dişçi" not in json.dumps(stt.body)  # metin yalnızca transkriptte (§11)
    # Kayıt kare üstünde aşağı gider: onay kapısı cevabı ona bağlar.
    [passed] = [f for f in down if isinstance(f, TranscriptionFrame)]
    assert passed.metadata["mayen.utterance"] == record


async def test_segment_that_is_not_heard_is_written_as_muted() -> None:
    log, store = MemoryEventLog(), MemoryTranscript()
    sessions, gate = make(log=log, store=store)
    # Süren hatırlatma turunu aynı öncelikteki söz kesemez; söz duyulmaz ama yazılır (§6).
    frames: list[Frame] = [
        Call(lambda: sessions.submit(trig(Priority.NORMAL))),
        SleepFrame(0.05),  # adımlar kapıdan sonra çalışır; söz tur başladıktan sonra gelsin
        TranscriptionFrame("bir şey", "p1", ""),
    ]
    await run(gate, frames)
    [stt] = log.of(EventKind.STT_SEGMENT)
    assert stt.body["muted"] is True
    assert [u.text for u in store.utterances] == ["bir şey"]


async def test_turn_start_names_its_owner_and_links_the_triggers_records() -> None:
    log = MemoryEventLog()
    sessions, gate = make(log=log)
    trigger = Trigger(
        "s1", Priority.NORMAL, TriggerSource.TIMER, "su iç", SYSTEM, records=("timer:4",)
    )
    await run(gate, [Call(lambda: sessions.submit(trigger))])
    [started] = log.of(EventKind.TURN_STARTED)
    assert started.body["requester"] == {"role": "system", "person_id": "p1"}
    # İçerik kopyalanmaz; tur zamanlayıcı kaydına kimliğiyle bağlanır.
    assert started.header.related == ("timer:4",)


async def test_gate_reports_the_sessions_state() -> None:
    seen: list[SessionState] = []
    sessions, gate = make(state=StateTracker(lambda _, current: seen.append(current)))
    frames: list[Frame] = [
        UserStartedSpeakingFrame(),
        UserStoppedSpeakingFrame(),
        BotStartedSpeakingFrame(),
        BotStoppedSpeakingFrame(),
        Call(gate.response_started),
        Call(gate.response_stopped),
        SleepFrame(SETTLE_S * 3),
        Call(lambda: sessions.submit(trig(Priority.LOW, content="chat"))),
        Call(lambda: sessions.submit(trig(Priority.URGENT, content="alarm"))),
        Call(gate.response_started),
        Call(gate.response_stopped),
        SleepFrame(SETTLE_S * 3),
    ]
    await run(gate, frames)
    s = SessionState
    assert seen == [
        s.LISTENING,  # söz sesli turu açtı
        s.THINKING,
        s.SPEAKING,
        s.THINKING,
        s.IDLE,
        s.THINKING,  # hatırlatma
        s.IDLE,  # acil tur onu kesti
        s.THINKING,
        s.IDLE,
    ]
