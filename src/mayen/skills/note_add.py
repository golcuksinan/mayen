"""Yeni bir not kaydeder."""

from pydantic import BaseModel, Field

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    text: str = Field(description="The note's content, in the user's own words")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    note = ctx.notes.add(args.text, SPEC.sensitivity)
    return ToolResult(Status.OK, {"id": note.id})


SPEC = ToolSpec(
    name="note_add",
    description="Saves a new note.",
    args=Args,
    effect=Effect.WRITE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
