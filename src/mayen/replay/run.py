"""Kaydedilmiş bir turu yeniden oynatma (§14): o günkü geçmiş, bugünkü prompt ve model.

Model turun ilk cevabını yazdığı andaki geçmişi görür ve cevabı baştan üretir. Yetki kararı
gerçektir; tool gövdesi hiç çalışmaz (§14: hiçbir gerçek eylem tetiklenmez). İzin verilen
çağrının sonucu önce kullanıcının mock'undan, yoksa aynı turda aynı argümanlarla yapılmış
çağrının kayıttaki sonucundan gelir. Onay gereken çağrıda oynatma durur: orada soru
sorulurdu ve cevabı kayıtta yok.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mayen.core.context import ContextBlock
from mayen.core.policy import decide, filter_records
from mayen.core.presence import Presence
from mayen.core.registry import ToolRegistry, parse_args
from mayen.pipeline.llm import StepCap, count_steps, with_block
from mayen.pipeline.tools import AWAITING_CONFIRMATION, openai_tools, to_model
from mayen.ports.events import EventKind, EventLog
from mayen.ports.models import ChatModel
from mayen.ports.people import PersonStore
from mayen.ports.timers import TimerStore
from mayen.ports.tools import Status, ToolResult, TurnFlags, Verdict
from mayen.ports.transcript import Party, TranscriptStore
from mayen.ports.triggers import TurnId
from mayen.replay.history import CallerOf, Message, Records, TableOf, TurnInfo, clean, result_of


@dataclass(frozen=True)
class Said:
    text: str


@dataclass(frozen=True)
class Called:
    tool: str
    arguments: Any
    verdict: str | None  # argümanı doğrulanamayan çağrıda karar yok
    result: Mapping[str, Any] | None = None  # modelin gördüğü sonuç


type Step = Said | Called


@dataclass(frozen=True)
class Replay:
    turn: TurnInfo
    heard: str  # turu açan söz ya da tetikleyici mesajı
    original: list[Step]
    replayed: list[Step] = field(default_factory=list)


class FixedClock:
    """Bağlam bloğunun saati turun başladığı an: model o günün tarihini görür."""

    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment

    def monotonic(self) -> float:
        return 0.0


class Replayer:
    def __init__(
        self,
        events: EventLog,
        transcript: TranscriptStore,
        timers: TimerStore,
        people: PersonStore,
        registry: ToolRegistry,
        caller_of: CallerOf,
        table: TableOf,
        model: ChatModel,
        system_prompt: str,
        language_rule: str,
        default_language: str,
        cap: StepCap,
    ) -> None:
        self._events = events
        self._transcript = transcript
        self._timers = timers
        self._people = people
        self._registry = registry
        self._caller_of = caller_of
        self._table = table
        self._model = model
        self._system = system_prompt
        self._rule = language_rule
        self._default = default_language
        self._cap = cap

    def turns(self) -> list[TurnInfo]:
        """Kayıttaki bütün turlar, başlama sırasıyla."""
        records = Records(
            self._events.read(), self._transcript.read(), self._timers, self._caller_of
        )
        return sorted(records.turns.values(), key=lambda t: t.time)

    def find(self, prefix: str) -> TurnInfo:
        """Kimliği bu önekle başlayan tek tur."""
        found = [t for t in self.turns() if str(t.id).startswith(prefix)]
        if len(found) != 1:
            raise LookupError(f"{len(found)} turns match {prefix!r}")
        return found[0]

    async def replay(
        self, turn_id: TurnId, mocks: Mapping[str, Mapping[str, Any]] | None = None
    ) -> Replay:
        found = self._events.read(turn_id=turn_id)
        session = next((e.header.session for e in found if e.header.session), None)
        if session is None:
            raise LookupError(f"no turn {turn_id}")
        records = Records(
            self._events.read(session=session),
            self._transcript.read(session=session),
            self._timers,
            self._caller_of,
        )
        turn = records.turns[turn_id]
        outputs = [
            e.header.time
            for e in records.events
            if e.header.turn_id == turn_id and e.header.kind is EventKind.TOOL_REQUESTED
        ] + [
            u.time
            for u in records.utterances
            if u.turn_id == turn_id and u.party is Party.ASSISTANT
        ]
        # Model ilk cevabını yazdığı an neyi gördüyse o: turu açan söz dahil, cevabı hariç.
        cut = min(outputs, default=None)
        history = records.history(self._table, cut)
        before = records.history(self._table, turn.time)
        heard = " / ".join(str(m.get("content", "")) for m in history[len(before) :])
        result = Replay(turn, heard, _original(records, turn_id, cut))
        await self._run(turn, session, clean(history), result.replayed, mocks or {}, records)
        return result

    async def _run(
        self,
        turn: TurnInfo,
        session: str,
        history: list[Message],
        out: list[Step],
        mocks: Mapping[str, Mapping[str, Any]],
        records: Records,
    ) -> None:
        block = ContextBlock(
            self._people, Presence(), FixedClock(turn.time), self._rule, self._default
        ).render(session, turn.requester)
        tools = openai_tools(self._registry)
        malformed: set[str] = set()
        # Her adım bir istek; tavan aşılınca istek tool'suz gider ve model susmak zorunda kalır.
        for _ in range(self._cap.max_steps + self._cap.max_corrections + 2):
            messages = [
                {"role": "system", "content": self._system},
                *with_block(history, block),
            ]
            steps = count_steps(history, lambda call_id: call_id in malformed)
            tool_choice = "auto"
            if self._cap.reached(steps):
                note = {"step_cap": {"steps": steps.taken, "corrections": steps.corrections}}
                messages.append({"role": "developer", "content": json.dumps(note)})
                tool_choice = "none"
            reply = await self._model.complete(messages, tools, tool_choice)
            message: Message = {"role": "assistant"}
            if reply.text:
                message["content"] = reply.text
                out.append(Said(reply.text))
            if reply.calls:
                message["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": c.arguments},
                    }
                    for c in reply.calls
                ]
            history.append(message)
            if not reply.calls or tool_choice == "none":
                return  # tool'suz istekte gelen çağrı çalışmaz; tur burada biter
            awaiting = False
            for call in reply.calls:
                step = self._call(call.name, call.arguments, turn, mocks, records)
                if step.verdict is None:
                    malformed.add(call.id)
                awaiting |= step.verdict == Verdict.CONFIRM.value
                out.append(step)
                content = json.dumps(dict(step.result or {}), ensure_ascii=False)
                history.append({"role": "tool", "tool_call_id": call.id, "content": content})
            if awaiting:
                return  # burada onay sorusu sorulurdu (§10.5)

    def _call(
        self,
        name: str,
        raw: str,
        turn: TurnInfo,
        mocks: Mapping[str, Mapping[str, Any]],
        records: Records,
    ) -> Called:
        spec = self._registry.get(name)
        try:
            arguments = json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            return Called(name, raw, None, to_model(ToolResult(Status.ERROR, error=str(e))))
        if spec is None:
            error = ToolResult(Status.ERROR, error=f"unknown tool: {name}")
            return Called(name, arguments, None, to_model(error))
        args = parse_args(spec, arguments)
        if isinstance(args, str):
            return Called(name, arguments, None, to_model(ToolResult(Status.ERROR, error=args)))
        table = self._table(turn.source)
        decision = decide(spec, turn.requester, table, TurnFlags())
        verdict = decision.verdict.value
        if decision.verdict is Verdict.DENY:
            refused = ToolResult(Status.DENIED, error=decision.reason)
            return Called(name, arguments, verdict, to_model(refused))
        if decision.verdict is Verdict.CONFIRM:
            return Called(name, arguments, verdict, {"status": AWAITING_CONFIRMATION})
        if name in mocks:
            return Called(name, arguments, verdict, dict(mocks[name]))
        dumped = args.model_dump(mode="json")
        recorded = next(
            (
                result_of(e.body)
                for e in records.events
                if e.header.turn_id == turn.id
                and e.header.kind is EventKind.TOOL_FINISHED
                and e.body["tool"] == name
                and e.body["arguments"] == dumped
                and e.body["result"]["status"] != Status.DENIED.value
            ),
            None,
        )
        if recorded is None:
            missing = ToolResult(Status.ERROR, error="replay: no mock for this call")
            return Called(name, arguments, verdict, to_model(missing))
        view = to_model(filter_records(recorded, turn.requester, table))
        return Called(name, arguments, verdict, view)


def _original(records: Records, turn_id: TurnId, cut: datetime | None) -> list[Step]:
    """Turda o gün modelin yaptıkları: çağrılar ve söyledikleri, sırayla."""
    if cut is None:
        return []
    steps: list[tuple[datetime, Step]] = []
    for e in records.events:
        h = e.header
        if h.turn_id == turn_id and h.kind is EventKind.TOOL_REQUESTED:
            steps.append(
                (h.time, Called(e.body["tool"], e.body["arguments"], e.body["verdict"]))
            )
    for u in records.utterances:
        if u.turn_id == turn_id and u.party is Party.ASSISTANT:
            steps.append((u.time, Said(u.text)))
    return [step for _, step in sorted(steps, key=lambda s: s[0])]


def render(replay: Replay) -> str:
    """Sahibin okuyacağı karşılaştırma: o gün ve şimdi."""
    t = replay.turn
    lines = [
        f"turn {t.id} ({t.source.value}, {t.time.astimezone():%Y-%m-%d %H:%M:%S},"
        f" {t.requester.role.value})",
        f"opened by: {replay.heard}",
        "",
        "then:",
        *_steps(replay.original),
        "",
        "now:",
        *_steps(replay.replayed),
    ]
    return "\n".join(lines)


def _steps(steps: Sequence[Step]) -> list[str]:
    if not steps:
        return ["  (nothing)"]
    lines = []
    for step in steps:
        if isinstance(step, Said):
            lines.append(f"  said: {step.text}")
        else:
            arguments = json.dumps(step.arguments, ensure_ascii=False)
            line = f"  call: {step.tool} {arguments} [{step.verdict or 'malformed'}]"
            if step.result is not None:
                line += f" -> {json.dumps(dict(step.result), ensure_ascii=False)}"
            lines.append(line)
    return lines
