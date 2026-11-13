"""Mezar taşı listesi (§11.4) bir metin dosyasında: satır başına bir karar, `<karar> <kimlik>`.

Dosya yalnızca büyür; satır silinmez. Yazma, karar veritabanına girmeden önce diske indirilir:
arada süreç ölürse açılış kararı listeden yeniden uygular, tersi olsaydı karar kaybolurdu.
"""

import os
from collections.abc import Sequence
from pathlib import Path

from mayen.ports.forget import Action, Tombstone


class TombstoneFormatError(ValueError):
    """Okunamayan bir satır: sessizce atlansaydı bir karar uygulanmamış kalırdı."""


class FileTombstones:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> list[Tombstone]:
        if not self.path.exists():
            return []
        out = []
        for number, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                action, record = raw.split()
                out.append(Tombstone(Action(action), record))
            except ValueError:
                raise TombstoneFormatError(f"{self.path}:{number}: {raw!r}") from None
        return out

    def add(self, tombstones: Sequence[Tombstone]) -> None:
        if not tombstones:
            return
        with self.path.open("a", encoding="utf-8") as f:
            f.write("".join(f"{t.action.value} {t.record}\n" for t in tombstones))
            f.flush()
            os.fsync(f.fileno())


def beside(database: Path) -> Path:
    """Listenin yeri: veritabanının yanında, onun yedeğine girmeyen ayrı bir dosya."""
    return database.with_name(f"{database.stem}.tombstones")
