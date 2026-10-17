"""Replay (§14): kayıtlardan o günkü geçmiş, bugünkü modelle yeniden oynatma, sahte tool'lar."""

import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from fakes import T0, MemoryEventLog, MemoryTranscript
from mayen.core.policy import ROLE_TABLE, PolicyTable, system_table
from mayen.core.registry import ToolRegistry
from mayen.core.timers import local
from mayen.pipeline.llm import StepCap
from mayen.ports.events import Event, EventId, EventKind, Header
from mayen.ports.models import ModelCall, ModelReply
from mayen.ports.people import DeviceId, Person
from mayen.ports.timers import Timer, TimerState
from mayen.ports.tools import Caller, Effect, Role, Sensitivity
from mayen.ports.transcript import Party, Utterance, UtteranceId
from mayen.ports.triggers import Priority, TurnId
from mayen.replay.history import Records
from mayen.replay.run import Called, Replayer, Said, render
from mayen.skills import note_delete, note_search

OWNER = Person("1", "Sahip", Role.OWNER, "British English", None, (DeviceId("local"),))
TEXT_TURN = TurnId(uuid.uuid4())
TIMER_TURN = TurnId(uuid.uuid4())
DUE = T0 + timedelta(seconds=9)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class Log:
    """Bir oturumun kaydı; olaylar ve sözler verildiği sırayla."""

    def __init__(self) -> None:
        self.events = MemoryEventLog()
        self.transcript = MemoryTranscript()

    def event(
        self,
        kind: EventKind,
        seconds: float,
        turn: TurnId | None,
        body: dict[str, Any],
        related: Sequence[str] = (),
    ) -> None:
        header = Header(
            EventId(uuid.uuid4()), kind, "test", at(seconds), "s1", turn, related=related
        )
        self.events.append(Event(header, body))

    def said(self, party: Party, seconds: float, turn: TurnId | None, text: str) -> str:
        person = party is Party.PERSON
        utterance = Utterance(
            UtteranceId(uuid.uuid4()),
            at(seconds),
            "s1",
            turn,
            party,
            Role.OWNER if person else None,
            "1" if person else None,
            text,
        )
        self.transcript.append(utterance)
        return f"utterance:{utterance.id}"

    def tool(
        self,
        seconds: float,
        turn: TurnId,
        call_id: str,
        tool: str,
        arguments: dict[str, Any],
        verdict: str,
        result: dict[str, Any] | None,
    ) -> None:
        body = {"tool": tool, "arguments": arguments, "call_id": call_id}
        self.event(EventKind.TOOL_REQUESTED, seconds, turn, {**body, "verdict": verdict})
        if result is not None:
            self.event(EventKind.TOOL_FINISHED, seconds + 0.1, turn, {**body, "result": result})


def envelope(data: dict[str, Any], records: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
    return {
        "status": "ok",
        "data": data,
        "records": list(records),
        "error": None,
        "withheld": 0,
    }


FOUND = envelope(
    {"found": 1}, [{"sensitivity": "PERSONAL", "data": {"id": "5", "text": "dişçi yarın"}}]
)


def recorded() -> Log:
    """Yazılı bir silme turu (onaylı) ve ardından çalan bir hatırlatma."""
    log = Log()
    owner = {"role": "owner", "person_id": "1"}
    log.said(Party.PERSON, 0, TEXT_TURN, "dişçi notunu sil")
    log.event(
        EventKind.TURN_STARTED,
        0.01,
        TEXT_TURN,
        {"source": "text", "priority": "normal", "fresh": True, "requester": owner},
    )
    log.tool(1, TEXT_TURN, "c1", "note_search", {"query": "dişçi"}, "allow", FOUND)
    log.tool(2, TEXT_TURN, "c2", "note_delete", {"id": "5"}, "confirm", None)
    log.said(Party.ASSISTANT, 2.5, TEXT_TURN, "Delete note 5?")
    answer = log.said(Party.PERSON, 3, TEXT_TURN, "evet")
    deleted = envelope({"deleted": "5"})
    log.event(
        EventKind.TOOL_FINISHED,
        3.4,
        TEXT_TURN,
        {"tool": "note_delete", "arguments": {"id": "5"}, "call_id": "c2", "result": deleted},
    )
    report = {
        "confirmation": "confirmed",
        "calls": [
            {"tool": "note_delete", "arguments": {"id": "5"}, "result": {"status": "ok"}}
        ],
    }
    log.event(EventKind.CONFIRMATION_CLOSED, 3.5, TEXT_TURN, report, [answer])
    log.said(Party.ASSISTANT, 4, TEXT_TURN, "Note 5 deleted.")
    log.event(EventKind.TURN_FINISHED, 5, TEXT_TURN, {"unanswered": False})
    system = {"role": "system", "person_id": None}
    log.event(
        EventKind.TURN_STARTED,
        10,
        TIMER_TURN,
        {
            "source": "timer",
            "priority": "high",
            "fresh": True,
            "requester": system,
            "device_person": "1",
        },
        ["timer:7"],
    )
    log.said(Party.ASSISTANT, 11, TIMER_TURN, "Time to drink water.")
    return log


class Timers:
    def get(self, timer_id: str) -> Timer | None:
        if timer_id != "7":
            return None
        return Timer(
            "7", DUE, "su iç", Priority.HIGH, 60.0, Sensitivity.PERSONAL, "1", TimerState.FIRED
        )


class People:
    def get(self, person_id: str) -> Person | None:
        return OWNER if person_id == "1" else None


class Model:
    """Sırayla verilen cevaplar; her isteği saklar."""

    def __init__(self, *replies: ModelReply) -> None:
        self.replies = list(replies)
        self.requests: list[tuple[list[Mapping[str, Any]], str]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        tool_choice: str,
    ) -> ModelReply:
        self.requests.append((list(messages), tool_choice))
        return self.replies.pop(0) if self.replies else ModelReply("done")


def caller(role: Role, person_id: str | None) -> Caller:
    return Caller(role, person_id, has_personal_device=person_id is not None)


def player(log: Log, model: Model, max_steps: int = 5) -> Replayer:
    return Replayer(
        log.events,
        log.transcript,
        Timers(),  # type: ignore[arg-type]  # yalnızca `get` okunur
        People(),  # type: ignore[arg-type]
        ToolRegistry([note_search.SPEC, note_delete.SPEC]),
        caller,
        lambda source: TABLE,
        model,
        "SYSTEM PROMPT",
        "Answer in {language}.",
        "English",
        StepCap(max_steps, 2),
    )


def call(call_id: str, name: str, arguments: dict[str, Any]) -> ModelReply:
    return ModelReply("", [ModelCall(call_id, name, json.dumps(arguments))])


# Hatırlatmanın açtığı turda `system` kişisel kaydı okuyabilir (config'teki gibi).
TABLE: PolicyTable = {
    **ROLE_TABLE,
    **system_table({Effect.READ: [Sensitivity.GENERAL, Sensitivity.PERSONAL]}),
}


def test_history_is_what_the_model_saw() -> None:
    log = recorded()
    records = Records(log.events.events, log.transcript.utterances, Timers(), caller)  # type: ignore[arg-type]
    history = records.history(lambda source: TABLE)
    contents = [(m["role"], m.get("content")) for m in history]
    assert contents == [
        ("user", "dişçi notunu sil"),
        ("assistant", None),
        (
            "tool",
            json.dumps(
                {"status": "ok", "found": 1, "records": [{"id": "5", "text": "dişçi yarın"}]},
                ensure_ascii=False,
            ),
        ),
        ("assistant", None),
        ("tool", json.dumps({"status": "awaiting_confirmation"})),
        ("assistant", "Delete note 5?"),
        # "evet" modele gitmedi; onayın sonucu geliştirici mesajıdır.
        (
            "developer",
            json.dumps(
                log.events.of(EventKind.CONFIRMATION_CLOSED)[0].body, ensure_ascii=False
            ),
        ),
        ("assistant", "Note 5 deleted."),
        (
            "developer",
            json.dumps(
                {
                    "trigger": "timer",
                    "priority": "high",
                    "content": "su iç",
                    "details": {"due": local(DUE)},
                },
                ensure_ascii=False,
            ),
        ),
        ("assistant", "Time to drink water."),
    ]
    first_call = history[1]["tool_calls"][0]
    assert first_call["id"] == "c1"
    assert json.loads(first_call["function"]["arguments"]) == {"query": "dişçi"}


async def test_turn_is_replayed_from_its_opening_with_recorded_results() -> None:
    model = Model(
        call("n1", "note_search", {"query": "dişçi"}),
        call("n2", "note_delete", {"id": "5"}),
    )
    replay = await player(recorded(), model).replay(TEXT_TURN)

    first, _ = model.requests[0]
    assert first[0] == {"role": "system", "content": "SYSTEM PROMPT"}
    # Bağlam bloğu turu açan mesajın önünde, o günün tarihiyle (§8.3).
    assert (
        first[1]["role"] == "developer" and "Answer in British English." in first[1]["content"]
    )
    # Söz, hattaki gibi konuşanın adıyla (§8.1).
    assert first[2:] == [{"role": "user", "content": "Sahip: dişçi notunu sil"}]
    assert replay.heard == "Sahip: dişçi notunu sil"
    [found, asked] = [s for s in replay.replayed if isinstance(s, Called)]
    assert found.result == {
        "status": "ok",
        "found": 1,
        "records": [{"id": "5", "text": "dişçi yarın"}],
    }
    # Onay gereken çağrıda durulur: orada soru sorulurdu.
    assert (asked.verdict, asked.result) == ("confirm", {"status": "awaiting_confirmation"})
    assert len(model.requests) == 2
    assert replay.original == [
        Called("note_search", {"query": "dişçi"}, "allow"),
        Called("note_delete", {"id": "5"}, "confirm"),
        Said("Delete note 5?"),
        Said("Note 5 deleted."),
    ]
    assert "now:" in render(replay)


async def test_timer_turn_gets_its_trigger_and_mocks_and_unknown_calls() -> None:
    model = Model(
        ModelReply(
            "",
            [
                ModelCall("a", "note_search", json.dumps({"query": "su"})),
                ModelCall("b", "note_search", json.dumps({"query": "ilaç"})),
            ],
        ),
        ModelReply("Drink water."),
    )
    mocks = {"note_search": {"status": "ok", "found": 0}}
    replay = await player(recorded(), model).replay(TIMER_TURN, mocks)
    first, _ = model.requests[0]
    assert json.loads(first[-1]["content"])["content"] == "su iç"
    # Kimse istemeden açılan turu oturumun cihazının kişisi dinler; dili onun (§8.6).
    assert "Answer in British English." in first[-2]["content"]
    assert [s.result for s in replay.replayed if isinstance(s, Called)] == [
        {"status": "ok", "found": 0},
        {"status": "ok", "found": 0},
    ]
    assert replay.replayed[-1] == Said("Drink water.")

    unmocked = await player(
        recorded(), Model(call("a", "note_search", {"query": "su"}))
    ).replay(TIMER_TURN)
    [step, _] = unmocked.replayed
    assert isinstance(step, Called) and step.result is not None
    assert step.result["error"] == "replay: no mock for this call"


async def test_step_cap_takes_the_tools_away() -> None:
    model = Model(*[call(f"n{i}", "note_search", {"query": "x"}) for i in range(5)])
    await player(recorded(), model, max_steps=2).replay(TIMER_TURN)
    choices = [choice for _, choice in model.requests]
    assert choices == ["auto", "auto", "none"]


async def test_turns_are_listed_and_found_by_prefix() -> None:
    p = player(recorded(), Model())
    assert [t.id for t in p.turns()] == [TEXT_TURN, TIMER_TURN]
    assert p.find(str(TIMER_TURN)[:8]).id == TIMER_TURN
    assert p.find(str(TEXT_TURN)).requester.role is Role.OWNER


def test_voice_turn_requester_is_who_the_turn_ended_with() -> None:
    log = Log()
    turn, old = TurnId(uuid.uuid4()), TurnId(uuid.uuid4())
    unknown = {"role": "unknown", "person_id": None}
    started = {"source": "voice", "priority": "normal", "fresh": True, "requester": unknown}
    for t, seconds in ((turn, 0), (old, 10)):
        # "Hey Mayen" tek başına tanınmadı; komut sahibin sesiydi.
        log.transcript.append(
            Utterance(
                UtteranceId(uuid.uuid4()),
                at(seconds),
                "s1",
                t,
                Party.PERSON,
                Role.UNKNOWN,
                None,
                "Hey Mayen",
            )
        )
        log.event(EventKind.TURN_STARTED, seconds, t, started)
    owner = {"role": "owner", "person_id": "1"}
    log.event(EventKind.TURN_FINISHED, 5, turn, {"unanswered": False, "requester": owner})
    log.event(EventKind.TURN_FINISHED, 15, old, {"unanswered": False})  # eski kayıt
    records = Records(log.events.events, log.transcript.utterances, Timers(), caller)  # type: ignore[arg-type]
    assert records.turns[turn].requester.role is Role.OWNER
    assert records.turns[old].requester.role is Role.UNKNOWN  # ilk sözün konuşanı


def test_restarted_text_turn_brings_its_message_again() -> None:
    log = Log()
    first, again = TurnId(uuid.uuid4()), TurnId(uuid.uuid4())
    owner = {"role": "owner", "person_id": "1"}
    started = {"source": "text", "priority": "normal", "requester": owner}
    log.said(Party.PERSON, 0, first, "berber notunu sil")
    log.event(EventKind.TURN_STARTED, 0.01, first, {**started, "fresh": True})
    log.event(EventKind.TURN_INTERRUPTED, 1, first, {"fate": "restart"})
    log.event(EventKind.TURN_STARTED, 2, again, {**started, "fresh": False})
    records = Records(log.events.events, log.transcript.utterances, Timers(), caller)  # type: ignore[arg-type]
    # Hat baştan başlayan turda mesajı yeniden ekler; geçmiş o gün nasılsa öyle kurulur.
    assert records.history(lambda source: TABLE) == [
        {"role": "user", "content": "berber notunu sil"},
        {"role": "user", "content": "berber notunu sil"},
    ]
