"""Oturumun cihazında bir pencereyi kapatır; geri alınamaz, niyet onayı ister (§9.1, §10.3)."""

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    window: int = Field(description="A window number from the window tool's 'list'")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    return await ctx.device.run(Capability.WINDOWS, "close", {"window": args.window})


SPEC = ToolSpec(
    name="window_close",
    description="Closes a window by its number on the device the user is talking to.",
    args=Args,
    effect=Effect.IRREVERSIBLE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
