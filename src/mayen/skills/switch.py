"""Evdeki bir anahtarı açma ya da kapatma (§9.5): akıllı priz ve ona takılı olan.

Adlar sahibin config'teki tablosundan, katalogda sabit bir listedir (§9.1); prize takılan
değişince yalnızca ad değişir. `ok`, anahtar yeniden okunup istenen durumda görülünce döner
(§9.1). Durumu okumak ayrı tool'dur (`switch_state`): etki sınıfı farklıdır.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from mayen.ports.switches import SwitchError
from mayen.ports.tools import (
    Effect,
    Sensitivity,
    SkillConfig,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
)


def spec(config: SkillConfig) -> ToolSpec[Any] | None:
    if not config.switches:
        return None
    names = tuple(sorted(config.switches))
    args: type[BaseModel] = create_model(
        "Args",
        switch=(Literal[names], Field(description="The switch, by its name")),  # type: ignore[arg-type]
        on=(bool, Field(description="true turns it on, false turns it off")),
    )

    async def run(arguments: BaseModel, ctx: ToolContext) -> ToolResult:
        name = str(arguments.switch)  # type: ignore[attr-defined]
        wanted = bool(arguments.on)  # type: ignore[attr-defined]
        assert ctx.switches is not None  # yapılandırılmamışsa skill kataloğa girmez
        try:
            await ctx.switches.set(name, wanted)
            seen = await ctx.switches.is_on(name)
        except SwitchError as e:
            return ToolResult(Status.ERROR, {"failure": e.failure.value}, error=str(e))
        data = {"switch": name, "on": seen}
        if seen != wanted:
            return ToolResult(Status.ERROR, data, error="the switch did not change")
        return ToolResult(Status.OK, data, relay=False)  # sonuç etkinin kendisi (§7)

    return ToolSpec(
        name="switch",
        description="Turns a switch at home (a smart plug and whatever is plugged into "
        "it) on or off. Names come through speech recognition and may be slightly off: "
        "choose the closest one in the list.",
        args=args,
        effect=Effect.EXTERNAL,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=False,  # istek ev ağında kalır
        timeout_s=10.0,
        run=run,
    )
