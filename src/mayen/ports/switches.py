"""Evdeki anahtarlar portu (§9.5): akıllı priz ve ona takılı olan. Skill *ne* istendiğini
bilir, cihazın markasını ve protokolünü adaptör bilir.

Anahtar adıyla seçilir; ad sahibin config'te verdiğidir ("gece lambası"), prize takılan
değişince yalnızca o ad değişir.
"""

from enum import StrEnum
from typing import Protocol


class SwitchFailure(StrEnum):
    REJECTED = "rejected"  # cihaz kimlik bilgisini reddetti
    UNAVAILABLE = "unavailable"  # cihaza ulaşılamadı ya da yanıtı okunamadı


class SwitchError(Exception):
    def __init__(self, failure: SwitchFailure, detail: str) -> None:
        super().__init__(detail)
        self.failure = failure


class Switches(Protocol):
    async def set(self, name: str, on: bool) -> None:
        """Anahtarı açar ya da kapatır; başarısızlık `SwitchError`."""
        ...

    async def is_on(self, name: str) -> bool:
        """Anahtarın şimdiki durumu, cihazdan okunur; başarısızlık `SwitchError`."""
        ...
