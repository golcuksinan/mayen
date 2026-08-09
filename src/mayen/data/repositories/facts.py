"""Kalıcı olgu deposu (§11.3): tek ortak havuz, kişi etiketli.

Olgular listelenebilir ve silinebilir olmalı — kullanıcının göremediği ve silemediği bir
bellek, hata ayıklanamaz bir bellektir.
"""

import sqlite3
from dataclasses import dataclass

from mayen.data import clock
from mayen.data.db import Database


@dataclass(frozen=True, slots=True)
class Fact:
    id: int
    person_id: int | None
    content: str
    source_message_id: int | None
    created_at: str


def _fact(row: sqlite3.Row) -> Fact:
    return Fact(
        id=row["id"],
        person_id=row["person_id"],
        content=row["content"],
        source_message_id=row["source_message_id"],
        created_at=row["created_at"],
    )


class FactRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(
        self,
        content: str,
        *,
        person_id: int | None = None,
        source_message_id: int | None = None,
    ) -> Fact:
        """`person_id` boşsa olgu tanınmayan birinden gelmiştir."""
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO facts (person_id, content, source_message_id, created_at) "
                "VALUES (?, ?, ?, ?) RETURNING *",
                (person_id, content, source_message_id, clock.now()),
            )
            return _fact(cur.fetchone())

    def list_all(self, *, person_id: int | None = None) -> list[Fact]:
        """`person_id` verilirse yalnızca o kişinin olguları."""
        with self._db.transaction() as conn:
            if person_id is None:
                rows = conn.execute("SELECT * FROM facts ORDER BY id").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM facts WHERE person_id = ? ORDER BY id", (person_id,)
                ).fetchall()
        return [_fact(row) for row in rows]

    def delete(self, fact_id: int) -> bool:
        with self._db.transaction() as conn:
            cur = conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            return cur.rowcount > 0
