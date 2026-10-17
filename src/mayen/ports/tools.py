"""Tool sözleşmesi (§9.1) ve yetki kararının sözlüğü (§10.2, §10.3)."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel

if TYPE_CHECKING:  # döngü: bu portlar `ports.tools`'un sözlüğünü kullanır
    from mayen.ports.devices import DeviceControl
    from mayen.ports.events import Clock
    from mayen.ports.notes import NoteStore
    from mayen.ports.timers import TimerStore


class Effect(StrEnum):
    """Tool'un yan etkisi; gizliliğe bakmaz (§9.1)."""

    READ = "READ"
    WRITE = "WRITE"
    EXTERNAL = "EXTERNAL"
    IRREVERSIBLE = "IRREVERSIBLE"
    DANGEROUS = "DANGEROUS"


class Sensitivity(StrEnum):
    GENERAL = "GENERAL"
    PERSONAL = "PERSONAL"


class Status(StrEnum):
    """Çağrının nasıl bittiği. Onay beklemek bir sonuç değil, turun durumudur (§5.4)."""

    OK = "ok"
    ERROR = "error"
    DENIED = "denied"
    UNSUPPORTED = "unsupported"  # oturumun cihazında bu yetenek yok (§9.7)
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    STARTED = "started"


class Role(StrEnum):
    OWNER = "owner"
    ACQUAINTANCE = "acquaintance"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class Verdict(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


class Confirmation(StrEnum):
    """Onay, kanala göre değil kanıtladığına göre adlanır (§10.3)."""

    INTENT = "intent"
    IDENTITY = "identity"


@dataclass(frozen=True)
class Caller:
    """Çağrıyı isteyen kişi. Kimlik onayı yalnızca kişisel cihazı olandan istenebilir."""

    role: Role
    person_id: str | None
    has_personal_device: bool


@dataclass(frozen=True)
class TurnFlags:
    """Oturum durumundaki işaretler (§8.1); sızdırma kuralı bunlara bakar (§10.3)."""

    personal_read: bool = False  # bu turda bir tool ile PERSONAL içerik okundu
    foreign_text: bool = False  # bağlamda başkasının yazdığı metin var (§10.6)


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    confirmation: Confirmation | None = None
    reason: str = ""


@dataclass(frozen=True)
class Record:
    """Kayıt tutan bir tool'un sonucundaki tek kayıt; hassasiyeti kendisindedir (§9.1)."""

    sensitivity: Sensitivity
    data: Mapping[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """Sonuç zarfının skill'in doldurduğu kısmı (§9.1)."""

    status: Status
    data: Mapping[str, Any] = field(default_factory=dict)
    records: Sequence[Record] = ()
    error: str | None = None
    withheld: int = 0  # okuma yetkisi olmadığı için sonuçtan çıkarılan kayıt sayısı


class ToolContext(Protocol):
    """Skill'e verilen bağlam: yalnızca depo portları taşır, veritabanı tutamacı asla (§9.1).

    Saat de buradadır: zamanı her modül ortak saatten alır (§5.5). Bağlam çağrı başınadır:
    çağıran kişi ve skill'in config'le birleşmiş varsayılanları çağrıdan çağrıya değişir.
    """

    @property
    def notes(self) -> "NoteStore": ...

    @property
    def timers(self) -> "TimerStore": ...

    @property
    def clock(self) -> "Clock": ...

    @property
    def device(self) -> "DeviceControl":
        """Oturumun cihazındaki istemci; makine denetimi oradan yapılır (§9.7)."""
        ...

    @property
    def caller(self) -> Caller:
        """Kaydın kime ait olduğu buradan yazılır; yetkiye çekirdek bakar, skill değil."""
        ...

    @property
    def defaults(self) -> Mapping[str, Any]:
        """`ToolSpec.defaults`, sahibin config'te üzerine yazdıklarıyla (§9.1)."""
        ...


@dataclass(frozen=True)
class ToolSpec[A: BaseModel]:
    """Bir skill'in tanımı; tanım, gövde ve politika sınıfı aynı dosyada durur (§9.1).

    Argümanlar bir Pydantic modelidir: doğrulama da, modele giden şema da ondan üretilir;
    sabit listeli bir argümanın seçenekleri böylece katalogda görünür.
    """

    name: str
    description: str
    args: type[A]
    effect: Effect
    sensitivity: Sensitivity  # kayıt tutan tool'da yeni kaydın varsayılanı
    sends_outside: bool  # zorunlu: unutulması sessiz bir sızıntı yolu açardı (§9.1)
    timeout_s: float
    run: Callable[[A, ToolContext], Awaitable[ToolResult]]
    defaults: Mapping[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False  # yalnızca onay ekler, hiç kaldırmaz (§10.3)
