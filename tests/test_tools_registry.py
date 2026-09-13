"""Kayıt defteri ve tool tanımının kalıbı (§9.1)."""

from collections.abc import Mapping

import pytest

from mayen.policy.effects import Effect
from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, ToolSpecError


async def _noop(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    return ToolResult(ok=True, speech="tamam")


def _tool(name: str = "note", args: tuple[Arg, ...] = ()) -> Tool:
    return Tool(
        name=name,
        description="Not defteri",
        effect=Effect.YAZMA,
        timeout_seconds=2.0,
        handler=_noop,
        args=args,
    )


def test_trailing_arg_must_be_last() -> None:
    body = Arg("body", ArgType.STRING, "Not gövdesi", trailing=True)
    title = Arg("title", ArgType.STRING, "Başlık")
    with pytest.raises(ToolSpecError):
        _tool(args=(body, title))


def test_at_most_one_trailing_arg() -> None:
    first = Arg("body", ArgType.STRING, "Gövde", trailing=True)
    second = Arg("note", ArgType.STRING, "Not", trailing=True)
    with pytest.raises(ToolSpecError):
        _tool(args=(first, second))


def test_duplicate_argument_rejected() -> None:
    with pytest.raises(ToolSpecError):
        _tool(args=(Arg("x", ArgType.STRING, "a"), Arg("x", ArgType.INTEGER, "b")))


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ToolSpecError):
        Tool(
            name="note",
            description="Not",
            effect=Effect.OKUMA,
            timeout_seconds=0.0,
            handler=_noop,
        )


def test_usage_lists_signature_and_optional_marker() -> None:
    tool = _tool(
        args=(
            Arg("title", ArgType.STRING, "Başlık"),
            Arg("body", ArgType.STRING, "Gövde", required=False, trailing=True),
        )
    )
    usage = tool.usage()
    assert usage.splitlines()[0] == "note --title <string> [--body <string>]"
    assert "--title: Başlık" in usage
    assert "--body: Gövde (isteğe bağlı)" in usage


def test_duplicate_registration_rejected() -> None:
    registry = Registry()
    registry.register(_tool())
    with pytest.raises(ToolSpecError):
        registry.register(_tool())


def test_unknown_tool_raises() -> None:
    with pytest.raises(KeyError):
        Registry().get("yok")


def test_iteration_follows_registration_order() -> None:
    registry = Registry()
    registry.register(_tool("a"))
    registry.register(_tool("b"))
    assert [tool.name for tool in registry] == ["a", "b"]
    assert "a" in registry
    assert len(registry) == 2


# --- onay cümlesi (§8.5 adım 3) ---------------------------------------------------------


def _irreversible(confirm: str | None, args: tuple[Arg, ...] = ()) -> Tool:
    return Tool(
        name="wipe",
        description="Siler",
        effect=Effect.GERI_ALINAMAZ,
        timeout_seconds=2.0,
        handler=_noop,
        args=args,
        confirm=confirm,
    )


def test_an_irreversible_tool_without_a_question_is_rejected() -> None:
    """Cümlesiz gönderilseydi çalışma anında yine katalog açıklaması okunurdu."""
    with pytest.raises(ToolSpecError):
        _irreversible(None)


def test_a_tool_that_never_asks_may_not_carry_a_question() -> None:
    """Okunmayacak bir cümle, sessizce yalan söyleyen ikinci bir metindir."""
    with pytest.raises(ToolSpecError):
        Tool(
            name="note",
            description="Not",
            effect=Effect.YAZMA,
            timeout_seconds=2.0,
            handler=_noop,
            confirm="Save the note?",
        )


def test_the_question_may_only_name_required_arguments() -> None:
    """İsteğe bağlı alan yoksa cümle kurulamaz; hata tanım anında gelmeli."""
    optional = Arg("id", ArgType.INTEGER, "numara", required=False)
    with pytest.raises(ToolSpecError):
        _irreversible("Should I wipe {id}?", args=(optional,))


def test_the_question_is_built_from_validated_values() -> None:
    """Okunan cümle ile çalışacak çağrı aynı şey olmalı."""
    tool = _irreversible("Should I wipe note {id}?", args=(Arg("id", ArgType.INTEGER, "no"),))
    assert tool.confirmation(tool.validate({"id": "3"})) == "Should I wipe note 3?"
