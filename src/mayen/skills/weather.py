"""Şimdiki hava durumu; yer söylenmezse çağıranın kendi varsayılan konumu (§11.1).

Varsayılan, boş bırakılan bir argümanla değil açık bir seçimle istenir: model, varlığını
bilmediği bir varsayılana güvenip alanı boş bırakmaz, eldeki bir yer adını uydurur.

Kişi yalnızca kendi konumunu kullanabildiği için sonuç başkasının konumunu sızdırmaz; bu yüzden
hassasiyet `GENERAL`'dır ve misafir de bir şehrin havasını sorabilir (§10.2). Tanınmayanın
varsayılan konumu yoktur: model ona hangi yeri sorduğunu sorar.
"""

from enum import StrEnum
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


class Where(StrEnum):
    USER_DEFAULT = "user_default"
    NAMED = "named"


class Args(BaseModel):
    where: Where = Field(
        description="named: the user named a place; user_default: they named none, and their "
        "own default location is used"
    )
    place: str | None = Field(
        default=None,
        description="The place the user named, as they said it; only with where=named",
    )


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if args.where is Where.NAMED:
        if not args.place:
            return ToolResult(Status.ERROR, error="where=named but no place; ask")
        place: str = args.place
    elif ctx.location is None:
        return ToolResult(Status.ERROR, error="no default location; ask which place")
    else:
        place = ctx.location
    assert ctx.weather is not None  # yapılandırılmamışsa skill kataloğa girmez
    try:
        now = await ctx.weather.current(place)
    except WeatherError as e:
        return ToolResult(Status.ERROR, {"failure": e.failure.value}, error=str(e))
    return ToolResult(
        Status.OK,
        {
            "place": now.place,
            "default_location": args.where is Where.USER_DEFAULT,
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
