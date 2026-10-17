"""Yetki kararı: tek zorlama noktası (§10.3)."""

from collections.abc import Collection, Mapping
from dataclasses import replace
from typing import Any

from mayen.ports.tools import (
    Caller,
    Confirmation,
    Decision,
    Effect,
    Role,
    Sensitivity,
    ToolResult,
    ToolSpec,
    TurnFlags,
    Verdict,
)

type Cell = tuple[Role, Effect, Sensitivity]
type PolicyTable = Mapping[Cell, bool]

_E = Effect
_S = Sensitivity

# §10.2'nin tablosu, hücre hücre yazılmış; üretilmiş bir matrisi test etmek üreticinin
# varsayımını test etmek olurdu (§10.3). `system` burada yok: yetkisi tetikleyici başına
# config'ten gelir ve tanımlanmamışsa yapılandırma hatasıdır (§10.2).
ROLE_TABLE: PolicyTable = {
    (Role.OWNER, _E.READ, _S.GENERAL): True,
    (Role.OWNER, _E.READ, _S.PERSONAL): True,
    (Role.OWNER, _E.WRITE, _S.GENERAL): True,
    (Role.OWNER, _E.WRITE, _S.PERSONAL): True,
    (Role.OWNER, _E.EXTERNAL, _S.GENERAL): True,
    (Role.OWNER, _E.EXTERNAL, _S.PERSONAL): True,
    (Role.OWNER, _E.IRREVERSIBLE, _S.GENERAL): True,
    (Role.OWNER, _E.IRREVERSIBLE, _S.PERSONAL): True,
    (Role.OWNER, _E.DANGEROUS, _S.GENERAL): True,
    (Role.OWNER, _E.DANGEROUS, _S.PERSONAL): True,
    (Role.ACQUAINTANCE, _E.READ, _S.GENERAL): True,
    (Role.ACQUAINTANCE, _E.READ, _S.PERSONAL): False,
    (Role.ACQUAINTANCE, _E.WRITE, _S.GENERAL): False,
    (Role.ACQUAINTANCE, _E.WRITE, _S.PERSONAL): False,
    (Role.ACQUAINTANCE, _E.EXTERNAL, _S.GENERAL): True,  # misafir (§10.2)
    (Role.ACQUAINTANCE, _E.EXTERNAL, _S.PERSONAL): False,
    (Role.ACQUAINTANCE, _E.IRREVERSIBLE, _S.GENERAL): False,
    (Role.ACQUAINTANCE, _E.IRREVERSIBLE, _S.PERSONAL): False,
    (Role.ACQUAINTANCE, _E.DANGEROUS, _S.GENERAL): False,
    (Role.ACQUAINTANCE, _E.DANGEROUS, _S.PERSONAL): False,
    (Role.UNKNOWN, _E.READ, _S.GENERAL): True,
    (Role.UNKNOWN, _E.READ, _S.PERSONAL): False,
    (Role.UNKNOWN, _E.WRITE, _S.GENERAL): False,
    (Role.UNKNOWN, _E.WRITE, _S.PERSONAL): False,
    (Role.UNKNOWN, _E.EXTERNAL, _S.GENERAL): True,  # misafir (§10.2)
    (Role.UNKNOWN, _E.EXTERNAL, _S.PERSONAL): False,
    (Role.UNKNOWN, _E.IRREVERSIBLE, _S.GENERAL): False,
    (Role.UNKNOWN, _E.IRREVERSIBLE, _S.PERSONAL): False,
    (Role.UNKNOWN, _E.DANGEROUS, _S.GENERAL): False,
    (Role.UNKNOWN, _E.DANGEROUS, _S.PERSONAL): False,
}


def system_table(allowed: Mapping[Effect, Collection[Sensitivity]]) -> PolicyTable:
    """Bir tetikleyici kaynağının açtığı turda `system` rolünün hücreleri (§10.2).

    Kaynağın yetkisi config'te tanımlı olmalıdır; tanımın içinde yazılmayan hücre kapalıdır.
    """
    return {(Role.SYSTEM, e, s): s in allowed.get(e, ()) for e in Effect for s in Sensitivity}


class MissingCellError(LookupError):
    """Politika tablosunda bir hücre yok; sessiz bir ret değil, hata (§10.3)."""


def permitted(table: PolicyTable, cell: Cell) -> bool:
    try:
        return table[cell]
    except KeyError:
        raise MissingCellError(cell) from None


def decide(
    spec: ToolSpec[Any], caller: Caller, table: PolicyTable, flags: TurnFlags
) -> Decision:
    """Bir çağrının kararı: izin, red ya da onay (§10.3)."""
    # Önce yetki: yetkisi olmayana onay sorulmaz, yoksa onay yetki vermenin yolu olurdu.
    if not permitted(table, (caller.role, spec.effect, spec.sensitivity)):
        return Decision(Verdict.DENY, reason="role not permitted")

    needed: Confirmation | None = None
    if spec.effect is Effect.IRREVERSIBLE or spec.requires_confirmation:
        needed = Confirmation.INTENT
    leak = spec.sends_outside and flags.personal_read and flags.foreign_text
    # Birden fazla tetikleyici onay isterse en güçlüsü istenir; kimlik niyeti de kanıtlar.
    if spec.effect is Effect.DANGEROUS or leak:
        needed = Confirmation.IDENTITY

    if needed is None:
        return Decision(Verdict.ALLOW)
    if needed is Confirmation.IDENTITY and not caller.has_personal_device:
        return Decision(Verdict.DENY, reason="identity confirmation needs a personal device")
    return Decision(Verdict.CONFIRM, needed)


def filter_records(result: ToolResult, caller: Caller, table: PolicyTable) -> ToolResult:
    """Okuma yetkisi olmayan kayıtları çıkarır, modele kaçının çıkarıldığını bildirir.

    Kayıt tutan tool'da hassasiyet kayıttadır (§9.1); çağrının izni kaydın kendisini okuma
    izni değildir. Okuma yetkisi aynı tablonun `READ` hücresidir, ayrı bir kural yoktur.
    """
    kept = [
        r for r in result.records if permitted(table, (caller.role, Effect.READ, r.sensitivity))
    ]
    withheld = len(result.records) - len(kept)
    if not withheld:
        return result
    return replace(result, records=kept, withheld=result.withheld + withheld)
