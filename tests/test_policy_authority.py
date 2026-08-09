"""§10.2 matrisi testleri. §17.4: her (etki sınıfı × kademe) hücresi için **bir** test.

Hücreler parametrize edilmiş tek bir gövdeyle değil, on altı ayrı beklentiyle yazıldı;
beklenen kararı matrisin kendisinden okuyan bir test, matrisi değil kendini doğrular.
"""

import pytest

from mayen.data.repositories.people import Tier
from mayen.policy.authority import Authority, Decision, Identity, authority_of, authorize
from mayen.policy.effects import Effect

CELLS: list[tuple[Authority, Effect, Decision]] = [
    (Authority.SAHIP, Effect.OKUMA, Decision.IZIN_VAR),
    (Authority.SAHIP, Effect.YAZMA, Decision.IZIN_VAR),
    (Authority.SAHIP, Effect.DIS, Decision.IZIN_VAR),
    (Authority.SAHIP, Effect.GERI_ALINAMAZ, Decision.ONAY_GEREKLI),
    (Authority.KAYITLI_KISI, Effect.OKUMA, Decision.IZIN_VAR),
    (Authority.KAYITLI_KISI, Effect.YAZMA, Decision.RED),
    (Authority.KAYITLI_KISI, Effect.DIS, Decision.IZIN_VAR),
    (Authority.KAYITLI_KISI, Effect.GERI_ALINAMAZ, Decision.RED),
    (Authority.BEKLEYEN, Effect.OKUMA, Decision.RED),
    (Authority.BEKLEYEN, Effect.YAZMA, Decision.RED),
    (Authority.BEKLEYEN, Effect.DIS, Decision.RED),
    (Authority.BEKLEYEN, Effect.GERI_ALINAMAZ, Decision.RED),
    (Authority.TANINMAYAN, Effect.OKUMA, Decision.RED),
    (Authority.TANINMAYAN, Effect.YAZMA, Decision.RED),
    (Authority.TANINMAYAN, Effect.DIS, Decision.RED),
    (Authority.TANINMAYAN, Effect.GERI_ALINAMAZ, Decision.RED),
]


@pytest.mark.parametrize(("authority", "effect", "expected"), CELLS)
def test_matrix_cell(authority: Authority, effect: Effect, expected: Decision) -> None:
    assert authorize(Identity(authority), effect) is expected


def test_matrix_covers_every_cell() -> None:
    # Eksik hücre "izin yok" değil, KeyError'dır — ama önce hiç eksik olmasın.
    assert len(CELLS) == len(Authority) * len(Effect) == 16


def test_unknown_person_has_no_tier() -> None:
    assert authority_of(None) is Authority.TANINMAYAN


@pytest.mark.parametrize("tier", list(Tier))
def test_every_stored_tier_maps_to_an_authority(tier: Tier) -> None:
    assert authority_of(tier).value == tier.value


def test_owner_still_needs_approval_for_irreversible() -> None:
    # Sahiplik onayı kaldırmaz (§10.2): onay yetki sorusu değil, niyet sorusudur.
    assert authorize(Identity(Authority.SAHIP), Effect.GERI_ALINAMAZ) is Decision.ONAY_GEREKLI


def test_person_id_does_not_change_the_decision() -> None:
    # Karar yalnızca kademeden çıkar; kişi kimliği yalnızca iz için taşınır.
    assert authorize(Identity(Authority.BEKLEYEN, person_id=7), Effect.OKUMA) is Decision.RED
