"""Oturumun cihazında uygulama açma (§9.4, §9.7): sahibin o cihazdaki tablosundan.

Model bir komut yazmaz, tablodaki bir adı seçer; tablo cihazda durur ve ondan başka bir şey
açılamaz. Kapatmak bu tool'un işi değildir.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, ToolContext, ToolResult, ToolSpec


class Action(StrEnum):
    LIST = "list"
    OPEN = "open"


class Args(BaseModel):
    action: Action = Field(description="'list' tells which apps can be opened")
    app: str | None = Field(default=None, description="An app name from the list, for 'open'")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    params = {} if args.app is None else {"app": args.app}
    return await ctx.device.run(Capability.APPS, args.action.value, params)


SPEC = ToolSpec(
    name="apps",
    description="Opens an app (a program or a game) on the device the user is talking to, or "
    "lists the apps that can be opened there.",
    args=Args,
    effect=Effect.EXTERNAL,
    sensitivity=Sensitivity.GENERAL,
    sends_outside=False,
    timeout_s=10.0,
    run=run,
)
