"""Şimdiki hava durumu; yer söylenmezse çağıranın kendi varsayılan konumu (§11.1).

Kişi yalnızca kendi konumunu kullanabildiği için sonuç başkasının konumunu sızdırmaz; bu yüzden
hassasiyet `GENERAL`'dır ve misafir de bir şehrin havasını sorabilir (§10.2). Tanınmayanın
varsayılan konumu yoktur: model ona hangi yeri sorduğunu sorar.
"""

from typing import Any

from pydantic import BaseModel, Field

from mayen.ports.tools import (
    Effect,
    Sensitivity,
    SkillConfig,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
)
from mayen.ports.weather import WeatherError


class Args(BaseModel):
    place: str | None = Field(
        default=None,
        description="A city or place, as the user said it; omit to use the user's own default "
        "location",
    )


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    place = args.place or ctx.location
    if place is None:
        return ToolResult(Status.ERROR, error="no place given and no default location; ask")
    assert ctx.weather is not None  # yapılandırılmamışsa skill kataloğa girmez
    try:
        now = await ctx.weather.current(place)
    except WeatherError as e:
        return ToolResult(Status.ERROR, {"failure": e.failure.value}, error=str(e))
    return ToolResult(
        Status.OK,
        {
            "place": now.place,
            "default_location": args.place is None,
            "temperature_c": round(now.temperature_c),
            "feels_like_c": round(now.feels_like_c),
            "condition": now.condition,
            "humidity_percent": now.humidity_percent,
            "wind_m_s": round(now.wind_m_s, 1),
        },
    )


def spec(config: SkillConfig) -> ToolSpec[Any] | None:
    if not config.weather:
        return None
    return ToolSpec(
        name="weather",
        description="Tells the current weather of a place.",
        args=Args,
        effect=Effect.READ,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=True,  # yer adı sağlayıcıya gider
        timeout_s=10.0,
        run=run,
    )
