"""Kişi profili portu (§11.1, §10.2): kişiler, rolleri ve eşleştirilmiş cihazları."""

from dataclasses import dataclass
from typing import NewType, Protocol

from mayen.ports.tools import Role

# Taşımanın doğruladığı cihaz kimliği (§10.1); istemcinin beyanı hiçbir zaman buraya girmez.
DeviceId = NewType("DeviceId", str)

# Çekirdeğin kendi makinesine bağlı ses birimleri; hiçbir bağlantıya verilmez. Geliştirme
# istisnası: mimaride bu cihaz ortaktır (önünde kimin olduğunu kanıtlamaz, §10.1). Sahibe
# eşleştirilmesi yalnızca tailnet'ten bağlanan bir kişisel istemci yokken işi kolaylaştırır.
LOCAL_DEVICE = DeviceId("local")


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    role: Role
    language: str  # çıkış dili tercihi (§8.6)
    address_as: str | None  # hitap tercihi; yoksa model kendi seçer
    devices: tuple[DeviceId, ...]  # kişisel cihazları: her cihaz en çok bir kişiye eşleşir


class OwnerExistsError(Exception):
    """Sahip zaten tanımlı; ikinci bir sahip atanamaz (§10.2)."""


class DevicePairedError(Exception):
    """Cihaz başka bir kişiye eşleştirilmiş; iki kişinin cihazı kişisel değildir (§10.1)."""


class PersonStore(Protocol):
    def create_owner(
        self, name: str, language: str, address_as: str | None, devices: tuple[DeviceId, ...]
    ) -> Person:
        """Sahibi kurar; sahip varsa `OwnerExistsError`. Yalnızca kurulum komutu çağırır."""
        ...

    def owner(self) -> Person | None: ...

    def get(self, person_id: str) -> Person | None: ...

    def by_device(self, device: DeviceId) -> Person | None:
        """Cihazın eşleştirildiği kişi; eşleşmemişse ortak cihazdır ve `None` döner."""
        ...
