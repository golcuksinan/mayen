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
from pathlib import Path

PREFIX = "MAYEN_"


class ConfigError(Exception):
    """Yapılandırma okunamadı. Sessizce varsayılana düşülmez (Kural 13)."""


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
    # §16: veritabanı tek dosya, tek sahip. Yedekleme ayarları §19.12'de açık ama açık
    # olan şey bu sayıların ne olacağı, yedeğin var olup olmayacağı değil.
    db_path: Path = Path("mayen.db")
    backup_dir: Path = Path("backups")
    backup_keep: int = 7
    backup_interval_minutes: int = 360
    # §19.9: ad → MAC, bir yapılandırma dosyasında. Tablo ve CRUD tool'ları yok; yeni
    # cihaz eklemek bir satır.
    wol_targets: Mapping[str, str] = field(default_factory=dict)


def load(env: Mapping[str, str] | None = None) -> Config:
    """Ortamdan yapılandırmayı okur. Süreç başına bir kez, en erken anda çağrılır."""
    src = os.environ if env is None else env
    default = Config()
    return Config(
        log_level=_level(src.get(f"{PREFIX}LOG_LEVEL")),
        log_json=_bool(src.get(f"{PREFIX}LOG_JSON")),
        openweathermap_key=_secret(src.get(f"{PREFIX}OPENWEATHERMAP_KEY")),
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
        wol_targets=_wol_targets(src.get(f"{PREFIX}WOL_TARGETS_PATH")),
    )


_MAC = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


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
