"""Yetki sarmalayıcısı (§10.3, §10.5 adım 1, §9.1): Pipecat hattı çalıştırılmadan."""

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from enum import StrEnum
from typing import Any, cast

from pipecat.frames.frames import DataFrame, Frame, FunctionCallFromLLM, LLMContextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMAssistantAggregator
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import LLMService
from pipecat.tests.utils import SleepFrame, run_test
from pydantic import BaseModel, Field

from fakes import FakeClock, MemoryEventLog
from mayen.core.events import Recorder
from mayen.core.policy import ROLE_TABLE, system_table
from mayen.core.registry import ToolRegistry
from mayen.pipeline.events import SessionEvents
from mayen.pipeline.tools import AWAITING_CONFIRMATION, AuthorizedTools, Shown, tools_schema
from mayen.ports.events import EventKind
from mayen.ports.tools import (
    Caller,
    Confirmation,
    Effect,
    Record,
    Role,
    Sensitivity,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
    TurnFlags,
)

OWNER = Caller(Role.OWNER, "p1", has_personal_device=True)
GUEST = Caller(Role.ACQUAINTANCE, "p2", has_personal_device=True)


class NoteId(BaseModel):
    id: int


class Ctx:
    def __init__(self) -> None:
        self.data: dict[int, tuple[Sensitivity, str]] = {
            1: (Sensitivity.GENERAL, "çöpü çıkar"),
            2: (Sensitivity.PERSONAL, "tahlil sonucu"),
        }
        self.caller: Caller | None = None  # bağlam çağrı başınadır; son çağıran


async def _search(args: BaseModel, ctx: ToolContext) -> ToolResult:
    assert isinstance(ctx, Ctx)
    records = [Record(s, {"id": i, "body": b}) for i, (s, b) in ctx.data.items()]
    return ToolResult(Status.OK, records=records)


async def _delete(args: BaseModel, ctx: ToolContext) -> ToolResult:
    assert isinstance(args, NoteId) and isinstance(ctx, Ctx)
    del ctx.data[args.id]
    return ToolResult(Status.OK, {"deleted": args.id})


async def _slow(args: BaseModel, ctx: ToolContext) -> ToolResult:
    await asyncio.sleep(1)
    return ToolResult(Status.OK)


async def _broken(args: BaseModel, ctx: ToolContext) -> ToolResult:
    raise RuntimeError("disk full")


class Empty(BaseModel):
    pass


Body = Callable[[Any, ToolContext], Awaitable[ToolResult]]


def _spec(name: str, effect: Effect, run: Body, args: type[BaseModel] = Empty) -> ToolSpec[Any]:
    return ToolSpec(
        name=name,
        description=name,
        args=args,
        effect=effect,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=False,
        timeout_s=0.05,
        run=run,
    )


SEARCH = _spec("note_search", Effect.READ, _search)
DELETE = _spec("note_delete", Effect.IRREVERSIBLE, _delete, NoteId)
SLOW = _spec("slow", Effect.READ, _slow)
BROKEN = _spec("broken", Effect.READ, _broken)


class Gate:
    def __init__(self) -> None:
        self.kind: Confirmation | None = None
        self.execute: Callable[[], Awaitable[ToolResult]] | None = None

    async def request(
        self,
        spec: ToolSpec[Any],
        args: BaseModel,
        kind: Confirmation,
        execute: Callable[[], Awaitable[ToolResult]],
        requester: Caller,
    ) -> None:
        self.kind = kind
        self.execute = execute


def tools(
    caller: Caller = OWNER,
    log: MemoryEventLog | None = None,
    ran: Callable[[], Awaitable[None]] | None = None,
    shown: Shown | None = None,
) -> tuple[AuthorizedTools, Ctx, Gate]:
    ctx, gate = Ctx(), Gate()

    def context(spec: ToolSpec[Any], c: Caller) -> ToolContext:
        ctx.caller = c
        return cast(ToolContext, ctx)

    registry = ToolRegistry([SEARCH, DELETE, SLOW, BROKEN])
    events = SessionEvents(Recorder(log or MemoryEventLog(), FakeClock()), "s1", lambda: None)
    return (
        AuthorizedTools(
            registry,
            lambda: ROLE_TABLE,
            context,
            gate,
            lambda: caller,
            TurnFlags,
            events,
            ran,
            shown,
        ),
        ctx,
        gate,
    )


async def test_allowed_call_runs() -> None:
    t, _, _ = tools()
    result, props = await t.call(SEARCH, {})
    assert result["status"] == "ok"
    assert len(result["records"]) == 2
    assert props is None


async def test_the_sound_follows_the_body_not_the_request() -> None:
    # Ses tool'un çalıştığını gösterir (§8.8): reddedilen ya da onay bekleyen çağrıda yok,
    # onaylanıp çalışan çağrıda var.
    played: list[str] = []

    async def ran() -> None:
        played.append("blip")

    t, _, gate = tools(GUEST, ran=ran)
    await t.call(SEARCH, {})
    await t.call(DELETE, {"id": 1})
    assert played == ["blip"]
    t, _, gate = tools(ran=ran)
    await t.call(DELETE, {"id": 2})
    assert played == ["blip"]
    assert gate.execute is not None
    await gate.execute()
    assert played == ["blip", "blip"]


async def test_the_body_sees_its_caller() -> None:
    t, ctx, _ = tools(GUEST)
    await t.call(SEARCH, {})
    assert ctx.caller == GUEST


async def test_the_table_is_read_at_call_time() -> None:
    # `system`'in yetkisi turu açan kaynağa göredir (§10.2): tablo çağrı anında okunur.
    ctx, gate = Ctx(), Gate()
    events = SessionEvents(Recorder(MemoryEventLog(), FakeClock()), "s1", lambda: None)
    system = Caller(Role.SYSTEM, None, has_personal_device=False)
    tables = [{**ROLE_TABLE, **system_table({Effect.READ: [Sensitivity.GENERAL]})}]
    t = AuthorizedTools(
        ToolRegistry([SEARCH]),
        lambda: tables[0],
        lambda spec, c: cast(ToolContext, ctx),
        gate,
        lambda: system,
        TurnFlags,
        events,
    )
    result, _ = await t.call(SEARCH, {})
    assert [r["body"] for r in result["records"]] == ["çöpü çıkar"]
    tables[0] = {**ROLE_TABLE, **system_table({})}
    result, _ = await t.call(SEARCH, {})
    assert result["status"] == "denied"


async def test_guest_gets_general_records_and_a_count() -> None:
    t, _, _ = tools(GUEST)
    result, _ = await t.call(SEARCH, {})
    assert [r["body"] for r in result["records"]] == ["çöpü çıkar"]
    assert result["withheld_records"] == 1


async def test_the_screen_gets_what_the_model_gets_and_refusals() -> None:
    # Olaydaki sonuç süzgeçten öncedir (§5.5); ekrana süzülmüş hâli gider (§7).
    seen: list[tuple[str, dict[str, Any], ToolResult]] = []

    async def shown(spec: ToolSpec[Any], arguments: Mapping[str, Any], r: ToolResult) -> None:
        seen.append((spec.name, dict(arguments), r))

    t, _, gate = tools(GUEST, shown=shown)
    await t.call(SEARCH, {})
    await t.call(DELETE, {"id": 1})
    (name, _, searched), (refused, arguments, denied) = seen
    assert name == "note_search" and [r.data["body"] for r in searched.records] == [
        "çöpü çıkar"
    ]
    assert searched.withheld == 1
    assert (refused, arguments, denied.status) == ("note_delete", {"id": 1}, Status.DENIED)
    t, _, gate = tools(shown=shown)
    await t.call(DELETE, {"id": 2})
    assert len(seen) == 2  # onay bekleyen çağrının sonucu henüz yok
    assert gate.execute is not None
    await gate.execute()
    assert seen[-1][0] == "note_delete" and seen[-1][2].data == {"deleted": 2}


async def test_denied_call_does_not_run() -> None:
    t, ctx, gate = tools(GUEST)
    result, _ = await t.call(DELETE, {"id": 1})
    assert result["status"] == "denied"
    assert 1 in ctx.data
    assert gate.execute is None


async def test_invalid_args_never_reach_the_gate() -> None:
    t, _, gate = tools()
    result, _ = await t.call(DELETE, {"id": "first"})
    assert result["status"] == "error"
    assert gate.execute is None


async def test_confirmation_holds_the_body_and_silences_the_model() -> None:
    t, ctx, gate = tools()
    result, props = await t.call(DELETE, {"id": 2})
    assert result == {"status": AWAITING_CONFIRMATION}
    assert props is not None and props.run_llm is False
    assert gate.kind is Confirmation.INTENT
    assert 2 in ctx.data, "onaydan önce gövde çalışmamalı"

    assert gate.execute is not None
    done = await gate.execute()
    assert done.status is Status.OK
    assert 2 not in ctx.data


async def test_timeout_is_a_result() -> None:
    t, _, _ = tools()
    result, _ = await t.call(SLOW, {})
    assert result["status"] == "timeout"


async def test_exception_is_a_result() -> None:
    t, _, _ = tools()
    result, _ = await t.call(BROKEN, {})
    assert result == {"status": "error", "error": "disk full"}


def test_schema_lists_every_tool() -> None:
    t, _, _ = tools()
    schema = t.schema()
    names = [f.name for f in schema.standard_tools]
    assert names == ["note_search", "note_delete", "slow", "broken"]
    delete = schema.standard_tools[1]
    assert delete.required == ["id"]


class Level(StrEnum):
    LOW = "low"
    HIGH = "high"


class WithEnum(BaseModel):
    level: Level = Field(default=Level.LOW, description="how loud")


def test_schema_carries_no_dangling_refs() -> None:
    # `$defs` alanlarla gitmez; şemayı dil bilgisine çeviren sunucu çözülemeyen ref'i reddeder.
    spec = _spec("set_level", Effect.WRITE, _search, WithEnum)
    (function,) = tools_schema(ToolRegistry([spec])).standard_tools
    assert "$ref" not in json.dumps(function.properties)
    assert function.properties["level"] == {
        "enum": ["low", "high"],
        "title": "Level",
        "type": "string",
        "default": "low",
        "description": "how loud",
    }


async def test_run_is_recorded_with_the_skills_own_result() -> None:
    log = MemoryEventLog()
    t, _, _ = tools(GUEST, log)
    await t.call(SEARCH, {}, "c1")
    requested, started, finished = log.events
    assert requested.header.kind is EventKind.TOOL_REQUESTED
    assert requested.body == {
        "tool": "note_search",
        "arguments": {},
        "call_id": "c1",
        "verdict": "allow",
    }
    assert started.header.kind is EventKind.TOOL_STARTED
    assert started.body == {"tool": "note_search", "arguments": {}, "call_id": "c1"}
    assert finished.body["call_id"] == "c1"
    assert finished.header.kind is EventKind.TOOL_FINISHED
    assert finished.header.status is Status.OK
    assert finished.header.duration_s is not None
    # Olay kaydı yetki süzgecinden önceki sonucu tutar; modele giden süzülmüş olandır.
    assert len(finished.body["result"]["records"]) == 2
    assert finished.header.session == "s1"


async def test_refused_calls_are_recorded_without_a_start() -> None:
    log = MemoryEventLog()
    t, _, _ = tools(GUEST, log)
    await t.call(DELETE, {"id": 1})
    await t.call(DELETE, {"id": "first"})
    assert log.kinds() == [
        EventKind.TOOL_REQUESTED,
        EventKind.TOOL_FINISHED,
        EventKind.TOOL_REQUESTED,
        EventKind.TOOL_FINISHED,
    ]
    denied, malformed = log.of(EventKind.TOOL_REQUESTED)
    assert denied.body["verdict"] == "deny"
    # Doğrulanamayan çağrıda karar yok; istendiği gibi, ham argümanlarıyla kayıtta.
    assert malformed.body["verdict"] is None
    assert malformed.body["arguments"] == {"id": "first"}
    finished = log.of(EventKind.TOOL_FINISHED)
    assert [e.header.status for e in finished] == [Status.DENIED, Status.ERROR]


async def test_confirmed_body_is_recorded_when_it_runs() -> None:
    log = MemoryEventLog()
    t, _, gate = tools(log=log)
    await t.call(DELETE, {"id": 2}, "c1")
    # Onay bekleyen çağrı da istendiği an kayıtta; gövdesi henüz çalışmadı.
    [requested] = log.events
    assert requested.header.kind is EventKind.TOOL_REQUESTED
    assert requested.body["verdict"] == "confirm"
    assert gate.execute is not None
    await gate.execute()
    assert log.kinds() == [
        EventKind.TOOL_REQUESTED,
        EventKind.TOOL_STARTED,
        EventKind.TOOL_FINISHED,
    ]
    assert {e.body["call_id"] for e in log.events} == {"c1"}


class _Go(DataFrame):
    """Testin modeli: bu kare gelince tek cevapta iki çağrı yapmış gibi davranır."""


class _Model(LLMService):
    def __init__(self) -> None:
        super().__init__(run_in_parallel=False)  # Mayen'in kipi (§9.3)
        self.context = LLMContext()
        self.runs = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMContextFrame):
            self.runs += 1
        elif isinstance(frame, _Go):
            calls = [FunctionCallFromLLM("note_search", i, {}, self.context) for i in "ab"]
            await self.run_function_calls(calls)
        else:
            await self.push_frame(frame, direction)


async def test_one_response_runs_the_model_once() -> None:
    # Pipecat sıralı kipte her sonuçta modeli çalıştırıyordu (pipecat#5852): tura iki cevap.
    t, _, _ = tools()
    model = _Model()
    t.register(model)
    aggregator = LLMAssistantAggregator(model.context)
    await run_test(Pipeline([model, aggregator]), frames_to_send=[_Go(), SleepFrame(0.2)])
    assert model.runs == 1
