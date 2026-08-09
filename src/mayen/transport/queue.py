"""Giden çerçeve kuyruğu ve backpressure (§13).

**Kuyruk sınırlıdır ve dolduğunda yazan taraf bekler; çerçeve düşürülmez.** Sıra bozulması
§6'ya göre kabul edilemez bir hatadır, dolayısıyla taşmada eskiyi atmak seçenek değil.
Beklemek doğru davranış çünkü baskı kaynağa kadar geriye yürüyor: istemci sesi tüketemiyorsa
TTS kuyruğu yavaşlar, o da sentezi yavaşlatır. Sınırsız kuyruk bunun yerine belleği şişirir
ve gecikmeyi kimsenin ölçmediği bir yere saklar.

**Tek istisna iptaldir ve kapsamı turdur** (§12, B1/B2): `cancel_turn` yalnızca o tura ait
bekleyen çerçeveleri düşürür. Kuyruğu baştan boşaltmak, söz kesmenin sırada bekleyen
proaktif hatırlatıcıyı da öldürmesi demek olurdu — ve bu, kullanıcının hiç haberi olmadan
kaybolan bir bildirim demek.
"""

import asyncio
from collections import deque

from mayen.transport.frames import Frame

DEFAULT_MAXSIZE = 64


class SendQueue:
    def __init__(self, maxsize: int = DEFAULT_MAXSIZE) -> None:
        if maxsize < 1:
            raise ValueError("maxsize en az 1 olmalı")
        self._maxsize = maxsize
        self._frames: deque[Frame] = deque()
        self._changed = asyncio.Condition()

    def __len__(self) -> int:
        return len(self._frames)

    @property
    def full(self) -> bool:
        return len(self._frames) >= self._maxsize

    async def put(self, frame: Frame) -> None:
        """Yer açılana kadar bekler. İptal edilebilir (Kural 12)."""
        async with self._changed:
            await self._changed.wait_for(lambda: not self.full)
            self._frames.append(frame)
            self._changed.notify_all()

    async def get(self) -> Frame:
        async with self._changed:
            await self._changed.wait_for(lambda: bool(self._frames))
            frame = self._frames.popleft()
            self._changed.notify_all()
            return frame

    async def cancel_turn(self, turn_id: str) -> int:
        """Verilen tura ait bekleyen çerçeveleri düşürür; kaçının düştüğünü döner.

        Turu olmayan çerçeveler ve başka turun çerçeveleri yerinde kalır.
        """
        async with self._changed:
            before = len(self._frames)
            self._frames = deque(
                frame for frame in self._frames if getattr(frame, "turn_id", None) != turn_id
            )
            self._changed.notify_all()
            return before - len(self._frames)
