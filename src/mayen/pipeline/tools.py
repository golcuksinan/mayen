"""Yetki sarmalayıcısı: her tool çağrısı Pipecat'ten önce buradan geçer (§10.3).

Karar `core`'dadır; burada uygulanır. Onay gereken çağrıda model hemen "onay bekleniyor"
sonucunu alır ve konuşmaz; asıl sonuç onay çözülünce eklenir. Sonucu onaya kadar bekletmek
olmaz: Pipecat kullanıcı konuşmaya başlayınca bekleyen çağrıyı iptal eder, onay cevabı da
bir konuşmadır.
"""

import asyncio
import dataclasses
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import FunctionCallResultProperties
from pipecat.services.llm_service import FunctionCallParams, LLMService
from pydantic import BaseModel

from mayen.core.policy import PolicyTable, decide, filter_records
from mayen.core.registry import ToolRegistry, parse_args
from mayen.pipeline.events import SessionEvents
from mayen.ports.events import EventKind
from mayen.ports.tools import (
    Caller,
    Confirmation,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
    TurnFlags,
    Verdict,
)

AWAITING_CONFIRMATION = "awaiting_confirmation"

type Shown = Callable[[ToolSpec[Any], Mapping[str, Any], ToolResult], Awaitable[None]]


class ConfirmationGate(Protocol):
    """Onay kapısı (§10.5): planı tutar, soruyu sorar, sonucu kendisi modele ekler."""

    async def request(
        self,
        spec: ToolSpec[Any],
        args: BaseModel,
        kind: Confirmation,
        execute: Callable[[], Awaitable[ToolResult]],
        requester: Caller,
    ) -> None: ...


def to_model(result: ToolResult) -> dict[str, Any]:
    """Modele giden kısaltılmış görünüm: boş alanlar bağlamda yer kaplamaz (§9.1)."""
    out: dict[str, Any] = {"status": result.status.value, **result.data}
    if result.records:
        out["records"] = [dict(r.data) for r in result.records]
    if result.withheld:
        out["withheld_records"] = result.withheld
    if result.error:
        out["error"] = result.error
    return out


async def execute(spec: ToolSpec[Any], args: BaseModel, ctx: ToolContext) -> ToolResult:
    """Gövdeyi zaman aşımıyla çalıştırır; hata ve zaman aşımı sonuç olur (§9.1)."""
    try:
        return await asyncio.wait_for(spec.run(args, ctx), spec.timeout_s)
    except TimeoutError:
        return ToolResult(Status.TIMEOUT, error=f"no result within {spec.timeout_s:g} s")
    except Exception as e:  # skill'in hatası modele geri beslenir, yükseltilmez
        return ToolResult(Status.ERROR, error=str(e))


def _inline(node: Any, defs: Mapping[str, Any]) -> Any:  # noqa: ANN401
    """`$ref`'i tanımıyla değiştirir: `$defs` alanlarla birlikte gitmez, ref boşa düşer."""
    if isinstance(node, list):
        return [_inline(n, defs) for n in node]
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    rest = {k: _inline(v, defs) for k, v in node.items() if k != "$ref"}
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        return {**_inline(defs[ref.removeprefix("#/$defs/")], defs), **rest}
    return rest


def tools_schema(registry: ToolRegistry) -> ToolsSchema:
    """Modele giden tool şeması; hat da replay de bunu gönderir (§14)."""
    functions = []
    for spec in registry.specs():
        schema = spec.args.model_json_schema()
        params = _inline(schema, schema.pop("$defs", {}))
        functions.append(
            FunctionSchema(
                name=spec.name,
                description=spec.description,
                properties=params.get("properties", {}),
                required=params.get("required", []),
            )
        )
    return ToolsSchema(standard_tools=functions)


def openai_tools(registry: ToolRegistry) -> list[dict[str, Any]]:
    """Aynı şema, hattın dışından gönderilen istek için OpenAI biçiminde."""
    return [
        {"type": "function", "function": f.to_default_dict()}
        for f in tools_schema(registry).standard_tools
    ]


class AuthorizedTools:
    """Kayıt defterindeki tool'ları yetki kararının arkasında Pipecat'e bağlar."""

    def __init__(
        self,
        registry: ToolRegistry,
        table: Callable[[], PolicyTable],
        context: Callable[[ToolSpec[Any], Caller], ToolContext],
        gate: ConfirmationGate,
        caller: Callable[[], Caller],
        flags: Callable[[], TurnFlags],
        events: SessionEvents,
        ran: Callable[[], Awaitable[None]] | None = None,
        shown: Shown | None = None,
    ) -> None:
        self._registry = registry
        # Tablo, bağlam, çağıran ve işaretler çağrı anında oturum durumundan okunur (§8.1):
        # `system` rolünün yetkisi turu açan tetikleyicinin kaynağına göredir (§10.2).
        self._table = table
        self._context = context
        self._gate = gate
        self._caller = caller
        self._flags = flags
        self._events = events
        # Gövde çalışınca (sonucu ne olursa olsun) çağrılır: sesli oturumda sözsüz ses (§8.8).
        self._ran = ran
        # Modele giden sonuç, süzgeçten sonra: sesli oturumda istemcinin ekranına (§7).
        self._shown = shown
        self._malformed: set[str] = set()  # argümanı doğrulanamayan çağrılar (§9.1)

    def schema(self) -> ToolsSchema:
        return tools_schema(self._registry)

    def register(self, llm: LLMService[Any]) -> None:
        for spec in self._registry.specs():
            llm.register_function(spec.name, self._handler(spec))

    def _handler(self, spec: ToolSpec[Any]) -> Callable[[FunctionCallParams], Awaitable[None]]:
        async def handle(params: FunctionCallParams) -> None:
            result, properties = await self.call(spec, params.arguments, params.tool_call_id)
            await params.result_callback(result, properties=properties)

        return handle

    def malformed(self, call_id: str) -> bool:
        """Bu çağrının argümanları doğrulanamadı mı; düzeltmesi adım harcamaz (§9.1)."""
        return call_id in self._malformed

    async def call(
        self, spec: ToolSpec[Any], raw: Mapping[str, Any], call_id: str | None = None
    ) -> tuple[dict[str, Any], FunctionCallResultProperties | None]:
        """Tek bir çağrı: doğrula, karar ver, uygula. Pipecat'siz test edilebilsin diye ayrı.

        Modelin istediği her çağrı, gövdesi çalışsın ya da çalışmasın, istendiği anda kayda
        girer (§5.5): onay bekleyen çağrı da modelin o an yaptığı bir şeydir.
        """
        args = parse_args(spec, raw)
        if isinstance(args, str):
            if call_id is not None:
                self._malformed.add(call_id)
            self._requested(spec, dict(raw), call_id, None)
            return to_model(self._refused(spec, dict(raw), call_id, Status.ERROR, args)), None

        arguments = args.model_dump(mode="json")
        caller = self._caller()
        table = self._table()
        decision = decide(spec, caller, table, self._flags())
        self._requested(spec, dict(raw), call_id, decision.verdict)
        if decision.verdict is Verdict.DENY:
            # Ret ekranda da görünür: işin neden yapılmadığı sesten kaçırılmış olabilir.
            denied = self._refused(spec, arguments, call_id, Status.DENIED, decision.reason)
            await self._show(spec, arguments, denied)
            return to_model(denied), None

        if decision.verdict is Verdict.CONFIRM:
            assert decision.confirmation is not None

            async def run_confirmed() -> ToolResult:
                return await self._run(spec, args, call_id, caller, table)

            await self._gate.request(spec, args, decision.confirmation, run_confirmed, caller)
            # Model burada konuşmaz; soruyu kapı plandan yazdırıp okutur (§10.5).
            return {"status": AWAITING_CONFIRMATION}, FunctionCallResultProperties(
                run_llm=False
            )

        return to_model(await self._run(spec, args, call_id, caller, table)), None

    def _requested(
        self,
        spec: ToolSpec[Any],
        arguments: dict[str, Any],
        call_id: str | None,
        verdict: Verdict | None,  # argümanı doğrulanamayan çağrıda karar yok
    ) -> None:
        """Argümanlar modelin yazdığı gibidir: geçmişte de o hâliyle durur (replay, §14)."""
        body = {
            "tool": spec.name,
            "arguments": arguments,
            "call_id": call_id,
            "verdict": None if verdict is None else verdict.value,
        }
        self._events.emit(EventKind.TOOL_REQUESTED, __name__, body)

    async def _run(
        self,
        spec: ToolSpec[Any],
        args: BaseModel,
        call_id: str | None,
        caller: Caller,
        table: PolicyTable,
    ) -> ToolResult:
        """Gövdenin çalışması olay kaydına girer; eylem geçmişi bu olaylardır (§11)."""
        body = {
            "tool": spec.name,
            "arguments": args.model_dump(mode="json"),
            "call_id": call_id,
        }
        self._events.emit(EventKind.TOOL_STARTED, __name__, body)
        started = self._events.monotonic()
        result = await execute(spec, args, self._context(spec, caller))
        self._events.emit(
            EventKind.TOOL_FINISHED,
            __name__,
            # Sonuç zarfının skill kısmı, yetki süzgecinden önce (§5.5).
            {**body, "result": dataclasses.asdict(result)},
            duration_s=self._events.monotonic() - started,
            status=result.status,
        )
        if self._ran is not None:
            await self._ran()
        shown = filter_records(result, caller, table)
        await self._show(spec, args.model_dump(mode="json"), shown)
        return shown

    async def _show(
        self, spec: ToolSpec[Any], arguments: Mapping[str, Any], result: ToolResult
    ) -> None:
        if self._shown is not None:
            await self._shown(spec, arguments, result)

    def _refused(
        self,
        spec: ToolSpec[Any],
        arguments: dict[str, Any],
        call_id: str | None,
        status: Status,
        error: str,
    ) -> ToolResult:
        """Gövdesi hiç çalışmayan çağrı da eylem geçmişindedir."""
        result = ToolResult(status, error=error)
        body = {
            "tool": spec.name,
            "arguments": arguments,
            "call_id": call_id,
            "result": dataclasses.asdict(result),
        }
        self._events.emit(EventKind.TOOL_FINISHED, __name__, body, status=status)
        return result
