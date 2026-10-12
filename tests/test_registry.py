"""Tool kayıt defteri ve argüman doğrulama (§9.1, §10.5 adım 1)."""

from typing import Literal

import pytest
from pydantic import BaseModel, Field

from mayen.core.registry import ToolRegistry, parse_args
from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class VolumeArgs(BaseModel):
    action: Literal["up", "down", "mute"] = Field(description="What to do with the volume.")
    step: int = Field(default=10, ge=1, le=100)


async def _run(args: VolumeArgs, ctx: ToolContext) -> ToolResult:
    return ToolResult(Status.OK, {"action": args.action})


def volume(name: str = "volume") -> ToolSpec[VolumeArgs]:
    return ToolSpec(
        name=name,
        description="Changes the speaker volume.",
        args=VolumeArgs,
        effect=Effect.EXTERNAL,
        sensitivity=Sensitivity.GENERAL,
        sends_outside=False,
        timeout_s=2.0,
        run=_run,
    )


def test_duplicate_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="volume"):
        ToolRegistry([volume(), volume()])


def test_catalog_shows_allowed_values() -> None:
    """Sabit listenin seçenekleri modele görünür (§9.1)."""
    (entry,) = ToolRegistry([volume()]).catalog()
    action = entry["parameters"]["properties"]["action"]
    assert action["enum"] == ["up", "down", "mute"]
    assert action["description"] == "What to do with the volume."


def test_registries_do_not_share_state() -> None:
    a = ToolRegistry([volume("a")])
    b = ToolRegistry([volume("b")])
    assert a.get("b") is None
    assert b.get("a") is None


def test_valid_args_are_parsed() -> None:
    args = parse_args(volume(), {"action": "down"})
    assert isinstance(args, VolumeArgs)
    assert args.step == 10


@pytest.mark.parametrize("raw", [{"action": "louder"}, {"action": "up", "step": 0}, {}])
def test_invalid_args_return_error_text(raw: dict[str, object]) -> None:
    assert isinstance(parse_args(volume(), raw), str)
