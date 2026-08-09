"""§8.3'ün iki çağrı biçimi aynı iç temsili üretiyor mu."""

import pytest

from mayen.agent.calls import (
    CallFormat,
    CallParseError,
    ToolCall,
    UnknownArgumentError,
    UnknownToolError,
    is_call,
    parse,
)
from mayen.policy.effects import Effect
from mayen.tools.catalog import builtin_registry
from mayen.tools.grammar import CALL_PREFIX
from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult

FORMATS = [CallFormat.CLI, CallFormat.JSON]


@pytest.fixture
def registry() -> Registry:
    return builtin_registry()


async def _unused(context: ToolContext, arguments: object) -> ToolResult:
    raise AssertionError("ayrıştırıcı testi gövdeyi çağırmaz")


@pytest.fixture
def list_registry() -> Registry:
    """Yerleşik defterde `LIST` argümanlı tool yok; liste yolu kendi defteriyle ölçülür."""
    registry = Registry()
    registry.register(
        Tool(
            name="metrics",
            description="Ölçüt listesi alan bir tool.",
            effect=Effect.OKUMA,
            timeout_seconds=1.0,
            handler=_unused,
            args=(Arg("fields", ArgType.LIST, "Ölçüt adları"),),
        )
    )
    return registry


def test_prose_is_not_a_call() -> None:
    assert not is_call("Bugün hava güzel.")
    assert is_call(f"{CALL_PREFIX}date_time")


def test_prose_cannot_be_parsed(registry: Registry) -> None:
    with pytest.raises(CallParseError):
        parse(registry, CallFormat.CLI, "Bugün hava güzel.")


def test_no_argument_call(registry: Registry) -> None:
    assert parse(registry, CallFormat.CLI, f"{CALL_PREFIX}date_time") == ToolCall(
        "date_time", {}
    )
    assert parse(
        registry, CallFormat.JSON, f'{CALL_PREFIX}{{"name": "date_time", "arguments": {{}}}}'
    ) == ToolCall("date_time", {})


def test_both_formats_produce_the_same_call(registry: Registry) -> None:
    cli = parse(registry, CallFormat.CLI, f"{CALL_PREFIX}weather --city Denizli")
    payload = '{"name": "weather", "arguments": {"city": "Denizli"}}'
    js = parse(registry, CallFormat.JSON, CALL_PREFIX + payload)
    assert cli == js == ToolCall("weather", {"city": "Denizli"})


def test_multi_word_value_reads_until_next_flag(registry: Registry) -> None:
    call = parse(
        registry,
        CallFormat.CLI,
        f"{CALL_PREFIX}contact_save --name Ali Veli --phone 0555 111 22 33",
    )
    assert call.arguments == {"name": "Ali Veli", "phone": "0555 111 22 33"}


def test_trailing_field_swallows_flag_like_text(registry: Registry) -> None:
    call = parse(
        registry, CallFormat.CLI, f"{CALL_PREFIX}note_create --body süt --ekmek ve yumurta al"
    )
    assert call.arguments == {"body": "süt --ekmek ve yumurta al"}


def test_trailing_field_keeps_inner_spacing(registry: Registry) -> None:
    call = parse(registry, CallFormat.CLI, f"{CALL_PREFIX}note_create --body iki  boşluk")
    assert call.arguments == {"body": "iki  boşluk"}


@pytest.mark.parametrize("call_format", FORMATS)
def test_unknown_tool_is_its_own_error(registry: Registry, call_format: CallFormat) -> None:
    text = {
        CallFormat.CLI: f"{CALL_PREFIX}send_email --to Ali",
        CallFormat.JSON: f'{CALL_PREFIX}{{"name": "send_email", "arguments": {{"to": "Ali"}}}}',
    }[call_format]
    with pytest.raises(UnknownToolError):
        parse(registry, call_format, text)


@pytest.mark.parametrize("call_format", FORMATS)
def test_unknown_argument_is_its_own_error(registry: Registry, call_format: CallFormat) -> None:
    text = {
        CallFormat.CLI: f"{CALL_PREFIX}weather --city Denizli --units metric",
        CallFormat.JSON: (
            f'{CALL_PREFIX}{{"name": "weather", "arguments":'
            ' {"city": "Denizli", "units": "metric"}}'
        ),
    }[call_format]
    with pytest.raises(UnknownArgumentError):
        parse(registry, call_format, text)


def test_cli_rejects_repeated_flag(registry: Registry) -> None:
    with pytest.raises(CallParseError):
        parse(registry, CallFormat.CLI, f"{CALL_PREFIX}weather --city Ankara --city İzmir")


def test_cli_rejects_valueless_flag(registry: Registry) -> None:
    with pytest.raises(CallParseError):
        parse(registry, CallFormat.CLI, f"{CALL_PREFIX}weather --city")


def test_cli_rejects_token_where_a_flag_was_expected(registry: Registry) -> None:
    with pytest.raises(CallParseError):
        parse(registry, CallFormat.CLI, f"{CALL_PREFIX}date_time şimdi")


def test_json_integer_becomes_the_text_cli_would_write(registry: Registry) -> None:
    payload = '{"name": "note_delete", "arguments": {"id": 5}}'
    call = parse(registry, CallFormat.JSON, CALL_PREFIX + payload)
    assert call.arguments == {"id": "5"}
    assert registry.get("note_delete").validate(call.arguments) == {"id": 5}


def test_json_list_becomes_the_text_cli_would_write(list_registry: Registry) -> None:
    cli = parse(list_registry, CallFormat.CLI, f"{CALL_PREFIX}metrics --fields cpu,memory")
    payload = '{"name": "metrics", "arguments": {"fields": ["cpu", "memory"]}}'
    assert parse(list_registry, CallFormat.JSON, CALL_PREFIX + payload) == cli
    assert list_registry.get("metrics").validate(cli.arguments) == {"fields": ["cpu", "memory"]}


def test_json_list_item_with_comma_is_refused(list_registry: Registry) -> None:
    payload = '{"name": "metrics", "arguments": {"fields": ["cpu,memory"]}}'
    with pytest.raises(CallParseError):
        parse(list_registry, CallFormat.JSON, CALL_PREFIX + payload)


def test_json_rejects_broken_document(registry: Registry) -> None:
    with pytest.raises(CallParseError):
        parse(registry, CallFormat.JSON, f'{CALL_PREFIX}{{"name": "date_time"')


def test_json_rejects_extra_top_level_field(registry: Registry) -> None:
    payload = '{"name": "date_time", "arguments": {}, "id": "7"}'
    with pytest.raises(CallParseError):
        parse(registry, CallFormat.JSON, CALL_PREFIX + payload)
