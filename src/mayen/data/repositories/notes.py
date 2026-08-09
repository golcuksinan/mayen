"""Notlar (§9.2: ara/listele, oluştur, sil)."""

import sqlite3
from dataclasses import dataclass

from mayen.data import clock
from mayen.data.db import Database


@dataclass(frozen=True, slots=True)
class Note:
    id: int
    body: str
    person_id: int | None
    created_at: str


def _note(row: sqlite3.Row) -> Note:
    return Note(
        id=row["id"],
        body=row["body"],
        person_id=row["person_id"],
        created_at=row["created_at"],
    )


class NoteRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, body: str, *, person_id: int | None = None) -> Note:
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO notes (body, person_id, created_at) VALUES (?, ?, ?) RETURNING *",
                (body, person_id, clock.now()),
            )
            return _note(cur.fetchone())

    def list_all(self) -> list[Note]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT * FROM notes ORDER BY id DESC").fetchall()
        return [_note(row) for row in rows]

    def search(self, term: str) -> list[Note]:
        """Alt dize araması. Notlar birkaç yüz satır mertebesinde; tam metin dizini
        ölçülmemiş bir karmaşıklık olurdu. Sayı büyürse FTS5'e geçilir."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM notes WHERE body LIKE ? ESCAPE '\\' ORDER BY id DESC",
                (f"%{_escape_like(term)}%",),
            ).fetchall()
        return [_note(row) for row in rows]

    def delete(self, note_id: int) -> bool:
        with self._db.transaction() as conn:
            cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0


def _escape_like(term: str) -> str:
    """`%` ve `_` LIKE'ın joker karakterleri; kullanıcı metninde geçtiklerinde arama
    sessizce fazla sonuç döndürür."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
