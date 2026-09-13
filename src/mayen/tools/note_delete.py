"""Notlar — sil (§9.2, GERİ_ALINAMAZ; onay ister)."""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, number


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    note_id = number(arguments, "id")
    if not context.notes.delete(note_id):
        return ToolResult(ok=False, error=f"{note_id}: böyle bir not yok")
    return ToolResult(ok=True, data={"id": note_id}, speech="Note deleted.")


TOOL = Tool(
    name="note_delete",
    description="Bir notu numarasıyla siler.",
    effect=Effect.GERI_ALINAMAZ,
    confirm="Should I delete note {id}?",
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("id", ArgType.INTEGER, "Silinecek notun numarası"),),
)
