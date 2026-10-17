"""Oturumun cihazındaki medya oynatıcı: oynat, duraklat, sonraki, ne çalıyor (§9.7).

Oynatıcı verilmezse istemci çalanı seçer; seçemezse oynatıcıları listeleyerek hata döner ve
model kişiye sorar. Açık oynatıcı yoksa bir şey başlatılamaz: uygulama açmak bu tool'un işi
değildir.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, ToolContext, ToolResult, ToolSpec


class Action(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    TOGGLE = "toggle"
    NEXT = "next"
    PREVIOUS = "previous"
    STATUS = "status"


class Args(BaseModel):
    action: Action = Field(description="'status' lists the open players and what they play")
    player: str | None = Field(
        default=None,
        description="A player id from 'status'; omit to use the one that is playing",
    )


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    params = {} if args.player is None else {"player": args.player}
    return await ctx.device.run(Capability.MEDIA, args.action.value, params)


SPEC = ToolSpec(
    name="media",
    description="Controls the media players (music, video) on the device the user is talking "
    "to, or tells what they are playing.",
    args=Args,
    effect=Effect.EXTERNAL,
    sensitivity=Sensitivity.GENERAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
