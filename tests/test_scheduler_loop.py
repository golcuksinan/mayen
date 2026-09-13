"""Zamanlayıcı: vakti gelen görev, kaçırılmış görev toleransı, yinelenen bakım işi (§12)."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mayen.data import clock
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.tasks import ScheduledTask, TaskRepository, TaskStatus
from mayen.scheduler.loop import Recurring, Scheduler

KIND = "reminder"


@pytest.fixture
def tasks(tmp_path: Path) -> TaskRepository:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    return TaskRepository(database)


def _stamp(*, minutes: float) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).strftime(clock.FORMAT)


def _scheduler(
    tasks: TaskRepository,
    ran: list[str],
    *,
    tolerance_seconds: float = 1800.0,
    fails: bool = False,
    recurring: list[Recurring] | None = None,
) -> Scheduler:
    async def handler(task: ScheduledTask) -> str:
        if fails:
            raise RuntimeError("ses yok")
        ran.append(str(task.payload["message"]))
        return "seslendirildi"

    return Scheduler(
        tasks,
        {KIND: handler},
        tick_seconds=0.01,
        tolerance_seconds=tolerance_seconds,
        recurring=recurring or [],
    )


async def test_due_task_runs_and_is_settled(tasks: TaskRepository) -> None:
    task = tasks.create(KIND, {"message": "ilaç"}, _stamp(minutes=-1))
    ran: list[str] = []

    await _scheduler(tasks, ran).tick()

    assert ran == ["ilaç"]
    assert tasks.pending() == []
    settled = tasks.settle(task.id, TaskStatus.IPTAL)
    assert settled is None, "çalışmış görev ikinci kez sonlandırılamaz"


async def test_future_task_is_left_alone(tasks: TaskRepository) -> None:
    tasks.create(KIND, {"message": "sonra"}, _stamp(minutes=30))
    ran: list[str] = []

    await _scheduler(tasks, ran).tick()

    assert ran == []
    assert len(tasks.pending()) == 1


async def test_missed_task_within_tolerance_runs(tasks: TaskRepository) -> None:
    tasks.create(KIND, {"message": "kısa kesinti"}, _stamp(minutes=-5))
    ran: list[str] = []

    dropped = await _scheduler(tasks, ran, tolerance_seconds=600).sweep_missed()

    assert dropped == 0
    assert ran == ["kısa kesinti"]


async def test_missed_task_beyond_tolerance_is_dropped_and_recorded(
    tasks: TaskRepository,
) -> None:
    """Sessizce silinmiyor: `DUSURULDU` bir durum ve sebebi satırda (§12, Kural 13)."""
    task = tasks.create(KIND, {"message": "dün"}, _stamp(minutes=-600))
    ran: list[str] = []

    dropped = await _scheduler(tasks, ran, tolerance_seconds=600).sweep_missed()

    assert dropped == 1
    assert ran == []
    settled = tasks.settle(task.id, TaskStatus.IPTAL)
    assert settled is None
    assert tasks.pending() == []


async def test_tolerance_applies_only_at_startup(tasks: TaskRepository) -> None:
    """Süreç ayaktayken geciken görev düşmez — tolerans açılışın kuralı."""
    tasks.create(KIND, {"message": "geciken"}, _stamp(minutes=-600))
    ran: list[str] = []

    await _scheduler(tasks, ran, tolerance_seconds=60).tick()

    assert ran == ["geciken"]


async def test_failed_task_is_settled_not_retried(tasks: TaskRepository) -> None:
    tasks.create(KIND, {"message": "patlar"}, _stamp(minutes=-1))
    ran: list[str] = []
    scheduler = _scheduler(tasks, ran, fails=True)

    await scheduler.tick()
    await scheduler.tick()

    assert ran == []
    assert tasks.pending() == [], "patlayan görev BEKLIYOR kalmıyor, sonsuza kadar denenmiyor"


async def test_unknown_kind_is_settled_not_skipped(tasks: TaskRepository) -> None:
    tasks.create("bilinmeyen", {"message": "?"}, _stamp(minutes=-1))
    ran: list[str] = []

    await _scheduler(tasks, ran).tick()

    assert tasks.pending() == []


async def test_unreadable_stamp_counts_as_missed(tasks: TaskRepository) -> None:
    """Biçimi bozuk damgayı zamanında saymak, onu bugün çalıştırmak olurdu.

    Damga elle düzenlenmiş bir satırdan gelebilir; `due()` yalnızca dizi karşılaştırması
    yaptığı için okunamayan bir değer pekâlâ "vakti gelmiş" görünebilir.
    """
    tasks.create(KIND, {"message": "bozuk"}, "2020-13-45T99:99:99Z")
    ran: list[str] = []

    dropped = await _scheduler(tasks, ran).sweep_missed()

    assert dropped == 1
    assert ran == []


async def test_recurring_job_waits_one_interval_then_runs(tasks: TaskRepository) -> None:
    runs: list[int] = []

    async def backup() -> None:
        runs.append(1)

    job = Recurring(name="backup", interval_seconds=0.0, run=backup)
    scheduler = _scheduler(tasks, [], recurring=[job])

    await scheduler.tick()
    assert runs == [], "ilk tik açılışa denk gelir; her yeniden başlatma yedek almamalı"

    await scheduler.tick()
    assert runs == [1]


async def test_recurring_failure_does_not_stop_the_scheduler(tasks: TaskRepository) -> None:
    tasks.create(KIND, {"message": "yine de çalış"}, _stamp(minutes=-1))
    ran: list[str] = []

    async def broken() -> None:
        raise OSError("disk dolu")

    job = Recurring(name="backup", interval_seconds=0.0, run=broken)
    job.due(0.0)  # ilk aralığı geç
    scheduler = _scheduler(tasks, ran, recurring=[job])

    await scheduler.tick()

    assert ran == ["yine de çalış"]


async def test_start_sweeps_then_loops(tasks: TaskRepository) -> None:
    tasks.create(KIND, {"message": "açılışta"}, _stamp(minutes=-1))
    tasks.create(KIND, {"message": "koşarken"}, _stamp(minutes=0))
    ran: list[str] = []
    scheduler = _scheduler(tasks, ran)

    await scheduler.start()
    try:
        async with asyncio.timeout(5.0):
            while len(ran) < 2:
                await asyncio.sleep(0.01)
    finally:
        await scheduler.stop()

    assert set(ran) == {"açılışta", "koşarken"}
