"""Unut (§11.4): kayıt silinmez, ama LLM'e hiçbir yoldan girmez.

Birim turdur: kişinin sözü, Mayen'in cevabı ve o turdaki tool çağrıları birlikte unutulur;
yalnızca kişinin sözü unutulsaydı onu tekrar eden cevap kalırdı. Tur dışında duyulan söz tek
başına bir kayıttır.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mayen.ports.events import ref
from mayen.ports.transcript import Utterance, UtteranceId
from mayen.ports.triggers import TurnId


@dataclass(frozen=True)
class Forgotten:
    turns: tuple[TurnId, ...] = ()
    utterances: tuple[UtteranceId, ...] = ()  # tur dışında duyulanlar

    def records(self) -> list[str]:
        return [ref("turn", t) for t in self.turns] + [
            ref("utterance", u) for u in self.utterances
        ]

    def __bool__(self) -> bool:
        return bool(self.turns or self.utterances)


class Forgetting(Protocol):
    """Çağrının turuna bağlıdır: süren tur hiçbir seçime girmez."""

    def last(self) -> Forgotten:
        """Kişinin bu turdan önceki son turu; tur dışında duyulan söz sayılmaz."""
        ...

    def period(self, since: datetime, until: datetime) -> Forgotten:
        """`[since, until)` aralığındaki turlar ve tur dışında duyulan sözler."""
        ...


class ForgottenRecords(Protocol):
    """Bir kaydın unutulup unutulmadığı; LLM'e kayıt götüren her yol buna bakar."""

    def turn_forgotten(self, turn_id: TurnId) -> bool: ...

    def utterance_forgotten(self, utterance: Utterance) -> bool:
        """Turdaki söz turuyla, tur dışındaki kendisiyle unutulur."""
        ...


class Tombstones(Protocol):
    """Unut kararlarının veritabanı dışındaki listesi (§11.4): yalnızca kimlikler, içerik yok.

    Veritabanı eski bir yedeğe dönerse unutulan kayıt LLM'e geri gelirdi; liste dışarıda durduğu
    için geri yüklemeden etkilenmez ve açılışta yeniden uygulanır.
    """

    def read(self) -> list[str]: ...

    def add(self, records: Sequence[str]) -> None:
        """Diske yazılmış olarak döner: karar veritabanına bundan sonra girer."""
        ...
