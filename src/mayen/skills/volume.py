"""Oturumun cihazında hoparlörün ses seviyesi ve sessizliği (§9.7).

Tek tool, isteğe bağlı alanlar: ayrı bir okuma tool'u kataloğu büyütür ve modele "oku mu yaz
mı" diye ikinci bir seçim ekler. Alan verilmezse durum okunur. Etki `EXTERNAL`'dır, okuma için
de: etki sınıfı tool'un yapabildiği en güçlü şeydir (§9.1).
"""

from pydantic import BaseModel, Field

from mayen.ports.devices import Capability
from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class Args(BaseModel):
    # Aralık şemada: %5000 bir yazım hatası değil, duyulur bir kazadır.
    level: int | None = Field(
        default=None, ge=0, le=100, description="Volume in percent; omit to leave it as is"
    )
    muted: bool | None = Field(default=None, description="Mute or unmute; omit to leave it")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if args.level is None and args.muted is None:
        return await ctx.device.run(Capability.SPEAKER, "get", {})
    data: dict[str, object] = {}
    if args.level is not None:
        result = await ctx.device.run(Capability.SPEAKER, "set_volume", {"level": args.level})
        if result.status is not Status.OK:
            return result
        data["level"], data["previous_level"] = result.data["level"], result.data["previous"]
    if args.muted is not None:
        result = await ctx.device.run(Capability.SPEAKER, "set_muted", {"muted": args.muted})
        if result.status is not Status.OK:
            return ToolResult(result.status, data, error=result.error)
        data["muted"], data["previous_muted"] = result.data["muted"], result.data["previous"]
    return ToolResult(Status.OK, data)


SPEC = ToolSpec(
    name="volume",
    description="Reads or sets the speaker volume and mute on the device the user is talking "
    "to. With no arguments it reads them.",
    args=Args,
    effect=Effect.EXTERNAL,
    sensitivity=Sensitivity.GENERAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
