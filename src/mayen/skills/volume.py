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
    # Göreli istek ("kıs", "biraz aç") mutlak sayıya çevrilemez: model o anki seviyeyi bilmez.
    change: int | None = Field(
        default=None,
        ge=-100,
        le=100,
        description="Change from the current volume in percentage points, e.g. -10 for "
        "quieter; use this instead of level when the user asks for louder or quieter",
    )
    muted: bool | None = Field(default=None, description="Mute or unmute; omit to leave it")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if args.level is not None and args.change is not None:
        return ToolResult(Status.ERROR, error="give level or change, not both")
    if args.level is None and args.change is None and args.muted is None:
        return await ctx.device.run(Capability.SPEAKER, "get", {})
    data: dict[str, object] = {}
    level = args.level
    if args.change is not None:
        current = await ctx.device.run(Capability.SPEAKER, "get", {})
        if current.status is not Status.OK:
            return current
        level = min(100, max(0, int(current.data["level"]) + args.change))
    if level is not None:
        result = await ctx.device.run(Capability.SPEAKER, "set_volume", {"level": level})
        if result.status is not Status.OK:
            return result
        data["level"], data["previous_level"] = result.data["level"], result.data["previous"]
    if args.muted is not None:
        result = await ctx.device.run(Capability.SPEAKER, "set_muted", {"muted": args.muted})
        if result.status is not Status.OK:
            return ToolResult(result.status, data, error=result.error)
        data["muted"], data["previous_muted"] = result.data["muted"], result.data["previous"]
    # Değişen ses duyulur; zaten istenen hâldeyse bu, kişinin bilmediği bir şeydir (§7).
    changed = data.get("level") != data.get("previous_level") or data.get("muted") != data.get(
        "previous_muted"
    )
    return ToolResult(Status.OK, data, relay=not changed)


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
