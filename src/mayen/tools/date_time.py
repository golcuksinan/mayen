"""Tarih/saat (§9.2, OKUMA). Kaynak: sistem saati."""

from collections.abc import Mapping

from mayen.data import clock
from mayen.policy.effects import Effect
from mayen.tools.spec import Tool, ToolContext, ToolResult


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    stamp = clock.now()
    return ToolResult(ok=True, data={"utc": stamp}, speech=f"It is {stamp} UTC.")


TOOL = Tool(
    name="date_time",
    description="Şu anki tarih ve saati verir (UTC).",
    effect=Effect.OKUMA,
    timeout_seconds=1.0,
    handler=_run,
)
