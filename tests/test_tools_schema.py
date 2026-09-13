"""Defterden JSON şema. `test_tools_grammar.py`'nin kardeşi: aynı defter, öbür biçim."""

from collections.abc import Mapping

import pytest

from mayen.policy.effects import Effect
from mayen.tools.registry import Registry
from mayen.tools.schema import schemas, tool_schema
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    return ToolResult(ok=True)


def _tool(*args: Arg, name: str = "ornek") -> Tool:
    return Tool(
        name=name,
        description="örnek tool",
        effect=Effect.OKUMA,
        timeout_seconds=1.0,
        handler=_run,
        args=args,
    )


def test_types_map_to_json_types() -> None:
    schema = tool_schema(
        _tool(
            Arg("city", ArgType.STRING, "şehir"),
            Arg("days", ArgType.INTEGER, "gün"),
            Arg("names", ArgType.LIST, "adlar"),
        )
    )
    props = schema["function"]["parameters"]["properties"]
    assert props["city"]["type"] == "string"
    assert props["days"]["type"] == "integer"
    assert props["names"] == {
        "type": "array",
        "items": {"type": "string"},
        "description": "adlar",
    }


def test_choices_become_an_enum() -> None:
    """Gramerdeki "geçersiz seçenek üretilemez" güvencesinin bu taraftaki karşılığı."""
    schema = tool_schema(_tool(Arg("action", ArgType.ENUM, "eylem", choices=("play", "pause"))))
    field = schema["function"]["parameters"]["properties"]["action"]
    assert field["enum"] == ["play", "pause"]


def test_only_required_arguments_are_required() -> None:
    schema = tool_schema(
        _tool(
            Arg("city", ArgType.STRING, "şehir"),
            Arg("days", ArgType.INTEGER, "gün", required=False),
        )
    )
    assert schema["function"]["parameters"]["required"] == ["city"]


def test_the_description_comes_from_the_definition() -> None:
    """Tek kaynak defter (§9.1): şema imzadan türetiliyor, yanına elle yazılmıyor."""
    schema = tool_schema(_tool(Arg("city", ArgType.STRING, "şehir adı")))
    assert schema["function"]["description"] == "örnek tool"
    assert schema["function"]["parameters"]["properties"]["city"]["description"] == "şehir adı"


def test_the_registry_order_is_kept() -> None:
    """İstek gövdesi öneğin parçası; sıranın koşudan koşuya değişmesi önbelleği düşürürdü."""
    registry = Registry()
    registry.register(_tool(name="bir"))
    registry.register(_tool(name="iki"))
    assert [s["function"]["name"] for s in schemas(registry)] == ["bir", "iki"]


def test_an_empty_registry_is_an_error() -> None:
    with pytest.raises(ValueError):
        schemas(Registry())
