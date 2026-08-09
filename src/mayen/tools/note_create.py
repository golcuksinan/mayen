"""Notlar — oluştur (§9.2, YAZMA). Gövde serbest metindir, o yüzden imzada en sonda (§8.3)."""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    note = context.notes.create(text(arguments, "body"))
    return ToolResult(ok=True, data={"id": note.id, "body": note.body}, speech="Note saved.")


TOOL = Tool(
    name="note_create",
    description="Yeni bir not kaydeder.",
    effect=Effect.YAZMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("body", ArgType.STRING, "Notun metni", trailing=True),),
)
