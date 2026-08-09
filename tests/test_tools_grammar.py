"""GBNF üretimi: iki aday biçim, tek defter (§8.3, §6).

Bu testler gramerin **yapısını** doğruluyor. "llama.cpp bu grameri kabul ediyor" iddiası
buradan çıkmaz ve çıkmamalı — kendi yazdığım bir doğrulayıcı, gramerin geçerliliğini değil
GBNF'i doğru anladığımı ölçerdi. O adım P7'de, gerçek koşucuyla atılıyor.
"""

from collections.abc import Mapping

import pytest

from mayen.policy.effects import Effect
from mayen.tools.catalog import builtin_registry
from mayen.tools.grammar import CALL_PREFIX, cli_grammar, json_grammar
from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult


async def _noop(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    return ToolResult(ok=True)


def rule(grammar: str, name: str) -> str:
    return next(line for line in grammar.splitlines() if line.startswith(f"{name} ::="))


@pytest.fixture(params=[cli_grammar, json_grammar], ids=["cli", "json"])
def grammar(request: pytest.FixtureRequest) -> str:
    """İki aday da aynı kurallara tabi: §19.1 kapanmadan biri ayrıcalıklı olamaz."""
    return str(request.param(builtin_registry()))


# --- her iki adayda ortak --------------------------------------------------------------


def test_branch_is_decidable_at_the_first_token(grammar: str) -> None:
    """C3 / §6: tool dalı zorunlu sabit önekle başlar, düz metin o karakterle başlayamaz."""
    assert rule(grammar, "root") == "root ::= tool-call | prose"
    assert rule(grammar, "tool-call").startswith(f'tool-call ::= "{CALL_PREFIX}"')
    assert rule(grammar, "prose").startswith("prose ::= [^<")


def test_tool_names_are_a_closed_list(grammar: str) -> None:
    registry = builtin_registry()
    branch = rule(grammar, "tool-call")
    for tool in registry:
        assert f"call-{tool.name.replace('_', '-')}" in branch
    assert branch.count("|") == len(registry) - 1


def test_every_tool_and_argument_is_reachable(grammar: str) -> None:
    for tool in builtin_registry():
        stem = tool.name.replace("_", "-")
        assert f"call-{stem} ::=" in grammar
        for arg in tool.args:
            assert arg.name in grammar


def test_empty_registry_is_an_error(grammar: str) -> None:
    with pytest.raises(ValueError):
        cli_grammar(Registry())
    with pytest.raises(ValueError):
        json_grammar(Registry())


# --- CLI'ye özgü (§8.3, A4) ------------------------------------------------------------


def test_cli_values_cannot_begin_with_a_flag() -> None:
    """Çok kelimeli değer bir sonraki bayrağı yutamaz: hiçbir kelime '--' ile başlamaz."""
    grammar = cli_grammar(builtin_registry())
    assert rule(grammar, "cli-word") == (
        'cli-word ::= [^ \\r\\n-] [^ \\r\\n]* | "-" [^ \\r\\n-] [^ \\r\\n]*'
    )


def test_cli_trailing_field_swallows_the_rest_of_the_line() -> None:
    """A4: son alanda hiçbir jeton bayrak sayılmaz."""
    grammar = cli_grammar(builtin_registry())
    assert rule(grammar, "cli-text") == "cli-text ::= [^\\r\\n]+"
    assert rule(grammar, "call-note-create") == (
        'call-note-create ::= "note_create" " --body " cli-text'
    )


def test_cli_optional_argument_is_optional() -> None:
    grammar = cli_grammar(builtin_registry())
    assert rule(grammar, "call-contact-get") == (
        'call-contact-get ::= "contact_get" (" --name " cli-string)?'
    )


# --- JSON'a özgü -----------------------------------------------------------------------


def test_json_optional_argument_does_not_leave_a_stray_comma() -> None:
    """İlk alanı atlanan bir çağrı, baştaki virgülle geçersiz JSON olurdu."""
    grammar = json_grammar(builtin_registry())
    assert rule(grammar, "args-contact-save-1") == (
        'args-contact-save-1 ::= ("\\"phone\\": " json-string more-contact-save-2)'
        " | args-contact-save-2"
    )
    assert rule(grammar, "more-contact-save-1") == (
        'more-contact-save-1 ::= (", " "\\"phone\\": " json-string more-contact-save-2)'
        " | more-contact-save-2"
    )


def test_json_required_argument_has_no_optional_branch() -> None:
    grammar = json_grammar(builtin_registry())
    assert rule(grammar, "args-note-create-0") == (
        'args-note-create-0 ::= "\\"body\\": " json-string more-note-create-1'
    )


def test_json_argument_object_can_be_empty() -> None:
    grammar = json_grammar(builtin_registry())
    assert rule(grammar, "args-date-time-0") == 'args-date-time-0 ::= ""'


# --- defter dışı bir tool da aynı kurallara uyar ---------------------------------------


def test_generation_follows_the_registry_not_a_hardcoded_list() -> None:
    registry = Registry()
    registry.register(
        Tool(
            name="only_tool",
            description="tek",
            effect=Effect.OKUMA,
            timeout_seconds=1.0,
            handler=_noop,
            args=(Arg("count", ArgType.INTEGER, "sayı"),),
        )
    )

    assert rule(cli_grammar(registry), "tool-call") == (
        f'tool-call ::= "{CALL_PREFIX}" (call-only-tool)'
    )
    assert rule(cli_grammar(registry), "call-only-tool") == (
        'call-only-tool ::= "only_tool" " --count " cli-integer'
    )
