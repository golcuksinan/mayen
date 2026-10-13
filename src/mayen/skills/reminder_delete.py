"""Henüz çalmamış bir hatırlatmayı numarasıyla kalıcı olarak siler."""

from pydantic import BaseModel, Field

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    id: str = Field(description="The number of the reminder to delete")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if not ctx.timers.delete(args.id):
        return ToolResult(Status.ERROR, error=f"no pending reminder {args.id}")
    return ToolResult(Status.OK, {"deleted": args.id})


SPEC = ToolSpec(
    name="reminder_delete",
    description="Permanently deletes a reminder that has not gone off yet, by its number.",
    args=Args,
    effect=Effect.IRREVERSIBLE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
