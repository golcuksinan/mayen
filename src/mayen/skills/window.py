"""Oturumun cihazındaki pencereler: listele, öne getir, küçült (§9.7).

Pencere numarası listeden gelir; numarayı istemci verir ve pencere açık kaldıkça değişmez.
Numara yoksa ya da bilinmiyorsa sonuç, açık pencerelerin listesiyle birlikte hatadır.
Kapatma geri alınamaz, bu yüzden ayrı tool'dur (`window_close`, §9.1). Pencere başlıkları
açık olan içeriği (sayfa, belge, ileti konusu) söyler; hassasiyet bu yüzden `PERSONAL`'dır.
"""

from dataclasses import replace
from enum import StrEnum

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, ToolContext, ToolResult, ToolSpec


class Action(StrEnum):
    LIST = "list"
    FOCUS = "focus"
    MINIMIZE = "minimize"


class Args(BaseModel):
    action: Action = Field(description="'list' tells the open windows and their numbers")
    window: int | None = Field(default=None, description="A window number from 'list'")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    # Numarasız ya da bilinmeyen numaralı istek, istemciden açık pencerelerin listesiyle döner.
    params = {} if args.window is None else {"window": args.window}
    result = await ctx.device.run(Capability.WINDOWS, args.action.value, params)
    # Öne gelen ya da küçülen pencere görünür; anlatılan yalnızca liste (§7).
    return replace(result, relay=args.action is Action.LIST)


SPEC = ToolSpec(
    name="window",
    description="Lists the windows on the device the user is talking to, brings one to the "
    "front or minimizes it.",
    args=Args,
    effect=Effect.EXTERNAL,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
