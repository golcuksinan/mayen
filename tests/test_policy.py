"""Yetki kararı (§10.3) ve kayıt süzgeci (§9.1)."""

import itertools

import pytest
from pydantic import BaseModel

from mayen.core.policy import ROLE_TABLE, MissingCellError, decide, filter_records
from mayen.ports.tools import (
    Caller,
    Confirmation,
    Effect,
    Record,
    Role,
    Sensitivity,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
    TurnFlags,
    Verdict,
)

OWNER = Caller(Role.OWNER, "p1", has_personal_device=True)
OWNER_NO_DEVICE = Caller(Role.OWNER, "p1", has_personal_device=False)
GUEST = Caller(Role.ACQUAINTANCE, "p2", has_personal_device=True)
CLEAN = TurnFlags()


class NoArgs(BaseModel):
    pass


async def _run(args: NoArgs, ctx: ToolContext) -> ToolResult:
    return ToolResult(Status.OK)


def spec(
    effect: Effect = Effect.READ,
    sensitivity: Sensitivity = Sensitivity.GENERAL,
    *,
    sends_outside: bool = False,
    requires_confirmation: bool = False,
) -> ToolSpec[NoArgs]:
    return ToolSpec(
        name="t",
        description="test tool",
        args=NoArgs,
        effect=effect,
        sensitivity=sensitivity,
        sends_outside=sends_outside,
        timeout_s=1.0,
        run=_run,
        requires_confirmation=requires_confirmation,
    )


# §10.2: sahip her şeye yetkili; tanıdık ve tanımsız yalnızca READ·GENERAL.
CELLS = list(
    itertools.product((Role.OWNER, Role.ACQUAINTANCE, Role.UNKNOWN), Effect, Sensitivity)
)


@pytest.mark.parametrize(("role", "effect", "sensitivity"), CELLS)
def test_role_table_cell(role: Role, effect: Effect, sensitivity: Sensitivity) -> None:
    expected = role is Role.OWNER or (
        effect is Effect.READ and sensitivity is Sensitivity.GENERAL
    )
    assert ROLE_TABLE[(role, effect, sensitivity)] is expected


def test_table_has_exactly_the_written_cells() -> None:
    assert set(ROLE_TABLE) == set(CELLS)


def test_system_role_without_config_is_an_error() -> None:
    caller = Caller(Role.SYSTEM, None, has_personal_device=False)
    with pytest.raises(MissingCellError):
        decide(spec(), caller, ROLE_TABLE, CLEAN)


def test_denied_role_is_not_asked_for_confirmation() -> None:
    d = decide(spec(Effect.IRREVERSIBLE), GUEST, ROLE_TABLE, CLEAN)
    assert d.verdict is Verdict.DENY
    assert d.confirmation is None


@pytest.mark.parametrize("effect", [Effect.READ, Effect.WRITE, Effect.EXTERNAL])
def test_reversible_effects_are_allowed(effect: Effect) -> None:
    assert decide(spec(effect), OWNER, ROLE_TABLE, CLEAN).verdict is Verdict.ALLOW


def test_irreversible_needs_intent() -> None:
    d = decide(spec(Effect.IRREVERSIBLE), OWNER, ROLE_TABLE, CLEAN)
    assert (d.verdict, d.confirmation) == (Verdict.CONFIRM, Confirmation.INTENT)


def test_irreversible_needs_no_personal_device() -> None:
    d = decide(spec(Effect.IRREVERSIBLE), OWNER_NO_DEVICE, ROLE_TABLE, CLEAN)
    assert d.verdict is Verdict.CONFIRM


def test_dangerous_needs_identity() -> None:
    d = decide(spec(Effect.DANGEROUS), OWNER, ROLE_TABLE, CLEAN)
    assert (d.verdict, d.confirmation) == (Verdict.CONFIRM, Confirmation.IDENTITY)


def test_identity_without_personal_device_is_denied() -> None:
    assert (
        decide(spec(Effect.DANGEROUS), OWNER_NO_DEVICE, ROLE_TABLE, CLEAN).verdict
        is Verdict.DENY
    )


def test_flag_adds_intent() -> None:
    d = decide(spec(requires_confirmation=True), OWNER, ROLE_TABLE, CLEAN)
    assert (d.verdict, d.confirmation) == (Verdict.CONFIRM, Confirmation.INTENT)


def test_flag_never_removes_confirmation() -> None:
    d = decide(spec(Effect.DANGEROUS, requires_confirmation=True), OWNER, ROLE_TABLE, CLEAN)
    assert d.confirmation is Confirmation.IDENTITY


@pytest.mark.parametrize(
    ("personal_read", "foreign_text", "sends_outside", "expected"),
    [
        (True, True, True, Verdict.CONFIRM),
        (True, True, False, Verdict.ALLOW),
        (True, False, True, Verdict.ALLOW),
        (False, True, True, Verdict.ALLOW),
    ],
)
def test_leak_rule(
    personal_read: bool, foreign_text: bool, sends_outside: bool, expected: Verdict
) -> None:
    flags = TurnFlags(personal_read=personal_read, foreign_text=foreign_text)
    d = decide(spec(sends_outside=sends_outside), OWNER, ROLE_TABLE, flags)
    assert d.verdict is expected
    if expected is Verdict.CONFIRM:
        assert d.confirmation is Confirmation.IDENTITY


def test_leak_outranks_intent() -> None:
    flags = TurnFlags(personal_read=True, foreign_text=True)
    d = decide(spec(Effect.IRREVERSIBLE, sends_outside=True), OWNER, ROLE_TABLE, flags)
    assert d.confirmation is Confirmation.IDENTITY


def _records() -> ToolResult:
    return ToolResult(
        Status.OK,
        records=[
            Record(Sensitivity.GENERAL, {"body": "çöpü çıkar"}),
            Record(Sensitivity.PERSONAL, {"body": "tahlil sonucu"}),
            Record(Sensitivity.PERSONAL, {"body": "doktor randevusu"}),
        ],
    )


def test_guest_sees_only_general_records() -> None:
    out = filter_records(_records(), GUEST, ROLE_TABLE)
    assert [r.data["body"] for r in out.records] == ["çöpü çıkar"]
    assert out.withheld == 2


def test_owner_sees_every_record() -> None:
    result = _records()
    assert filter_records(result, OWNER, ROLE_TABLE) is result
