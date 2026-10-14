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
        self._malformed: set[str] = set()  # argümanı doğrulanamayan çağrılar (§9.1)

    def schema(self) -> ToolsSchema:
        functions = []
        for spec in self._registry.specs():
            params = spec.args.model_json_schema()
            functions.append(
                FunctionSchema(
                    name=spec.name,
                    description=spec.description,
                    properties=params.get("properties", {}),
                    required=params.get("required", []),
                )
            )
        return ToolsSchema(standard_tools=functions)

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
        """Tek bir çağrı: doğrula, karar ver, uygula. Pipecat'siz test edilebilsin diye ayrı."""
        args = parse_args(spec, raw)
        if isinstance(args, str):
            if call_id is not None:
                self._malformed.add(call_id)
            return to_model(self._refused(spec, dict(raw), Status.ERROR, args)), None

        caller = self._caller()
        table = self._table()
        decision = decide(spec, caller, table, self._flags())
        if decision.verdict is Verdict.DENY:
            arguments = args.model_dump(mode="json")
            return to_model(
                self._refused(spec, arguments, Status.DENIED, decision.reason)
            ), None

        if decision.verdict is Verdict.CONFIRM:
            assert decision.confirmation is not None

            async def run_confirmed() -> ToolResult:
                return await self._run(spec, args, caller, table)

            await self._gate.request(spec, args, decision.confirmation, run_confirmed, caller)
            # Model burada konuşmaz; soruyu kapı plandan yazdırıp okutur (§10.5).
            return {"status": AWAITING_CONFIRMATION}, FunctionCallResultProperties(
                run_llm=False
            )

        return to_model(await self._run(spec, args, caller, table)), None

    async def _run(
        self, spec: ToolSpec[Any], args: BaseModel, caller: Caller, table: PolicyTable
    ) -> ToolResult:
        """Gövdenin çalışması olay kaydına girer; eylem geçmişi bu olaylardır (§11)."""
        body = {"tool": spec.name, "arguments": args.model_dump(mode="json")}
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
        return filter_records(result, caller, table)

    def _refused(
        self, spec: ToolSpec[Any], arguments: dict[str, Any], status: Status, error: str
    ) -> ToolResult:
        """Gövdesi hiç çalışmayan çağrı da eylem geçmişindedir."""
        result = ToolResult(status, error=error)
        body = {"tool": spec.name, "arguments": arguments, "result": dataclasses.asdict(result)}
        self._events.emit(EventKind.TOOL_FINISHED, __name__, body, status=status)
        return result
