"""Notlar — ara/listele (§9.2, OKUMA)."""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, optional_text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    query = optional_text(arguments, "query")
    notes = context.notes.list_all() if query is None else context.notes.search(query)
    if not notes:
        return ToolResult(ok=True, data={"notes": []}, speech="No matching note.")
    return ToolResult(
        ok=True,
        data={"notes": [{"id": note.id, "body": note.body} for note in notes]},
        speech="; ".join(f"{note.id}: {note.body}" for note in notes),
    )


TOOL = Tool(
    name="note_search",
    description="Notları listeler; arama metni verilirse içinde geçenleri döndürür.",
    effect=Effect.OKUMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("query", ArgType.STRING, "Aranacak metin", required=False, trailing=True),),
)
