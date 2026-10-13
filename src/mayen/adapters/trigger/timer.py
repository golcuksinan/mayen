"""Zamanlayıcı tetikleyicisi (§5.1, §12): depoya aralıklarla bakar, vadesi geleni gönderir.

Bir sonraki vadeye kadar uyumak yerine bakılır: `asyncio`'nun uykusu tekdüze saatle sayar ve
makine uykudayken durur, uyanınca vadesi çoktan geçmiş bir zamanlayıcı geç kalırdı. Yeni
kurulan bir zamanlayıcı da uyuyan döngüyü uyandırmak için ayrı bir yol isterdi.
"""

import asyncio
from collections.abc import Awaitable, Callable

# Bir hatırlatmanın en çok bu kadar geç çalması bir insan için fark edilmez.
INTERVAL_S = 1.0


class TimerTrigger:
    def __init__(
        self, dispatch: Callable[[], Awaitable[None]], interval_s: float = INTERVAL_S
    ) -> None:
        self._dispatch = dispatch
        self._interval_s = interval_s

    async def run(self) -> None:
        """İptal edilene kadar; ilk bakış hemen, açılışta kaçırılanlar beklemesin (§12)."""
        while True:
            await self._dispatch()
            await asyncio.sleep(self._interval_s)
