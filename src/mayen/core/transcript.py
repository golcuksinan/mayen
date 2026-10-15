"""Transkripte yazma (§11): sözün kimliğini ve zamanını çekirdek verir, ortak saatten."""

import uuid

from mayen.ports.events import Clock
from mayen.ports.tools import Caller
from mayen.ports.transcript import Party, TranscriptStore, Utterance, UtteranceId
from mayen.ports.triggers import TurnId


class Transcript:
    """Sözleri transkripte yazar. Loga hiçbir şey yazmaz: metin içeriktir (§14)."""

    def __init__(self, store: TranscriptStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def heard(
        self, session: str, turn_id: TurnId | None, speaker: Caller, text: str
    ) -> Utterance:
        """Bir kişinin sözü ya da yazısı."""
        return self._append(session, turn_id, Party.PERSON, speaker, text, interrupted=False)

    def said(
        self, session: str, turn_id: TurnId | None, text: str, *, interrupted: bool
    ) -> Utterance:
        """Mayen'in sözü."""
        return self._append(session, turn_id, Party.ASSISTANT, None, text, interrupted)

    def _append(
        self,
        session: str,
        turn_id: TurnId | None,
        party: Party,
        speaker: Caller | None,
        text: str,
        interrupted: bool,
    ) -> Utterance:
        utterance = Utterance(
            id=UtteranceId(uuid.uuid4()),
            time=self._clock.now(),
            session=session,
            turn_id=turn_id,
            party=party,
            role=None if speaker is None else speaker.role,
            person_id=None if speaker is None else speaker.person_id,
            text=text,
            interrupted=interrupted,
        )
        self._store.append(utterance)
        return utterance
