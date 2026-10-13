"""Vadesi gelen zamanlayıcılar ve gecikme toleransı (§12).

Kural tektir, açılışta da çalışırken de: vadesi geçen bir zamanlayıcı toleransı içindeyse bir
kez çalar, aştıysa "kaçırılanlar" özetine girer. Mayen kapalıyken, makine uykudayken ya da
hiçbir cihaz bağlı değilken geçen süre aynı şekilde sayılır; üçü için ayrı bir yol olsaydı
biri unutulurdu.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from mayen.ports.events import Clock
from mayen.ports.timers import Timer, TimerState, TimerStore
from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import Trigger, TriggerSource

# Kimse konuşmadan açılan tur (§10.2); yetkisi tetikleyici kaynağına göre config'tedir.
SYSTEM = Caller(Role.SYSTEM, None, has_personal_device=False)

# Modele giden yerel zaman; `time` skill'inin biçimiyle aynı, model ikisini karşılaştırır.
LOCAL_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class Due:
    fire: list[Timer]
    missed: list[Timer]


def sort_due(pending: Sequence[Timer], now: datetime) -> Due:
    """Vadesi gelenleri çalacaklar ve kaçırılanlar diye ayırır; vadesi gelmeyen dışarıda."""
    fire: list[Timer] = []
    missed: list[Timer] = []
    for timer in pending:
        if timer.due > now:
            continue
        late = now - timer.due
        (fire if late <= timedelta(seconds=timer.tolerance_s) else missed).append(timer)
    return Due(fire, missed)


def local(moment: datetime) -> str:
    """Makinenin saat dilimiyle: ayrı bir ayar, sistem saatiyle ayrışan ikinci gerçek olurdu."""
    return moment.astimezone().strftime(LOCAL_FORMAT)


class TimerDispatcher:
    """Vadesi gelenleri tetikleyici olarak gönderir ve akıbetlerini depoya yazar.

    Akıbet gönderimden sonra yazılır: gönderilemeyen zamanlayıcı beklemede kalır ve bir
    sonraki bakışta yeniden denenir. Hedef oturum yoksa hiçbir şey gönderilmez (§12: hiçbir
    cihaz bağlı değilse kuyruklanır).
    """

    def __init__(
        self,
        store: TimerStore,
        clock: Clock,
        submit: Callable[[Trigger], Awaitable[None]],
        target: Callable[[], str | None],
    ) -> None:
        self._store = store
        self._clock = clock
        self._submit = submit
        self._target = target

    async def dispatch(self) -> None:
        session = self._target()
        if session is None:
            return
        due = sort_due(self._store.pending(), self._clock.now())
        for timer in due.fire:
            await self._submit(
                Trigger(
                    session,
                    timer.priority,
                    TriggerSource.TIMER,
                    timer.text,
                    SYSTEM,
                    {"due": local(timer.due)},
                )
            )
            self._store.close(timer.id, TimerState.FIRED)
        if due.missed:
            # Tek özet: uzun bir kapanıştan sonra hatırlatmalar art arda çalmasın (§12).
            missed: list[dict[str, Any]] = [
                {"text": t.text, "due": local(t.due)} for t in due.missed
            ]
            priority = max((t.priority for t in due.missed), key=lambda p: p.rank)
            await self._submit(
                Trigger(session, priority, TriggerSource.TIMER, "", SYSTEM, {"missed": missed})
            )
            for timer in due.missed:
                self._store.close(timer.id, TimerState.MISSED)
