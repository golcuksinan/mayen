"""OpenWeatherMap'in "şimdiki hava" ucu (§9.5). Anahtar ortamdan gelir ve yalnızca sorgu
parametresine yazılırken açılır (§14); hata metinlerine adres girmez, çünkü adres anahtarı
taşır.
"""

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from pydantic import SecretStr

from mayen.ports.weather import Weather, WeatherError, WeatherFailure

TIMEOUT_S = 8.0


class OpenWeatherMap:
    def __init__(self, url: str, key: SecretStr) -> None:
        self._url = url
        self._key = key

    async def current(self, place: str) -> Weather:
        query = urllib.parse.urlencode(
            {"q": place, "appid": self._key.get_secret_value(), "units": "metric", "lang": "en"}
        )
        payload = await asyncio.to_thread(self._get, f"{self._url}?{query}")
        try:
            return Weather(
                place=str(payload["name"]),
                temperature_c=float(payload["main"]["temp"]),
                feels_like_c=float(payload["main"]["feels_like"]),
                condition=str(payload["weather"][0]["description"]),
                humidity_percent=int(payload["main"]["humidity"]),
                wind_m_s=float(payload["wind"]["speed"]),
            )
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise WeatherError(WeatherFailure.UNAVAILABLE, f"unexpected reply: {e}") from e

    @staticmethod
    def _get(url: str) -> Any:  # noqa: ANN401
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_S) as reply:
                return json.load(reply)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise WeatherError(WeatherFailure.NOT_FOUND, "no such place") from None
            if e.code in (401, 429):
                raise WeatherError(WeatherFailure.REJECTED, f"provider said {e.code}") from None
            raise WeatherError(WeatherFailure.UNAVAILABLE, f"provider said {e.code}") from None
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            # `URLError`'ın metni adresi içermez; yine de yalnızca sebebi taşınır.
            reason = getattr(e, "reason", type(e).__name__)
            raise WeatherError(WeatherFailure.UNAVAILABLE, f"unreachable: {reason}") from None
