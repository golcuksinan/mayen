"""Boştaki arka plan işlerinin koşucusu (§11.2, §11.3, Kural 11, B4).

**Kural 11 iki ayrı şey istiyor ve ikincisi unutulanı:** iş tur sırasında *başlamaz*, ve
boşta başlamış bir iş **tur kuyruğa girer girmez iptal edilir**. İkincisi olmadan birincisi
işe yaramaz: boşta başlayan bir özetleme, tur geldiğinde hâlâ üretim yapıyor olabilir ve
tek GPU'nun tek slotunu tutar — kullanıcının ilk token'ı onu bekler.

**İptal jetonu asyncio'nun kendisi.** §11.3 "bütün arka plan işleri bir iptal jetonu
taşır" diyor; taşıdıkları jeton işin kendi görevi. Bu projede ikinci bir iptal yolu
bilinçli olarak yok (bkz. `adapters/llm.py`, `session/actor.py`): iki yoldan biri er ya da
geç unutulur, ve unutulan yol sessizce çalışmaya devam eden bir arka plan işi demektir.

**Turun bitişinden hemen sonra değil, bir gecikme sonra.** Kullanıcı çoğu zaman bir cevabın
ardından ikinci kez konuşur; sesin bitişiyle birlikte üretime başlamak, o ikinci turun ilk
token'ını bekletmek olurdu. Gecikme ölçülmüş bir sayı değil, bir işletim değeri — montaj
veriyor.

**İptal edilen iş baştan başlar, kaldığı yerden değil** (§11.3: yarım kalmışın sonucu
yazılmaz). `Digest` zaten yazmadan önce üretimi bitiriyor.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence

from mayen.obs.log import get_logger

log = get_logger(__name__)

type Job = Callable[[], Awaitable[object]]


class BackgroundWork:
    """Boşta koşan, tur gelince iptal edilen işler."""

    def __init__(self, jobs: Sequence[Job], *, delay_seconds: float) -> None:
        self._jobs = tuple(jobs)
        self._delay = delay_seconds
        self._wake = asyncio.Event()
        self._busy = False
        self._supervisor: asyncio.Task[None] | None = None
        self._running: asyncio.Task[None] | None = None
        #: Kaç kez preempt edildi. Sık preempt edilen bir iş hiç bitmiyor demektir; §11.2
        #: kırpma sıklığını nasıl ölçtürüyorsa bu da öyle okunur.
        self.preempted = 0

    async def start(self) -> None:
        """§11.2'nin birinci anı: açılışta bekleyen iş varsa işlenir."""
        if self._supervisor is not None:
            return
        self._supervisor = asyncio.create_task(self._loop(), name="memory:background")
        self._wake.set()

    async def stop(self) -> None:
        for task in (self._running, self._supervisor):
            if task is not None:
                task.cancel()
                # `await task` değil: iş kapanıştan **önce** patlamış olabilir ve o hata
                # zaten kayda geçti (`_collect`); ikinci kez yükseltmek, kapatmayı
                # başarısız kılardı.
                await asyncio.wait({task})
        self._running = None
        self._supervisor = None

    def turn_started(self) -> None:
        """Tur kuyruğa girdi (B4). Senkron: iptalin beklemesi, tam da beklenmemesi gereken
        şeyi beklemek olurdu."""
        self._busy = True
        if self._running is not None and not self._running.done():
            self.preempted += 1
            log.info("arka plan işi turun önünden çekildi", preempted=self.preempted)
            self._running.cancel()

    def turn_finished(self) -> None:
        """§11.2'nin ikinci anı: boştaki ilk fırsat."""
        self._busy = False
        self._wake.set()

    async def _loop(self) -> None:
        while True:
            await self._wake.wait()
            self._wake.clear()
            await asyncio.sleep(self._delay)
            if self._busy:
                continue
            self._running = asyncio.create_task(self._run_all(), name="memory:jobs")
            # `await` değil: iş preempt edildiğinde `CancelledError` denetçiyi de
            # öldürürdü ve bir daha hiçbir iş koşmazdı.
            await asyncio.wait({self._running})
            self._collect(self._running)
            self._running = None

    def _collect(self, task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return  # preempt: beklenen son, hata değil
        error = task.exception()
        if error is not None:
            # Kural 13: patlayan bir bellek işi sessizce kaybolmaz, ama turu da etkilemez.
            log.exception("arka plan işi başarısız", error=str(error), exc_info=error)

    async def _run_all(self) -> None:
        for job in self._jobs:
            await job()
