"""Yapılandırma: tipli, tek yerde, ortam değişkeninden.

Sırlar koda ve depoya girmez; yalnızca ortamdan okunur (P1, §19.7). Eksik sır sessizce
yok sayılmaz — `None` olarak taşınır ve ona ihtiyaç duyan tool açık hata verir (§14).
"""

import logging
import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

PREFIX = "MAYEN_"


class ConfigError(Exception):
    """Yapılandırma okunamadı. Sessizce varsayılana düşülmez (Kural 13)."""


class ServiceKind(StrEnum):
    """Bir model servisi gerçek mi sahte mi (§3).

    Seçim yapılandırmada, çünkü sahteler yalnızca testin işi değil: TTS servisini
    ayağa kaldırmadan uçtan uca konuşmak, ya da bir ölçüm koşarken GPU'yu boşaltmak
    isteyen kişi de aynı düğmeyi çeviriyor. `main.py`'de tek bir `if`'e karşılık geliyor;
    üst katmanların hiçbiri bu ayrımı görmüyor.

    Değerler İngilizce ve §-sözlüğünden değil: bunlar `ARCHITECTURE.md`'nin alan
    kelimeleri değil, kabuğun düğmeleri.
    """

    FAKE = "fake"
    REAL = "real"


@dataclass(frozen=True, slots=True)
class Secret:
    """Kayıtlara ve traceback'lere sızmayan sır sarmalayıcısı.

    Değere yalnızca `.reveal()` ile ulaşılır; `repr`/`str` her zaman maskelidir, böylece
    bir sır yanlışlıkla structlog alanına veya hata mesajına konsa bile açığa çıkmaz.
    """

    _value: str

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(***)"

    def __str__(self) -> str:
        return "***"


@dataclass(frozen=True, slots=True)
class Config:
    log_level: int = logging.INFO
    log_json: bool = False
    openweathermap_key: Secret | None = None
    # §3: modeller kendi süreçlerinde, HTTP arkasında. Adres yapılandırmadan gelir —
    # modeli değiştirmek ya da başka makineye taşımak yalnızca bu satırın değişmesi.
    # Zaman aşımı bilerek burada değil: onu istemciyi kuran taraf seçer (bkz.
    # `adapters/llamacpp.py`); ölçüm ile tur akışının bütçeleri aynı sayı değil.
    llm_url: str = "http://127.0.0.1:8080"
    # Kokoro TTS servisi (`services/kokoro/`), aynı gerekçeyle ayrı süreç ve ayrı adres.
    # Ses karakteri (§19.10) buradan gelmiyor: ses, hız ve efekt zinciri servisin kendi
    # ortam değişkenleri — modeli tanıyan tarafta durmaları gerekiyor ve uygulama süreci
    # onları hiç görmüyor.
    tts_url: str = "http://127.0.0.1:8081"
    # Hangi adaptör kurulacak. **STT varsayılanı `fake` ve bu bir tercih değil**: §19.2'nin
    # STT yarısı açık, seçilmiş bir model yok. `real` verildiğinde süreç açılışta duruyor
    # ve açık maddeyi adıyla söylüyor — bir varsayılana düşmek, açık bir maddeyi
    # varsayımla kapatmak olurdu (§19'un meta kuralı). TTS varsayılanı `real`: Kokoro
    # seçildi ve çalışıyor (Faz 7).
    stt: ServiceKind = ServiceKind.FAKE
    tts: ServiceKind = ServiceKind.REAL
    # §16: veritabanı tek dosya, tek sahip. Yedekleme ayarları §19.12'de açık ama açık
    # olan şey bu sayıların ne olacağı, yedeğin var olup olmayacağı değil.
    db_path: Path = Path("mayen.db")
    backup_dir: Path = Path("backups")
    backup_keep: int = 7
    backup_interval_minutes: int = 360
    # §12: uygulama kapalıyken vakti geçmiş görev, açılışta bu tolerans içindeyse
    # çalıştırılır, değilse düşürülür. §19.13 sayıyı açık bırakıyor ve açık olan şey
    # **sayı**; davranışı §12 zaten tanımlıyor. Otuz dakika bir varsayılan: kısa bir
    # yeniden başlatmadan sonra hatırlatıcı hâlâ anlamlı, ertesi güne kalanı değil.
    missed_task_tolerance_minutes: int = 30
    # §19.9: ad → MAC, bir yapılandırma dosyasında. Tablo ve CRUD tool'ları yok; yeni
    # cihaz eklemek bir satır.
    wol_targets: Mapping[str, str] = field(default_factory=dict)
    # Açılabilir uygulamalar: ad → argv. Aynı gerekçe (Değişmez 8), aynı biçim; listede
    # olmayan bir uygulama açılamaz.
    apps: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    # §19.8: ders programı depodaki dosyadan gelir ve açılışta DB'ye yüklenir. Dönem
    # burada yok, dosyanın kendisinde — gerekçesi `data/schedule.py`'nin başlığında.
    # Yolu verilmezse program yüklenmez; tool boş program bildirir.
    courses_path: Path | None = None
    # Asistanın kişiliği/üslubu: düz metin dosyası (§8.1'in rol parçası). Yalnızca **rol**
    # buradan gelir; çağrı biçimi ve tool kataloğu defterden üretilmeye devam eder —
    # gerekçesi `agent/prompt.py:system_prompt`'ta. **Zorunlu**: kodda yedek metin yok.
    role_path: Path | None = None
    # §2'nin "çıkış İngilizce" kuralı, ayrı dosya. Rol metninin **içinde** değil, çünkü
    # yeri belirleyici: sistem promptunun en sonuna, katalogdan sonra gidiyor ve rolün
    # başına yazıldığında ölçülebilir biçimde tutmuyor (`docs/faz7-rol.md`). Zorunlu
    # değil: verilmezse model konuşmanın dilinde cevaplar, yani eski davranış.
    language_rule_path: Path | None = None
    # §13'ün soketinin dinlediği yer. Varsayılan `127.0.0.1`: uzaktan erişim kapsam
    # dışı (§1), yani dışarıya açılmak bir yapılandırma kararı olmalı, varsayılan değil.
    host: str = "127.0.0.1"
    port: int = 8765
    # §19.3 (konuşmacı eşikleri) açık olduğu sürece kimlik `TANINMAYAN` kalır ve §10.2'nin
    # o satırında dört hücrenin dördü de RED — yani hiçbir tool çağrılamaz. Bu bayrak açık
    # maddeyi kapatmıyor, geçici bir kapı açıyor: verildiğinde bütün segmentler SAHİP
    # sayılır. **Kural 6 bozulmuyor**, çünkü kapı ses değil kabuk: bayrağı verebilen
    # kişinin makineye erişimi var (§19.14'ün kurulum betiğiyle aynı mantık). Konuşmacı
    # tanıma gerçek olduğunda bu satır silinir.
    assume_owner: bool = False


def load(env: Mapping[str, str] | None = None) -> Config:
    """Ortamdan yapılandırmayı okur. Süreç başına bir kez, en erken anda çağrılır."""
    src = os.environ if env is None else env
    default = Config()
    return Config(
        log_level=_level(src.get(f"{PREFIX}LOG_LEVEL")),
        log_json=_bool(src.get(f"{PREFIX}LOG_JSON")),
        openweathermap_key=_secret(src.get(f"{PREFIX}OPENWEATHERMAP_KEY")),
        llm_url=_url(f"{PREFIX}LLM_URL", src.get(f"{PREFIX}LLM_URL"), default.llm_url),
        tts_url=_url(f"{PREFIX}TTS_URL", src.get(f"{PREFIX}TTS_URL"), default.tts_url),
        stt=_kind(f"{PREFIX}STT", src.get(f"{PREFIX}STT"), default.stt),
        tts=_kind(f"{PREFIX}TTS", src.get(f"{PREFIX}TTS"), default.tts),
        db_path=_path(src.get(f"{PREFIX}DB_PATH"), default.db_path),
        backup_dir=_path(src.get(f"{PREFIX}BACKUP_DIR"), default.backup_dir),
        backup_keep=_positive_int(
            f"{PREFIX}BACKUP_KEEP", src.get(f"{PREFIX}BACKUP_KEEP"), default.backup_keep
        ),
        backup_interval_minutes=_positive_int(
            f"{PREFIX}BACKUP_INTERVAL_MINUTES",
            src.get(f"{PREFIX}BACKUP_INTERVAL_MINUTES"),
            default.backup_interval_minutes,
        ),
        missed_task_tolerance_minutes=_positive_int(
            f"{PREFIX}MISSED_TASK_TOLERANCE_MINUTES",
            src.get(f"{PREFIX}MISSED_TASK_TOLERANCE_MINUTES"),
            default.missed_task_tolerance_minutes,
        ),
        wol_targets=_wol_targets(src.get(f"{PREFIX}WOL_TARGETS_PATH")),
        apps=_apps(src.get(f"{PREFIX}APPS_PATH")),
        courses_path=_optional_path(src.get(f"{PREFIX}COURSES_PATH")),
        role_path=_optional_path(src.get(f"{PREFIX}ROLE_PATH")),
        language_rule_path=_optional_path(src.get(f"{PREFIX}LANGUAGE_RULE_PATH")),
        host=_host(src.get(f"{PREFIX}HOST"), default.host),
        port=_positive_int(f"{PREFIX}PORT", src.get(f"{PREFIX}PORT"), default.port),
        assume_owner=_bool(src.get(f"{PREFIX}ASSUME_OWNER")),
    )


_MAC = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")

_APP_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
"""Uygulama adları gramere seçenek olarak giriyor (`ArgType.ENUM`), o yüzden aynı dar
biçime uymak zorundalar. Kısıt `tools/spec.py`'de de yazılı; burada tekrarlanıyor çünkü
`config` alt katman ve tersine bağımlılık §4'ü kırardı. Burada yakalanınca hata dosyayı ve
satırı gösteriyor; orada yakalansaydı açılışta anlamsız bir tanım hatası olurdu."""


def _wol_targets(raw: str | None) -> Mapping[str, str]:
    """§19.9'un ad → MAC dosyası (TOML, `[targets]` altında).

    Dosya yoksa hedef de yoktur; ama **verilen bir yol okunamıyorsa** bu sessizce boş
    listeye düşmez (Kural 13): yanlış yazılmış bir yol, "hiçbir cihaz tanımlı değil"
    diyen bir asistanla sonuçlanırdı.
    """
    if raw is None or not raw.strip():
        return {}
    path = Path(raw.strip()).expanduser()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{PREFIX}WOL_TARGETS_PATH okunamadı: {path}") from exc
    targets = data.get("targets", {})
    if not isinstance(targets, dict):
        raise ConfigError(f"{path}: 'targets' bir tablo olmalı")
    for name, mac in targets.items():
        if not isinstance(mac, str) or not _MAC.match(mac):
            raise ConfigError(f"{path}: {name!r} için geçersiz MAC adresi: {mac!r}")
    return dict(targets)


def _apps(raw: str | None) -> Mapping[str, tuple[str, ...]]:
    """Açılabilir uygulamalar: ad → argv (TOML, `[apps]` altında).

    §19.9'un WoL dosyasının kardeşi ve aynı sebeple var (Değişmez 8): modelin söylediği
    komutu çalıştırmak, model çıktısını kabukta çalıştırmak olurdu. Model yalnızca listedeki
    **adı** seçiyor; komut satırını burası biliyor.

    Değer bir **dizi**, tek bir metin değil: `"firefox --new-window"` yazılabilseydi onu
    bölmek için bir kabuk ayrıştırmasına ihtiyaç olurdu ve tırnak/boşluk kuralları tam da
    kaçmanın sızdığı yer. Dizide her eleman bir argüman.
    """
    if raw is None or not raw.strip():
        return {}
    path = Path(raw.strip()).expanduser()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{PREFIX}APPS_PATH okunamadı: {path}") from exc
    apps = data.get("apps", {})
    if not isinstance(apps, dict):
        raise ConfigError(f"{path}: 'apps' bir tablo olmalı")
    result: dict[str, tuple[str, ...]] = {}
    for name, argv in apps.items():
        if not _APP_NAME.fullmatch(name):
            raise ConfigError(
                f"{path}: geçersiz uygulama adı {name!r} — küçük harf, rakam, '-' ve '_'"
            )
        if not isinstance(argv, list) or not argv:
            raise ConfigError(f"{path}: {name!r} için komut boş olmayan bir dizi olmalı")
        if not all(isinstance(part, str) and part for part in argv):
            raise ConfigError(f"{path}: {name!r} komutunun her parçası metin olmalı")
        result[name] = tuple(argv)
    return result


def _level(raw: str | None) -> int:
    if raw is None:
        return logging.INFO
    level = logging.getLevelNamesMapping().get(raw.strip().upper())
    if level is None:
        raise ConfigError(f"{PREFIX}LOG_LEVEL geçersiz: {raw!r}")
    return level


def _bool(raw: str | None) -> bool:
    if raw is None:
        return False
    normalized = raw.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    raise ConfigError(f"Mantıksal değer bekleniyordu, {raw!r} geldi")


def _path(raw: str | None, default: Path) -> Path:
    if raw is None or not raw.strip():
        return default
    return Path(raw.strip()).expanduser()


def _optional_path(raw: str | None) -> Path | None:
    if raw is None or not raw.strip():
        return None
    return Path(raw.strip()).expanduser()


def _host(raw: str | None, default: str) -> str:
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _url(name: str, raw: str | None, default: str) -> str:
    """Şema aranıyor: şemasız bir adres `httpx` tarafında göreli yol sayılır ve hata
    isteğin ilk denendiği anda, çok uzakta çıkar (Kural 13)."""
    if raw is None or not raw.strip():
        return default
    value = raw.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        raise ConfigError(f"{name} http:// ya da https:// ile başlamalı: {raw!r}")
    return value


def _kind(name: str, raw: str | None, default: ServiceKind) -> ServiceKind:
    """`fake` ya da `real`. Tanınmayan değer hata: `--tts gercek` yazan kişinin sessizce
    sahteyle koşması, tam da fark etmeyeceği bir yanlışlık olurdu (Kural 13)."""
    if raw is None or not raw.strip():
        return default
    try:
        return ServiceKind(raw.strip().lower())
    except ValueError:
        secenekler = "/".join(kind.value for kind in ServiceKind)
        raise ConfigError(f"{name} {secenekler} olmalı: {raw!r}") from None


def _positive_int(name: str, raw: str | None, default: int) -> int:
    """Sıfır ve negatif de reddedilir: `backup_keep=0` "yedek alma" demek değil, ayarın
    yanlış yazıldığı anlamına gelir ve sessizce kabul edilirse veri kaybettirir."""
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} bir tamsayı olmalı, {raw!r} geldi") from None
    if value < 1:
        raise ConfigError(f"{name} pozitif olmalı, {value} geldi")
    return value


def _secret(raw: str | None) -> Secret | None:
    if raw is None or not raw.strip():
        return None
    return Secret(raw.strip())
