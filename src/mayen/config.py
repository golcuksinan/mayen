"""Yapılandırma: tipli, tek yerde, ortam değişkeninden.

Sırlar koda ve depoya girmez; yalnızca ortamdan okunur (P1, §19.7). Eksik sır sessizce
yok sayılmaz — `None` olarak taşınır ve ona ihtiyaç duyan tool açık hata verir (§14).
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

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


def load(env: Mapping[str, str] | None = None) -> Config:
    """Ortamdan yapılandırmayı okur. Süreç başına bir kez, en erken anda çağrılır."""
    src = os.environ if env is None else env
    return Config(
        log_level=_level(src.get(f"{PREFIX}LOG_LEVEL")),
        log_json=_bool(src.get(f"{PREFIX}LOG_JSON")),
        openweathermap_key=_secret(src.get(f"{PREFIX}OPENWEATHERMAP_KEY")),
    )


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


def _secret(raw: str | None) -> Secret | None:
    if raw is None or not raw.strip():
        return None
    return Secret(raw.strip())
