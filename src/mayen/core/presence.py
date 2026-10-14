"""Bağlı oturumlar ve hatırlatmanın hedefi (§12, §7).

Hedef, içeriğin ait olduğu kişinin en son etkileşimde bulunduğu cihazdır; Mayen'in genelinde
son kullanılan cihaz başka birinin olabilir. `PERSONAL` içerik yalnızca kişinin kendi
cihazına gider (§7). Uygun oturum yoksa hedef yoktur ve içerik bekler.
"""

from mayen.ports.people import DeviceId
from mayen.ports.tools import Sensitivity


class Presence:
    def __init__(self) -> None:
        # Oturum → cihazın eşleştirildiği kişi (ortak cihazsa `None`); bağlanma sırasıyla.
        self._sessions: dict[str, str | None] = {}
        self._last: dict[str, str] = {}  # kişi → en son etkileşimde bulunduğu oturum

    def connected(self, session: str, device: DeviceId | None, owner: str | None) -> None:
        """`owner`, cihazın kişisel cihazı olduğu kişidir; cihaz doğrulanmadıysa `None`."""
        if device is None and owner is not None:
            raise ValueError("an unverified connection is nobody's personal device")
        self._sessions[session] = owner

    def disconnected(self, session: str) -> None:
        self._sessions.pop(session, None)

    def personal(self, session: str) -> str | None:
        """Oturum bir kişinin kişisel cihazındaysa o kişi."""
        return self._sessions.get(session)

    def interacted(self, person_id: str, session: str) -> None:
        if session in self._sessions:
            self._last[person_id] = session

    def target(self, person_id: str | None, sensitivity: Sensitivity) -> str | None:
        if person_id is None:
            return None
        last = self._last.get(person_id)
        if last in self._sessions and (
            sensitivity is Sensitivity.GENERAL or self._sessions[last] == person_id
        ):
            return last
        own = [s for s, owner in self._sessions.items() if owner == person_id]
        return own[-1] if own else None  # en son bağlanan kişisel cihaz
