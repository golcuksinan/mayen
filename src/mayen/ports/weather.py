"""Hava durumu kaynağı portu (§9.5): skill *ne* istendiğini bilir, sağlayıcıyı adaptör bilir.

Değerler metrik; durum metni İngilizcedir, modele giden her metin gibi (§8.6).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class WeatherFailure(StrEnum):
    NOT_FOUND = "not_found"  # sağlayıcı böyle bir yer bilmiyor
    REJECTED = "rejected"  # anahtar reddedildi ya da kota doldu
    UNAVAILABLE = "unavailable"  # sağlayıcıya ulaşılamadı ya da yanıtı okunamadı


class WeatherError(Exception):
    def __init__(self, failure: WeatherFailure, detail: str) -> None:
        super().__init__(detail)
        self.failure = failure


@dataclass(frozen=True)
class Weather:
    place: str  # sağlayıcının bulduğu yer; söylenenle aynı olmayabilir
    temperature_c: float
    feels_like_c: float
    condition: str
    humidity_percent: int
    wind_m_s: float


class WeatherSource(Protocol):
    async def current(self, place: str) -> Weather:
        """Şimdiki hava; başarısızlık `WeatherError`."""
        ...
