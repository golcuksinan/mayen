"""Unut ve sil (§11.4).

Unutulan kayıt silinmez, ama LLM'e hiçbir yoldan girmez; silinen kayıt bütün kopyalarıyla
gider. Birim turdur: kişinin sözü, Mayen'in cevabı ve o turdaki tool çağrıları birlikte seçilir;
yalnızca kişinin sözü seçilseydi onu tekrar eden cevap kalırdı. Tur dışında duyulan söz tek
başına bir kayıttır.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from mayen.ports.events import ref
from mayen.ports.transcript import Utterance, UtteranceId
from mayen.ports.triggers import TurnId


@dataclass(frozen=True)
class Chosen:
    """Unutulmak ya da silinmek üzere seçilen kayıtlar."""

    turns: tuple[TurnId, ...] = ()
    utterances: tuple[UtteranceId, ...] = ()  # tur dışında duyulanlar

    def records(self) -> list[str]:
        return [ref("turn", t) for t in self.turns] + [
            ref("utterance", u) for u in self.utterances
        ]

    def __bool__(self) -> bool:
        return bool(self.turns or self.utterances)


class Erasing(Protocol):
    """Skill'in gördüğü unut ya da sil; çağrının turuna bağlıdır: süren tur hiçbir seçime
    girmez."""

    def last(self) -> Chosen:
        """Kişinin bu turdan önceki son turu; tur dışında duyulan söz sayılmaz."""
        ...

    def period(self, since: datetime, until: datetime) -> Chosen:
        """`[since, until)` aralığındaki turlar ve tur dışında duyulan sözler."""
        ...


class ForgottenRecords(Protocol):
    """Bir kaydın unutulup unutulmadığı; LLM'e kayıt götüren her yol buna bakar."""

    def turn_forgotten(self, turn_id: TurnId) -> bool: ...

    def utterance_forgotten(self, utterance: Utterance) -> bool:
        """Turdaki söz turuyla, tur dışındaki kendisiyle unutulur."""
        ...


class Action(StrEnum):
    """Mezar taşının kararı; saklanan sözlüktür."""

    FORGET = "forget"
    DELETE = "delete"


@dataclass(frozen=True)
class Tombstone:
    action: Action
    record: str  # `turn:<kimlik>` ya da `utterance:<kimlik>`; içerik asla


class Tombstones(Protocol):
    """Unut ve sil kararlarının veritabanı dışındaki listesi (§11.4): yalnızca kimlikler.

    Veritabanı eski bir yedeğe dönerse unutulan ya da silinen kayıt geri gelirdi; liste dışarıda
    durduğu için geri yüklemeden etkilenmez ve açılışta yeniden uygulanır.
    """

    def read(self) -> list[Tombstone]: ...

    def add(self, tombstones: Sequence[Tombstone]) -> None:
        """Diske yazılmış olarak döner: karar veritabanına bundan sonra girer."""
        ...


@dataclass(frozen=True)
class Erased:
    """Bir silmenin veritabanında bulduğu: kaç söz ve olay gitti, sözlerin ses kayıtları."""

    utterances: int = 0
    events: int = 0
    recordings: tuple[str, ...] = ()  # `recording:<ad>`; dosyaları ayrı port siler


class RecordEraser(Protocol):
    """Kayıtları ve olay kaydındaki kopyalarını siler; unut ve sil kararlarının olaylarına
    dokunmaz, onlar yalnızca kimlik taşır."""

    def erase(self, turns: Sequence[TurnId], utterances: Sequence[UtteranceId]) -> Erased: ...


# Sözün ses kaydının adı: yazıldığı yerel zaman. Aralıkla silme dosyayı adından bulur; söze
# bağlı olmayan eski kayıtlar da böyle bulunur.
RECORDING_NAME = "%Y%m%d-%H%M%S-%f"


class Recordings(Protocol):
    """Sözlerin ses kayıtları (§6): sesi ve metni dosyadadır, silinen sözle gider."""

    def delete(self, names: Sequence[str]) -> int:
        """Bu adlı kayıtların dosyaları; silinen dosya sayısı."""
        ...

    def delete_between(self, since: datetime, until: datetime) -> int:
        """`[since, until)` aralığında yazılmış kayıtların dosyaları; silinen dosya sayısı."""
        ...
