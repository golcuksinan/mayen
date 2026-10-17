"""Oturumun cihazında bir pencereyi kapatır; geri alınamaz, niyet onayı ister (§9.1, §10.3).

Numaranın yanında uygulama da istenir: onay cümlesi plandaki her değeri okur (§10.5), kişi
yalnızca bir numara duysaydı hangi pencerenin kapanacağını bilemezdi. İstemci ikisi aynı
pencereyi göstermiyorsa kapatmaz; tahmin edilmiş bir numara başka bir pencereyi kapatamaz.
"""

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    window: int = Field(description="A window number from the window tool's 'list'")
    app: str = Field(description="That window's app, exactly as 'list' gave it")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    return await ctx.device.run(
        Capability.WINDOWS, "close", {"window": args.window, "app": args.app}
    )


SPEC = ToolSpec(
    name="window_close",
    # Küçültmenin yeri açıklamada yazmazsa model "küçült" isteğini de bu tool'a getiriyor.
    description="Closes a window for good, by its number, on the device the user is talking "
    "to; minimizing or bringing one to the front is the window tool.",
    args=Args,
    effect=Effect.IRREVERSIBLE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
