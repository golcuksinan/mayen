"""Evdeki bir anahtarın açık mı kapalı mı olduğu (§9.5); durum cihazdan okunur.

Adlar `switch` ile aynı tablodan, katalogda sabit bir listedir (§9.1).
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
    )

    async def run(arguments: BaseModel, ctx: ToolContext) -> ToolResult:
        name = str(arguments.switch)  # type: ignore[attr-defined]
        assert ctx.switches is not None  # yapılandırılmamışsa skill kataloğa girmez
        try:
            on = await ctx.switches.is_on(name)
        except SwitchError as e:
            return ToolResult(Status.ERROR, {"failure": e.failure.value}, error=str(e))
        return ToolResult(Status.OK, {"switch": name, "on": on})

    return ToolSpec(
        name="switch_state",
        description="Tells whether a switch at home (a smart plug and whatever is plugged "
        "into it) is on or off. Names come through speech recognition and may be slightly "
        "off: choose the closest one in the list.",
        args=args,
        effect=Effect.READ,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=False,
        timeout_s=10.0,
        run=run,
    )
