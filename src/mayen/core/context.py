"""Bağlam bloğu (§8.3, §8.6, §11.1): turun değişken içeriği, öneğin sonunda.

Blok her model isteğinde yeniden kurulur ve geçmişe yazılmaz; sistem promptu hiç değişmez.
Modele giden metin İngilizcedir; kişinin verisi (ad, hitap) verildiği dilde kalır.
"""

import json
from datetime import datetime

from mayen.core.presence import Presence
from mayen.core.profile import speaker
from mayen.ports.events import Clock
from mayen.ports.people import PersonStore
from mayen.ports.tools import Caller

# Dil kuralı metnindeki yer tutucu; kuralın kendisi sahibin prompt dosyasındadır.
LANGUAGE_SLOT = "{language}"

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def when(moment: datetime) -> str:
    """Ay adıyla (§8.3): gün ve ay sayıyla yazılınca model ikisini karıştırabilir.

    Adlar yerel ayardan alınmaz; modele giden metin her makinede İngilizcedir (§8.6).
    """
    local = moment.astimezone()
    month = _MONTHS[local.month - 1]
    return f"{_WEEKDAYS[local.weekday()]}, {local.day} {month} {local.year}, {local:%H:%M}"


class ContextBlock:
    """Bir oturumun bağlam bloğu: tarih/saat, konuşan kişi ve en sonda dil kuralı (§8.6)."""

    def __init__(
        self,
        people: PersonStore,
        presence: Presence,
        clock: Clock,
        language_rule: str,
        default_language: str,
    ) -> None:
        self._people = people
        self._presence = presence
        self._clock = clock
        self._rule = language_rule
        self._default = default_language  # tanınmayan kişinin çıkış dili (§8.6)

    def language(self, session: str, requester: Caller) -> str:
        """Turu isteyen kişinin dili; kimse istemediyse (zamanlayıcı) oturumun cihazının
        kişisi dinleyendir. İkisi de yoksa config'teki varsayılan."""
        person_id = requester.person_id or self._presence.personal(session)
        person = None if person_id is None else self._people.get(person_id)
        return self._default if person is None else person.language

    def render(self, session: str, requester: Caller) -> str:
        person = None if requester.person_id is None else self._people.get(requester.person_id)
        # Tanınmayan ya da kimse olmayan (system) çağıranın modele giden tek bilgisi rolüdür.
        facts = {"role": requester.role.value} if person is None else speaker(person)
        rule = self._rule.replace(LANGUAGE_SLOT, self.language(session, requester))
        return "\n".join(
            [
                "[context]",
                f"date/time: {when(self._clock.now())}",
                f"speaker: {json.dumps(facts, ensure_ascii=False)}",
                rule.strip(),
            ]
        )
