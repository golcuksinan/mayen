"""Mezar taşı listesi (§11.4) bir metin dosyasında: satır başına bir kayıt kimliği.

Dosya yalnızca büyür; satır silinmez. Yazma, karar veritabanına girmeden önce diske indirilir:
arada süreç ölürse açılış kararı listeden yeniden uygular, tersi olsaydı karar kaybolurdu.
"""

import os
from collections.abc import Sequence
from pathlib import Path


class FileTombstones:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> list[str]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [line for line in (raw.strip() for raw in lines) if line]

    def add(self, records: Sequence[str]) -> None:
        if not records:
            return
        with self.path.open("a", encoding="utf-8") as f:
            f.write("".join(f"{r}\n" for r in records))
            f.flush()
            os.fsync(f.fileno())


def beside(database: Path) -> Path:
    """Listenin yeri: veritabanının yanında, onun yedeğine girmeyen ayrı bir dosya."""
    return database.with_name(f"{database.stem}.tombstones")
