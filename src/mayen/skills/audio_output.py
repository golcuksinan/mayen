"""Oturumun cihazında sesin çıktığı cihaz: hoparlör, kulaklık (§9.7).

Argüman verilmezse çıkışları listeler; model `id`'yi listeden alır. Ad yerine kimlik: cihazın
görünen adı makineden makineye ve dilden dile değişir, kimlik değişmez.
"""

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    output: str | None = Field(
        default=None,
        description="The id of the output to switch to, from the list; omit to list them",
    )


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if args.output is None:
        return await ctx.device.run(Capability.SPEAKER, "list_outputs", {})
    return await ctx.device.run(Capability.SPEAKER, "set_output", {"output": args.output})


SPEC = ToolSpec(
    name="audio_output",
    description="Lists the audio outputs (speakers, headphones) of the device the user is "
    "talking to, or switches the sound to one of them.",
    args=Args,
    effect=Effect.EXTERNAL,
    sensitivity=Sensitivity.GENERAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
