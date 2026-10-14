"""Kişi profilinden çağırana ve modele giden bilgiye (§11.1, §10.2)."""

from mayen.ports.people import Person
from mayen.ports.tools import Caller, Role

# Rolü olmayan herkes; kendini kaydetmiş ama rolü verilmemiş kişi de (§10.2).
UNKNOWN = Caller(Role.UNKNOWN, None, has_personal_device=False)


def caller(person: Person | None) -> Caller:
    if person is None:
        return UNKNOWN
    return Caller(person.role, person.id, has_personal_device=bool(person.devices))


def speaker(person: Person) -> dict[str, str]:
    """Bağlama otomatik giren kısım: ad, rol, dil ve hitap. Yetki ayarları ve cihazlar
    modele hiç ulaşmaz (§11.1). Değerler verildiği dilde kalır, anahtarlar İngilizcedir."""
    facts = {"name": person.name, "role": person.role.value, "language": person.language}
    if person.address_as is not None:
        facts["address_as"] = person.address_as
    return facts
