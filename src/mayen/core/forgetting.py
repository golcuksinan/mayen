"""Unut (§11.4): neyin unutulacağını seçer, kararı kaydeder, bilmesi gerekenlere bildirir.

Karar iki yere yazılır, ikisinde de içerik değil yalnızca kimlikler: önce veritabanı dışındaki
mezar taşı listesine, sonra olay kaydına `record.forgotten` olarak. Açılışta ikisi
karşılaştırılır ve birinde eksik olan öbürüne eklenir: eski bir yedeğe dönen veritabanı
kararı listeden geri alır (§11.4). Bildirim alanlar, kaydı LLM'e götürebilecek yerlerdir:
oturumların canlı bağlamı.
"""

import logging
from collections.abc import Callable
from datetime import datetime

from mayen.core.events import Recorder
from mayen.ports.events import EventKind, EventLog, ref
from mayen.ports.forget import Forgotten, Tombstones
from mayen.ports.tools import Status
from mayen.ports.transcript import Party, TranscriptStore, Utterance, UtteranceId
from mayen.ports.triggers import TurnId

type Listener = Callable[[Forgotten], None]

log = logging.getLogger(__name__)


class ForgetError(RuntimeError):
    """Karar kaydedildi ama bir oturumun canlı bağlamından çıkarılamadı."""


class Forgetter:
    def __init__(
        self,
        transcript: TranscriptStore,
        events: EventLog,
        recorder: Recorder,
        tombstones: Tombstones,
        recorded: Callable[[], list[str]],
    ) -> None:
        """`recorded`, olay kaydındaki kararların kimlikleridir."""
        self._transcript = transcript
        self._events = events
        self._recorder = recorder
        self._tombstones = tombstones
        self._listeners: dict[str, Listener] = {}
        listed = dict.fromkeys(tombstones.read())
        known = dict.fromkeys(recorded())
        tombstones.add([r for r in known if r not in listed])
        missing = [r for r in listed if r not in known]
        if missing:
            # Liste veritabanından ileride: veritabanı eski bir hâline dönmüş.
            self._record(None, None, {"restored": len(missing)}, missing)
        self._forgotten = {*listed, *known}

    def attach(self, session: str, listener: Listener) -> None:
        self._listeners[session] = listener

    def detach(self, session: str) -> None:
        self._listeners.pop(session, None)

    def turn_forgotten(self, turn_id: TurnId) -> bool:
        return ref("turn", turn_id) in self._forgotten

    def utterance_forgotten(self, utterance: Utterance) -> bool:
        if utterance.turn_id is not None:
            return self.turn_forgotten(utterance.turn_id)
        return ref("utterance", utterance.id) in self._forgotten

    def bound(self, session: str, current: TurnId | None) -> "BoundForgetting":
        return BoundForgetting(self, session, current)

    def last(self, session: str, current: TurnId | None) -> Forgotten:
        """Kişinin bu turdan önceki son turu. Tur dışında duyulan söz sayılmaz: komuttan hemen
        önce kaçırılan bir wake word ("Hey Mayen") tur dışı bir sözdür ve onu seçmek, asıl
        unutulmak isteneni bırakırdı."""
        until = self._started(current)
        for u in reversed(self._transcript.read(until=until)):
            t = u.turn_id
            if u.party is not Party.PERSON or t is None or t == current:
                continue
            if self.turn_forgotten(t):
                continue
            return self._apply(session, current, Forgotten(turns=(t,)))
        return Forgotten()

    def period(
        self, session: str, current: TurnId | None, since: datetime, until: datetime
    ) -> Forgotten:
        turns: dict[TurnId, None] = {}
        utterances: dict[UtteranceId, None] = {}
        for u in self._transcript.read(since=since, until=until):
            if self.utterance_forgotten(u):
                continue
            if u.turn_id is None:
                utterances[u.id] = None
            elif u.turn_id != current:
                turns[u.turn_id] = None
        # Sözü olmayan tur da (sessiz bir hatırlatma gibi) aralıktadır.
        for e in self._events.read(since=since, until=until):
            t = e.header.turn_id
            started = e.header.kind is EventKind.TURN_STARTED
            if started and t is not None and t != current and not self.turn_forgotten(t):
                turns[t] = None
        return self._apply(session, current, Forgotten(tuple(turns), tuple(utterances)))

    def _started(self, current: TurnId | None) -> datetime:
        if current is not None:
            for e in self._events.read(turn_id=current):
                if e.header.kind is EventKind.TURN_STARTED and e.header.turn_id == current:
                    return e.header.time
        return self._recorder.clock.now()

    def _apply(self, session: str, current: TurnId | None, chosen: Forgotten) -> Forgotten:
        if not chosen:
            return chosen
        records = chosen.records()
        self._tombstones.add(records)
        body = {"turns": len(chosen.turns), "utterances": len(chosen.utterances)}
        self._record(session, current, body, records)
        self._forgotten.update(records)
        # Bir oturumdaki hata ötekileri bekletmez; ama sessiz de kalmaz: o bağlam unutulanı
        # hâlâ taşıyor olabilir.
        failed = []
        for session_of, listener in list(self._listeners.items()):
            try:
                listener(chosen)
            except Exception:
                log.exception("could not forget in session %s", session_of)
                failed.append(session_of)
        if failed:
            raise ForgetError(f"recorded, but still in {len(failed)} live sessions")
        return chosen

    def _record(
        self,
        session: str | None,
        current: TurnId | None,
        body: dict[str, int],
        records: list[str],
    ) -> None:
        self._recorder.emit(
            EventKind.RECORD_FORGOTTEN,
            __name__,
            body,
            session=session,
            turn_id=current,
            status=Status.OK,
            related=records,
        )


class BoundForgetting:
    """Bir çağrının gördüğü unut: oturumu ve süren turu bağlıdır (`ports.forget.Forgetting`)."""

    def __init__(self, forgetter: Forgetter, session: str, current: TurnId | None) -> None:
        self._forgetter = forgetter
        self._session = session
        self._current = current

    def last(self) -> Forgotten:
        return self._forgetter.last(self._session, self._current)

    def period(self, since: datetime, until: datetime) -> Forgotten:
        return self._forgetter.period(self._session, self._current, since, until)
