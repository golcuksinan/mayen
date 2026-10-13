"""Şimdiki tarih ve saat, makinenin yerel saat diliminde."""

from pydantic import BaseModel

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class NoArgs(BaseModel):
    pass


async def run(_: NoArgs, ctx: ToolContext) -> ToolResult:
    # Dilim sistemden: ayrı bir ayar, sistem saatiyle ayrışabilecek ikinci bir gerçek olurdu.
    local = ctx.clock.now().astimezone()
    return ToolResult(Status.OK, {"time": local.strftime("%Y-%m-%d %H:%M, %A")})


SPEC = ToolSpec(
    name="time",
    description="Returns the current date and time.",
    args=NoArgs,
    effect=Effect.READ,
    sensitivity=Sensitivity.GENERAL,
    sends_outside=False,
    timeout_s=1.0,
    run=run,
)
