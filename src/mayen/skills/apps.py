"""Oturumun cihazında uygulama açma (§9.4, §9.7): sahibin config'teki tablosundan.

Adlar katalogda sabit bir listedir (§9.1): model listedeki bir adı seçer, olmayan bir ad
yazamaz. Uygulama cihazdaki istemcide, sistemin kendi tanımıyla açılır. Tabloda hiç uygulama
yoksa tool kataloğa girmez: hiçbir şey açamayan bir tool, modele yapamayacağı bir şeyi vaat
ederdi. Kapatmak bu tool'un işi değildir.
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from mayen.ports.devices import Capability
from mayen.ports.tools import (
    Effect,
    Sensitivity,
    SkillConfig,
    ToolContext,
    ToolResult,
    ToolSpec,
)


def spec(tables: SkillConfig) -> ToolSpec[Any] | None:
    table: Mapping[str, str] = dict(tables.apps)
    if not table:
        return None
    names = tuple(sorted(table))
    args: type[BaseModel] = create_model(
        "Args",
        app=(Literal[names], Field(description="The app to open")),  # type: ignore[arg-type]
    )

    async def run(arguments: BaseModel, ctx: ToolContext) -> ToolResult:
        name = str(arguments.app)  # type: ignore[attr-defined]
        result = await ctx.device.run(
            Capability.APPS, "open", {"app": name, "entry": table[name]}
        )
        return replace(result, relay=False)  # açılan uygulama görünür (§7)

    return ToolSpec(
        name="apps",
        description="Opens an app (a program or a game) on the device the user is talking "
        "to. Names come through speech recognition and may be slightly off: choose the "
        "closest one in the list.",
        args=args,
        effect=Effect.EXTERNAL,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=False,
        timeout_s=10.0,
        run=run,
    )
