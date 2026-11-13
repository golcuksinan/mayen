"""Unut ve sil (§11.4): neyin seçileceği, kararın nereye yazılacağı, kimin haber alacağı.

Seçim ikisinde aynıdır: kişinin son turu ya da bir zaman aralığı; süren tur hiçbir seçime
girmez. Karar iki yere yazılır, ikisinde de içerik değil yalnızca kimlikler: önce veritabanı
dışındaki mezar taşı listesine, sonra olay kaydına (`record.forgotten`, `record.deleted`).
Açılışta ikisi karşılaştırılır ve birinde eksik olan öbürüne eklenir; eski bir yedeğe dönen
veritabanı kararı listeden geri alır, silinmiş kayıt yeniden silinir. Haber alanlar kaydı LLM'e
götürebilecek yerlerdir: oturumların canlı bağlamı.
"""

import logging
from collections.abc import Callable, Iterable
from datetime import datetime
from uuid import UUID

from mayen.core.events import Recorder
from mayen.ports.events import EventKind, EventLog, ref
from mayen.ports.forget import (
    Action,
    Chosen,
    RecordEraser,
    Recordings,
    Tombstone,
    Tombstones,
)
from mayen.ports.tools import Status
from mayen.ports.transcript import Party, TranscriptStore, Utterance, UtteranceId
from mayen.ports.triggers import TurnId

type Listener = Callable[[Chosen], None]

log = logging.getLogger(__name__)

_KIND = {Action.FORGET: EventKind.RECORD_FORGOTTEN, Action.DELETE: EventKind.RECORD_DELETED}


class EraseError(RuntimeError):
    """Karar kaydedildi ama bir oturumun canlı bağlamından çıkarılamadı."""


class Erasure:
    def __init__(
        self,
        transcript: TranscriptStore,
        events: EventLog,
        recorder: Recorder,
        tombstones: Tombstones,
        recorded: Callable[[EventKind], list[str]],
        eraser: RecordEraser,
        recordings: Recordings,
    ) -> None:
        """`recorded`, olay kaydında o türdeki kararların kimlikleridir."""
        self._transcript = transcript
        self._events = events
        self._recorder = recorder
        self._tombstones = tombstones
        self._eraser = eraser
        self._recordings = recordings
        self._listeners: dict[str, Listener] = {}
        self._forgotten: set[str] = set()
        listed = tombstones.read()
        for action in Action:
            self._reconcile(action, [t.record for t in listed if t.action is action], recorded)

    def _reconcile(
        self,
        action: Action,
        listed: list[str],
        recorded: Callable[[EventKind], list[str]],
    ) -> None:
        known = dict.fromkeys(recorded(_KIND[action]))
        on_list = dict.fromkeys(listed)
        self._tombstones.add([Tombstone(action, r) for r in known if r not in on_list])
        missing = [r for r in on_list if r not in known]
        if action is Action.DELETE and on_list:
            # Silinmiş olan yeniden silinir: veritabanı eski bir hâline dönmüş olabilir. Hiçbir
            # şey bulunmazsa sorgu boşa gider, karar değişmez.
            turns, utterances = _split(on_list)
            erased = self._eraser.erase(turns, utterances)
            if erased.utterances or erased.events:
                log.warning("deleted records came back with the database; deleted again")
        if missing:
            # Liste veritabanından ileride: veritabanı eski bir hâline dönmüş.
            self._record(_KIND[action], None, None, {"restored": len(missing)}, missing)
        self._forgotten.update(known)
        self._forgotten.update(on_list)

    # --- oturumlar ---

    def attach(self, session: str, listener: Listener) -> None:
        self._listeners[session] = listener

    def detach(self, session: str) -> None:
        self._listeners.pop(session, None)

    # --- sorular (`ports.forget.ForgottenRecords`) ---

    def turn_forgotten(self, turn_id: TurnId) -> bool:
        return ref("turn", turn_id) in self._forgotten

    def utterance_forgotten(self, utterance: Utterance) -> bool:
        if utterance.turn_id is not None:
            return self.turn_forgotten(utterance.turn_id)
        return ref("utterance", utterance.id) in self._forgotten

    # --- kararlar ---

    def bound(self, action: Action, session: str, current: TurnId | None) -> "Bound":
        return Bound(self, action, session, current)

    def forget_last(self, session: str, current: TurnId | None) -> Chosen:
        return self._forget(session, current, self._last(current, skip_forgotten=True))

    def forget_period(
        self, session: str, current: TurnId | None, since: datetime, until: datetime
    ) -> Chosen:
        chosen = self._period(current, since, until, skip_forgotten=True)
        return self._forget(session, current, chosen)

    def delete_last(self, session: str, current: TurnId | None) -> Chosen:
        # Unutulmuş tur da silinebilir: unut kaydı bırakır, sil götürür.
        return self._delete(session, current, self._last(current, skip_forgotten=False), None)

    def delete_period(
        self, session: str, current: TurnId | None, since: datetime, until: datetime
    ) -> Chosen:
        chosen = self._period(current, since, until, skip_forgotten=False)
        return self._delete(session, current, chosen, (since, until))

    # --- seçim ---

    def _last(self, current: TurnId | None, *, skip_forgotten: bool) -> Chosen:
        """Kişinin bu turdan önceki son turu. Tur dışında duyulan söz sayılmaz: komuttan hemen
        önce kaçırılan bir wake word ("Hey Mayen") tur dışı bir sözdür ve onu seçmek, asıl
        unutulmak isteneni bırakırdı."""
        until = self._started(current)
        for u in reversed(self._transcript.read(until=until)):
            t = u.turn_id
            if u.party is not Party.PERSON or t is None or t == current:
                continue
            if skip_forgotten and self.turn_forgotten(t):
                continue
            return Chosen(turns=(t,))
        return Chosen()

    def _period(
        self, current: TurnId | None, since: datetime, until: datetime, *, skip_forgotten: bool
    ) -> Chosen:
        turns: dict[TurnId, None] = {}
        utterances: dict[UtteranceId, None] = {}
        for u in self._transcript.read(since=since, until=until):
            if skip_forgotten and self.utterance_forgotten(u):
                continue
            if u.turn_id is None:
                utterances[u.id] = None
            elif u.turn_id != current:
                turns[u.turn_id] = None
        # Sözü olmayan tur da (sessiz bir hatırlatma gibi) aralıktadır.
        for e in self._events.read(since=since, until=until):
            t = e.header.turn_id
            started = e.header.kind is EventKind.TURN_STARTED
            if not started or t is None or t == current:
                continue
            if not (skip_forgotten and self.turn_forgotten(t)):
                turns[t] = None
        return Chosen(tuple(turns), tuple(utterances))

    def _started(self, current: TurnId | None) -> datetime:
        if current is not None:
            for e in self._events.read(turn_id=current):
                if e.header.kind is EventKind.TURN_STARTED and e.header.turn_id == current:
                    return e.header.time
        return self._recorder.clock.now()

    # --- uygulama ---

    def _forget(self, session: str, current: TurnId | None, chosen: Chosen) -> Chosen:
        if not chosen:
            return chosen
        records = chosen.records()
        self._tombstones.add([Tombstone(Action.FORGET, r) for r in records])
        body = {"turns": len(chosen.turns), "utterances": len(chosen.utterances)}
        self._record(EventKind.RECORD_FORGOTTEN, session, current, body, records)
        self._forgotten.update(records)
        self._notify(chosen)
        return chosen

    def _delete(
        self,
        session: str,
        current: TurnId | None,
        chosen: Chosen,
        span: tuple[datetime, datetime] | None,
    ) -> Chosen:
        if not chosen:
            return chosen
        records = chosen.records()
        self._tombstones.add([Tombstone(Action.DELETE, r) for r in records])
        erased = self._eraser.erase(chosen.turns, chosen.utterances)
        names = [r.removeprefix("recording:") for r in erased.recordings]
        files = self._recordings.delete(names)
        if span is not None:
            # Söze bağlanmadan yazılmış eski kayıtlar da aralıktadır; adları zamanlarıdır.
            files += self._recordings.delete_between(*span)
        body = {
            "turns": len(chosen.turns),
            "utterances": erased.utterances,
            "events": erased.events,
            "files": files,
        }
        self._record(EventKind.RECORD_DELETED, session, current, body, records)
        self._forgotten.update(records)
        self._notify(chosen)
        return chosen

    def _notify(self, chosen: Chosen) -> None:
        # Bir oturumdaki hata ötekileri bekletmez; ama sessiz de kalmaz: o bağlam seçileni
        # hâlâ taşıyor olabilir.
        failed = []
        for session, listener in list(self._listeners.items()):
            try:
                listener(chosen)
            except Exception:
                log.exception("could not drop chosen records in session %s", session)
                failed.append(session)
        if failed:
            raise EraseError(f"recorded, but still in {len(failed)} live sessions")

    def _record(
        self,
        kind: EventKind,
        session: str | None,
        current: TurnId | None,
        body: dict[str, int],
        records: list[str],
    ) -> None:
        self._recorder.emit(
            kind,
            __name__,
            body,
            session=session,
            turn_id=current,
            status=Status.OK,
            related=records,
        )


def _split(records: Iterable[str]) -> tuple[list[TurnId], list[UtteranceId]]:
    turns: list[TurnId] = []
    utterances: list[UtteranceId] = []
    for r in records:
        store, _, raw = r.partition(":")
        if store == "turn":
            turns.append(TurnId(UUID(raw)))
        elif store == "utterance":
            utterances.append(UtteranceId(UUID(raw)))
    return turns, utterances


class Bound:
    """Bir çağrının gördüğü unut ya da sil (`ports.forget.Erasing`): oturumu ve süren turu
    bağlıdır."""

    def __init__(
        self, erasure: Erasure, action: Action, session: str, current: TurnId | None
    ) -> None:
        self._erasure = erasure
        self._action = action
        self._session = session
        self._current = current

    def last(self) -> Chosen:
        if self._action is Action.DELETE:
            return self._erasure.delete_last(self._session, self._current)
        return self._erasure.forget_last(self._session, self._current)

    def period(self, since: datetime, until: datetime) -> Chosen:
        if self._action is Action.DELETE:
            return self._erasure.delete_period(self._session, self._current, since, until)
        return self._erasure.forget_period(self._session, self._current, since, until)
