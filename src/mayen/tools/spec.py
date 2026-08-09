"""Tool tanımı: şema, sonuç biçimi ve bağlam nesnesi (§9.1).

Bir tool = bir dosya: şema, gövde ve politika sınıfı (etki) aynı yerde durur (Kural 9).
Burada duran, o dosyaların doldurduğu kalıp.

**Kullanım metni üretilir, ayrıca yazılmaz.** §9.1 tool'un `--help` çıktısını bildirmesini
ister; ama metni imzadan ayrı bir alanda ikinci kez yazmak, imza değiştiğinde sessizce
yalan söyleyen bir metin demektir — dokümanın koddan sapmasının §9.1'in kendi anlattığı
sebebi. Bildirilen şey imzadır; `usage()` onun tek okunuşudur.

**Serbest metin alanı en sonda:** §8.3'e göre en fazla bir alan bayrak gibi görünen metin
barındırabilir ve o alan imzada en sonda durur. Bu kural burada, tanım anında zorlanır;
CLI ayrıştırıcısının çalışma anında keşfetmesine bırakılmaz.
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

import httpx

from mayen.config import Config
from mayen.data.repositories.courses import CourseRepository
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository
from mayen.data.repositories.tasks import TaskRepository
from mayen.policy.effects import Effect


class ArgType(StrEnum):
    """Argüman tipleri. Hem doğrulama hem gramer üretimi bu kümeden okur."""

    STRING = "string"
    INTEGER = "integer"
    LIST = "list"


class ToolSpecError(Exception):
    """Bozuk tool tanımı. Çalışma anında değil, tanım anında patlar."""


class ToolArgumentError(Exception):
    """Geçersiz çağrı. §8.5 adım 1: kullanıcıya hiç sorulmaz, modele geri beslenir —
    `usage` da o yüzden hatanın üstünde taşınır."""

    def __init__(self, message: str, usage: str) -> None:
        super().__init__(message)
        self.usage = usage


@dataclass(frozen=True, slots=True)
class Arg:
    """Tipli argüman.

    `trailing`: bu alandan sonrası satır sonuna kadar tek parça metindir ve hiçbir jeton
    bayrak sayılmaz (§8.3). İmzada en fazla bir tane olabilir ve en sonda durur.
    """

    name: str
    type: ArgType
    description: str
    required: bool = True
    trailing: bool = False


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Yapılandırılmış sonuç (§9.1).

    Dört alan ayrı taşınır; "her şey metindir, JSON'u iki kere ayrıştır" düzeni kurulmaz.
    `speech` kullanıcıya okunacak biçim, `data` modele geri beslenen veridir.
    """

    ok: bool
    data: Mapping[str, object] | None = None
    speech: str = ""
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Tool'un veriye ulaşabildiği tek kapı (§9.1).

    Genel bir veritabanı tutamacı yok: tool ne verildiyse ona erişir. Bu yüzden alanlar
    `Database` değil repository'lerdir — SQL `data/` dışına çıkmaz (§16).
    """

    config: Config
    http: httpx.AsyncClient
    """Dışarıya açılan tek kapı (`DIŞ` etkili tool'lar için). Tool kendi istemcisini
    kurmuyor: bağlantı havuzu ve zaman aşımı çağıranın elinde kalsın, testte de gerçek ağa
    çıkmadan taşıma değiştirilebilsin diye."""

    people: PeopleRepository
    notes: NoteRepository
    courses: CourseRepository
    tasks: TaskRepository
    course_term: str
    """Geçerli dönem. §19.8'e göre program depodaki dosyadan yükleniyor; dönemi bilen de
    o yükleyici. Tool bunu argüman olarak sormaz — model hangi dönemde olunduğunu bilmez."""


Handler = Callable[[ToolContext, Mapping[str, object]], Awaitable[ToolResult]]


def text(arguments: Mapping[str, object], name: str) -> str:
    """Doğrulanmış argümanı tipiyle okur. `validate()` geçtiyse tip zaten doğru; yanlışsa
    bu bir çağrı hatası değil tanım hatasıdır, o yüzden `AssertionError` değil `TypeError`."""
    value = arguments[name]
    if not isinstance(value, str):
        raise TypeError(f"{name}: metin bekleniyordu, {type(value).__name__} geldi")
    return value


def optional_text(arguments: Mapping[str, object], name: str) -> str | None:
    return None if name not in arguments else text(arguments, name)


def number(arguments: Mapping[str, object], name: str) -> int:
    value = arguments[name]
    if not isinstance(value, int):
        raise TypeError(f"{name}: tam sayı bekleniyordu, {type(value).__name__} geldi")
    return value


def optional_number(arguments: Mapping[str, object], name: str) -> int | None:
    return None if name not in arguments else number(arguments, name)


@dataclass(frozen=True, slots=True)
class Tool:
    """Bir tool'un tam tanımı: katalogda görünen metin, imza, politika ve gövde."""

    name: str
    description: str
    effect: Effect
    timeout_seconds: float
    handler: Handler
    args: Sequence[Arg] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for index, arg in enumerate(self.args):
            if arg.name in seen:
                raise ToolSpecError(f"{self.name}: yinelenen argüman {arg.name!r}")
            seen.add(arg.name)
            if arg.trailing and index != len(self.args) - 1:
                raise ToolSpecError(
                    f"{self.name}: serbest metin alanı {arg.name!r} imzada en sonda"
                    " durmalı (§8.3)"
                )
        if sum(1 for arg in self.args if arg.trailing) > 1:
            raise ToolSpecError(
                f"{self.name}: en fazla bir serbest metin alanı olabilir (§8.3)"
            )
        if self.timeout_seconds <= 0:
            raise ToolSpecError(f"{self.name}: zaman aşımı pozitif olmalı")

    def validate(self, raw: Mapping[str, str]) -> dict[str, object]:
        """Ham argümanları tipli değerlere çevirir (§9.1: tipli ve doğrulanmış).

        Bilinmeyen alan da hatadır: gramerde alan adları sabit liste olduğu için oraya
        düşen bir ad, modelin uydurduğu değil ayrıştırıcının kaçırdığı bir şeydir.
        """
        known = {arg.name: arg for arg in self.args}
        for name in raw:
            if name not in known:
                raise ToolArgumentError(
                    f"{self.name}: bilinmeyen argüman {name!r}", self.usage()
                )
        values: dict[str, object] = {}
        for arg in self.args:
            if arg.name not in raw:
                if arg.required:
                    raise ToolArgumentError(
                        f"{self.name}: zorunlu argüman eksik {arg.name!r}", self.usage()
                    )
                continue
            values[arg.name] = self._coerce(arg, raw[arg.name])
        return values

    def _coerce(self, arg: Arg, value: str) -> object:
        text = value.strip()
        if not text:
            raise ToolArgumentError(f"{self.name}: {arg.name!r} boş olamaz", self.usage())
        match arg.type:
            case ArgType.STRING:
                return text
            case ArgType.INTEGER:
                try:
                    return int(text)
                except ValueError as exc:
                    raise ToolArgumentError(
                        f"{self.name}: {arg.name!r} bir tam sayı olmalı, {text!r} verildi",
                        self.usage(),
                    ) from exc
            case ArgType.LIST:
                items = [item.strip() for item in text.split(",") if item.strip()]
                if not items:
                    raise ToolArgumentError(
                        f"{self.name}: {arg.name!r} boş liste olamaz", self.usage()
                    )
                return items

    def usage(self) -> str:
        """Hatalı çağrıdan sonra modele dönen `--help` çıktısı (§8.3)."""
        signature = " ".join(
            f"--{arg.name} <{arg.type}>" if arg.required else f"[--{arg.name} <{arg.type}>]"
            for arg in self.args
        )
        lines = [f"{self.name} {signature}".rstrip(), f"  {self.description}"]
        for arg in self.args:
            mark = "" if arg.required else " (isteğe bağlı)"
            lines.append(f"  --{arg.name}: {arg.description}{mark}")
        return "\n".join(lines)
