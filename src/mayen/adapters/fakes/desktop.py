"""Sahte masaüstü.

Yapılan çağrıyı biriktiriyor: testin ölçtüğü şey "ne oldu" değil **ne istendi** — gerçek
etki (pencerenin kapanması) testte zaten gözlemlenemez. Ses seviyesi bir alan olarak
duruyor, çünkü "önce oku sonra yaz" davranışı olan tek yer o.
"""

from collections.abc import Sequence

from mayen.adapters.errors import ServiceFailedError

SERVICE = "fake-desktop"


class FakeDesktop:
    def __init__(self, *, level: int = 40, player: str | None = "firefox") -> None:
        self.level = level
        self.player = player
        self.windows: list[str] = []
        self.medias: list[str] = []
        self.launched: list[Sequence[str]] = []

    async def volume(self) -> int:
        return self.level

    async def set_volume(self, level: int) -> None:
        self.level = level

    async def media(self, action: str) -> str:
        if self.player is None:
            raise ServiceFailedError(SERVICE, "çalışan bir medya oynatıcısı yok")
        self.medias.append(action)
        return self.player

    async def window(self, action: str) -> None:
        self.windows.append(action)

    async def launch(self, argv: Sequence[str]) -> None:
        self.launched.append(tuple(argv))
