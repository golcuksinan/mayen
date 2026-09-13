"""Zamanlanmış görevlerin koşucusu (§12).

Görevler kalıcı; süreç kapanıp açıldığında kaybolmuyorlar — depoları `data`'da, buradaki
tek iş **vakti gelene bakmak ve koşturmak**. İki ayrı işi var ve ikisi de aynı tik'ten
besleniyor:

- **Veritabanındaki görevler** (`scheduled_tasks`): vakti gelmiş olanlar türüne göre bir
  işleyiciye gidiyor ve sonucu satıra yazılıyor.
- **Yinelenen işler** (`Recurring`): yedekleme gibi, satırı olmayan ve yalnızca aralığı
  olan işler. Bunları da göreve çevirmek, kullanıcının `task_list` ile göreceği kuyruğu
  sistemin kendi bakım işleriyle doldurmak olurdu.

**Kaçırılmış görev açılışta karara bağlanır** (§12): tolerans içindeyse çalıştırılır,
değilse `DUSURULDU` olarak işaretlenir — sessizce silinmez, sessizce de geç çalışmaz.
Tolerans bir yapılandırma değeri (§19.13); süresi burada seçilmiyor.

**Açılıştaki kaçırılmışlık ile koşarken gecikme aynı şey değil.** Süreç ayaktayken bir
görev en fazla bir tik geç kalır; tolerans yalnızca **açılış taramasında** uygulanıyor.
Her tik'te uygulansaydı, uzun bir işin arkasında bekleyen görev toleransı aşıp düşerdi.

**Patlayan görev tekrar denenmiyor.** Sonuç satıra yazılıp görev kapanıyor: `BEKLIYOR`
bırakmak, aynı hatayı her tik'te tekrarlayan ve kaydı dolduran bir döngü demekti. Tanınmayan
tür de aynı yoldan kapanıyor — sessizce atlanan bir görev, sonsuza kadar vakti geçmiş
kalırdı (Kural 13).

**Kural 11 burada da geçerli:** hatırlatıcının sesi `Announcer` üzerinden global tur
kilidini alıyor, yani aktif turun sırasına girmiyor, onunla yarışmıyor.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field

from mayen.data import clock
from mayen.data.repositories.tasks import ScheduledTask, TaskRepository, TaskStatus
from mayen.obs.log import get_logger

log = get_logger(__name__)

type Handler = Callable[[ScheduledTask], Awaitable[str]]
"""Bir görevi koşar ve **sonucunu** döndürür: satıra yazılan `outcome` odur."""


@dataclass(slots=True)
class Recurring:
    """Aralığı olan, satırı olmayan bakım işi (yedekleme gibi).

    İlk koşusu açılışta değil, bir aralık sonra: açılış zaten en yoğun an ve her yeniden
    başlatma bir yedek almak, `keep` penceresini birkaç dakikaya sıkıştırırdı.
    """

    name: str
    interval_seconds: float
    run: Callable[[], Awaitable[None]]
    _next: float | None = field(default=None, repr=False)

    def due(self, monotonic: float) -> bool:
        """Vakti geldi mi. Saat `monotonic`: duvar saatinin geri alınması, bir sonraki
        yedeği saatlerce erteleyebilirdi."""
        if self._next is None:
            self._next = monotonic + self.interval_seconds
            return False
        if monotonic < self._next:
            return False
        self._next = monotonic + self.interval_seconds
        return True


class Scheduler:
    """Tik'leyen taraf. Tik'in kendisi (`tick`) ayrı bir yöntem: uykusuz çağrılabildiği
    için testler saatin geçmesini beklemiyor."""

    def __init__(
        self,
        tasks: TaskRepository,
        handlers: Mapping[str, Handler],
        *,
        tick_seconds: float,
        tolerance_seconds: float,
        recurring: Sequence[Recurring] = (),
    ) -> None:
        self._tasks = tasks
        self._handlers = handlers
        self._tick_seconds = tick_seconds
        self._tolerance_seconds = tolerance_seconds
        self._recurring = list(recurring)
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Açılış taramasını yapar ve döngüyü başlatır."""
        await self.sweep_missed()
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="scheduler")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def sweep_missed(self) -> int:
        """Uygulama kapalıyken vakti geçmiş görevleri karara bağlar (§12).

        Toleransı aşanı düşürür ve **kaç tanesinin düştüğünü döndürür**; içindekileri
        normal yoldan koşturur. Düşürülen her görev kayda geçiyor: sessizce kaybolan bir
        hatırlatıcı, hiç kurulmamış bir hatırlatıcıdan ayırt edilemez.
        """
        dropped = 0
        for task in self._tasks.due():
            if self._lateness(task) > self._tolerance_seconds:
                log.warning(
                    "kaçırılmış görev düşürüldü",
                    task_id=task.id,
                    kind=task.kind,
                    due_at=task.due_at,
                )
                self._tasks.settle(
                    task.id, TaskStatus.DUSURULDU, outcome="tolerans aşıldı, süreç kapalıydı"
                )
                dropped += 1
            else:
                await self._run(task)
        return dropped

    async def tick(self) -> None:
        """Bir tur: vakti gelen görevler, sonra vakti gelen bakım işleri."""
        for task in self._tasks.due():
            await self._run(task)
        monotonic = asyncio.get_running_loop().time()
        for job in self._recurring:
            if not job.due(monotonic):
                continue
            try:
                await job.run()
            except Exception:
                # Yedeğin patlaması zamanlayıcıyı öldürmez: bir sonraki aralıkta yeniden
                # denenir. Sessiz değil — kaydı olmayan bir yedekleme hatası, yedek olduğu
                # sanılan bir dizin demektir (Kural 13).
                log.exception("yinelenen iş başarısız", job=job.name)

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._tick_seconds)
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Tek bir tik'in patlaması zamanlayıcıyı susturmaz; susarsa bir daha hiçbir
                # hatırlatıcı çalmaz ve kimse fark etmez.
                log.exception("zamanlayıcı tik'i başarısız")

    async def _run(self, task: ScheduledTask) -> None:
        handler = self._handlers.get(task.kind)
        if handler is None:
            log.error("tanınmayan görev türü", task_id=task.id, kind=task.kind)
            self._tasks.settle(
                task.id, TaskStatus.DUSURULDU, outcome=f"tanınmayan tür: {task.kind}"
            )
            return
        try:
            outcome = await handler(task)
        except Exception as error:
            log.exception("görev başarısız", task_id=task.id, kind=task.kind)
            self._tasks.settle(
                task.id, TaskStatus.DUSURULDU, outcome=f"{type(error).__name__}: {error}"
            )
            return
        self._tasks.settle(task.id, TaskStatus.CALISTI, outcome=outcome)

    def _lateness(self, task: ScheduledTask) -> float:
        """Görevin kaç saniye geciktiği. Okunamayan damga **sonsuz gecikme** sayılıyor:
        biçimi bozuk bir satırı zamanında saymak, onu bugün çalıştırmak olurdu."""
        try:
            due = clock.parse(task.due_at)
        except ValueError:
            log.error("görevin zaman damgası okunamadı", task_id=task.id, due_at=task.due_at)
            return float("inf")
        return (clock.parse(clock.now()) - due).total_seconds()
