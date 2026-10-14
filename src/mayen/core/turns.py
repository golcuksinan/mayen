"""Tetikleyiciden tura: kesme ve kuyruk politikası (§5.2, §5.3); uygulanışı `pipeline`'dadır."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import Fate, Priority, Trigger, TriggerSource, TurnId

# Hatta karşılığı olan akıbetler; kaldığı yerden devam ödünç alınan çerçevede yok (§5.3).
SUPPORTED_FATES = frozenset({Fate.CANCEL, Fate.RESTART})


class TurnConfigError(ValueError):
    """Kuyruk ayarları tutarsız; açılışta yükselir."""


@dataclass(frozen=True)
class Turn:
    id: TurnId
    trigger: Trigger


def new_turn(trigger: Trigger) -> Turn:
    return Turn(TurnId(uuid.uuid4()), trigger)


def interrupts(current: Turn, incoming: Priority) -> bool:
    """Bu öncelikte gelen tetikleyici süren turu keser mi, yoksa sıraya mı girer (§5.3)."""
    if incoming.rank <= current.trigger.priority.rank:
        return False
    owner_speaking = (
        current.trigger.source is TriggerSource.VOICE
        and current.trigger.requester.role is Role.OWNER
    )
    # Sahibin kendi turunu yalnızca acil bir durum böler.
    return not owner_speaking or incoming is Priority.URGENT


@dataclass(frozen=True)
class Start:
    """Bu tur şimdi başlar."""

    turn: Turn


@dataclass(frozen=True)
class Interrupt:
    """Bu turun işleri ve ses parçaları düşer (§5.3); `fate` iptalse bağlama not düşer."""

    turn: Turn
    fate: Fate


type Action = Start | Interrupt


@dataclass
class _Waiting:
    turn: Turn
    order: int


@dataclass
class Turns:
    """Oturumların süren turları ve bekleyen tetikleyicileri.

    Oturum başına en çok bir tur sürer; aynı anda süren tur sayısı `max_running`'dir (§5.2).
    Bekleyenler öncelik sırasıyla, aynı öncelikte geliş sırasıyla başlar.
    """

    fates: Mapping[TriggerSource, Fate]
    max_running: int = 1
    _running: dict[str, Turn] = field(default_factory=dict, init=False)
    _waiting: list[_Waiting] = field(default_factory=list, init=False)
    _arrivals: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        missing = set(TriggerSource) - self.fates.keys()
        if missing:
            # Sessiz bir varsayılan, kesilen turun ne olacağını config'i okuyana söylemez.
            raise TurnConfigError(f"no fate for sources {sorted(missing)}")
        unsupported = {s for s, f in self.fates.items() if f not in SUPPORTED_FATES}
        if unsupported:
            raise TurnConfigError(
                f"fate not supported by the pipeline for {sorted(unsupported)}"
            )
        if self.max_running < 1:
            raise TurnConfigError("max_running must be at least 1")

    def running(self, session: str) -> Turn | None:
        return self._running.get(session)

    def waiting(self, session: str) -> list[Turn]:
        return [
            w.turn
            for w in sorted(self._waiting, key=self._key)
            if w.turn.trigger.session == session
        ]

    def hears(self, session: str, voice: Priority) -> bool:
        """Bu oturumda şimdi söylenen söz duyulur mu.

        Sesli tetikleyici de §5.3'e uyar; ama sıraya alınamaz, duyulmayan söz yeniden
        söylenir. Süren sesli tur ise konuşmanın kendisidir: içindeki söz kesme ödünç alınan
        çerçevenindir (§5.4) ve yeni bir tetikleyici sayılmaz.
        """
        current = self._running.get(session)
        if current is None:
            return len(self._running) < self.max_running
        return current.trigger.source is TriggerSource.VOICE or interrupts(current, voice)

    def identify(self, session: str, requester: Caller) -> None:
        """Sesli turun sahibi ancak ilk segment tanınınca bilinir; kesme kuralı ona bakar."""
        current = self._running.get(session)
        if current is not None and current.trigger.source is TriggerSource.VOICE:
            trigger = replace(current.trigger, requester=requester)
            self._running[session] = replace(current, trigger=trigger)

    def submit(self, trigger: Trigger) -> list[Action]:
        turn = new_turn(trigger)
        current = self._running.get(trigger.session)
        if current is not None and interrupts(current, trigger.priority):
            fate = self.fates[current.trigger.source]
            if fate is Fate.RESTART:
                # Baştan başlayan tur yeni bir kimlik alır: eski koşunun geç gelen parçaları
                # yeni koşuya karışmasın diye düşürme kimliğe göredir.
                self._enqueue(new_turn(current.trigger), front=True)
            self._running[trigger.session] = turn
            return [Interrupt(current, fate), Start(turn)]
        self._enqueue(turn)
        return self._fill()

    def finished(self, turn_id: TurnId) -> list[Action]:
        """Tur kendiliğinden bitti; yeri bekleyenlerden birine geçer."""
        for session, turn in list(self._running.items()):
            if turn.id == turn_id:
                del self._running[session]
        return self._fill()

    def drop(self, session: str) -> list[Action]:
        """Oturum kapandı: süren ve bekleyen turları onunla gider, yeri başkasına geçer."""
        self._running.pop(session, None)
        self._waiting = [w for w in self._waiting if w.turn.trigger.session != session]
        return self._fill()

    def _enqueue(self, turn: Turn, *, front: bool = False) -> None:
        # Öne alınan tur kendi önceliğindekilerin önüne geçer, daha yükseklerin değil.
        self._arrivals += 1
        self._waiting.append(_Waiting(turn, -self._arrivals if front else self._arrivals))

    @staticmethod
    def _key(w: _Waiting) -> tuple[int, int]:
        return (-w.turn.trigger.priority.rank, w.order)

    def _fill(self) -> list[Action]:
        started: list[Action] = []
        for w in sorted(self._waiting, key=self._key):
            if len(self._running) >= self.max_running:
                break
            session = w.turn.trigger.session
            if session in self._running:
                continue
            self._waiting.remove(w)
            self._running[session] = w.turn
            started.append(Start(w.turn))
        return started
