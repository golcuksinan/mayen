"""Bir notu numarasıyla kalıcı olarak siler."""

from pydantic import BaseModel, Field

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    id: str = Field(description="The number of the note to delete")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if not ctx.notes.delete(args.id):
        return ToolResult(Status.ERROR, error=f"note {args.id} does not exist")
    return ToolResult(Status.OK, {"deleted": args.id})


SPEC = ToolSpec(
    name="note_delete",
    description="Permanently deletes a note by its number.",
    args=Args,
    effect=Effect.IRREVERSIBLE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
