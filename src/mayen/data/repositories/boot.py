"""Açılış kayıtları (§16).

§11.2 "son açılıştan bu yana özetlenmemiş konuşma" üzerinde çalışıyor; o soru ancak
açılışların kaydı varsa cevaplanabilir. Temiz kapanış `stopped_at` yazar, çökme yazmaz —
`stopped_at IS NULL` kalan satır çökmüş bir çalışmadır.
"""

import sqlite3
from dataclasses import dataclass

from mayen.data import clock
from mayen.data.db import Database


@dataclass(frozen=True, slots=True)
class BootRecord:
    id: int
    started_at: str
    stopped_at: str | None
    version: str


def _record(row: sqlite3.Row) -> BootRecord:
    return BootRecord(
        id=row["id"],
        started_at=row["started_at"],
        stopped_at=row["stopped_at"],
        version=row["version"],
    )


class BootRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def start(self, version: str) -> BootRecord:
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO boot_records (started_at, version) VALUES (?, ?) RETURNING *",
                (clock.now(), version),
            )
            return _record(cur.fetchone())

    def stop(self, boot_id: int) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE boot_records SET stopped_at = ? WHERE id = ?", (clock.now(), boot_id)
            )

    def previous(self) -> BootRecord | None:
        """Bir öncekiyle ilgilenen §11.2; şu ankiyle değil."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM boot_records ORDER BY id DESC LIMIT 2"
            ).fetchall()
        return _record(rows[1]) if len(rows) > 1 else None
