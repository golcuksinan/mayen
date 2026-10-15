"""İş ve zamanlayıcı deposu portu (§11, §12): hatırlatma skill'leri ve zamanlayıcı tetikleyicisi
yalnızca bunu görür."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from mayen.ports.tools import Sensitivity
from mayen.ports.triggers import Priority


class TimerState(StrEnum):
    """Saklanan sözlük; depo CHECK kısıtını buradan kurar (§11.6)."""

    PENDING = "pending"
    FIRED = "fired"  # vadesinde ya da toleransı içinde tur açtı
    MISSED = "missed"  # toleransı aşıldı, "kaçırılanlar" özetine girdi (§12)


@dataclass(frozen=True)
class Timer:
    id: str
    due: datetime
    text: str  # kişinin kendi sözleri; modele aynen gider
    priority: Priority  # sessiz saatlerde yalnızca `urgent` geçer (§12)
    tolerance_s: float  # kapalıyken vadesi geçtiyse en çok bu kadar geç çalar (§12)
    sensitivity: Sensitivity
    person_id: str | None  # kimin hatırlatması; hedef cihaz ondan seçilir (§12)
    state: TimerState


class TimerStore(Protocol):
    def add(
        self,
        due: datetime,
        text: str,
        priority: Priority,
        tolerance_s: float,
        sensitivity: Sensitivity,
        person_id: str | None,
    ) -> Timer: ...

    def get(self, timer_id: str) -> Timer | None:
        """Akıbeti ne olursa olsun; silinmişse `None`."""
        ...

    def pending(self) -> list[Timer]:
        """Bekleyen zamanlayıcılar, vade sırasıyla."""
        ...

    def delete(self, timer_id: str) -> bool:
        """Bekleyen zamanlayıcıyı siler; yoksa ya da artık beklemiyorsa `False`."""
        ...

    def close(self, timer_id: str, state: TimerState) -> None:
        """Bekleyen zamanlayıcının akıbetini yazar; bir kez kapanan bir daha çalmaz."""
        ...
