"""Konuşma geçmişi ve özetler (§11.1, §11.2).

Oturum sınırı yok; geçmiş tek sürekli akış ve sırası `id`. Sert kırpma satırı **silmez**
(§11.1) — yalnızca pencerenin dışında bırakır, ve `summary_id IS NULL` boştaki özetleme
işinin iş listesidir.
"""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from mayen.data import clock
from mayen.data.db import Database

type Role = Literal["user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class Message:
    id: int
    turn_id: str
    role: Role
    person_id: int | None
    content: str
    token_count: int | None
    summary_id: int | None
    created_at: str
    tool_calls: str | None = None
    """Mesajın taşıdığı tool çağrıları, JSON metin (yerel çağrı biçimi, Faz B/2).

    Neredeyse her satırda NULL: §8.3'ün metin biçimlerinde çağrı `content`'in içinde
    duruyor. Gerekçesi migration 002'de."""


@dataclass(frozen=True, slots=True)
class Summary:
    id: int
    from_message: int
    to_message: int
    content: str
    token_count: int | None
    created_at: str


def _message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        turn_id=row["turn_id"],
        role=row["role"],
        person_id=row["person_id"],
        content=row["content"],
        token_count=row["token_count"],
        summary_id=row["summary_id"],
        created_at=row["created_at"],
        tool_calls=row["tool_calls"],
    )


def _summary(row: sqlite3.Row) -> Summary:
    return Summary(
        id=row["id"],
        from_message=row["from_message"],
        to_message=row["to_message"],
        content=row["content"],
        token_count=row["token_count"],
        created_at=row["created_at"],
    )


class MessageRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def append(
        self,
        turn_id: str,
        role: Role,
        content: str,
        *,
        person_id: int | None = None,
        token_count: int | None = None,
        tool_calls: str | None = None,
    ) -> Message:
        """`token_count` verilmezse boş kalır: sayı LLM sunucusunun sayacından gelir,
        tahmin edilmez (Kural 10). Sıfır yazmak tahmin etmektir."""
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO messages (turn_id, role, person_id, content, token_count, "
                "created_at, tool_calls) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *",
                (turn_id, role, person_id, content, token_count, clock.now(), tool_calls),
            )
            return _message(cur.fetchone())

    def set_token_count(self, message_id: int, token_count: int) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE messages SET token_count = ? WHERE id = ?", (token_count, message_id)
            )

    def recent(self, limit: int) -> list[Message]:
        """Bağlam penceresi için son mesajlar, eskiden yeniye."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_message(row) for row in reversed(rows)]

    def unsummarized(self) -> list[Message]:
        """Özetlenmeyi bekleyenler (§11.2: açılışta ve boştaki ilk fırsatta)."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE summary_id IS NULL ORDER BY id"
            ).fetchall()
        return [_message(row) for row in rows]


class SummaryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(
        self,
        message_ids: Sequence[int],
        content: str,
        *,
        token_count: int | None = None,
    ) -> Summary:
        """Özeti yazar ve kapsadığı mesajları **aynı işlemde** işaretler.

        Ayrı işlem olsaydı arada bir çökme, özeti olan ama işaretlenmemiş mesaj bırakır ve
        o mesajlar bir daha özetlenirdi.
        """
        if not message_ids:
            raise ValueError("Boş mesaj kümesi özetlenemez")
        placeholders = ",".join("?" * len(message_ids))
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO summaries (from_message, to_message, content, token_count, "
                "created_at) VALUES (?, ?, ?, ?, ?) RETURNING *",
                (min(message_ids), max(message_ids), content, token_count, clock.now()),
            )
            summary = _summary(cur.fetchone())
            conn.execute(
                f"UPDATE messages SET summary_id = ? WHERE id IN ({placeholders})",
                (summary.id, *message_ids),
            )
        return summary

    def set_token_count(self, summary_id: int, token_count: int) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE summaries SET token_count = ? WHERE id = ?", (token_count, summary_id)
            )

    def latest(self) -> Summary | None:
        with self._db.transaction() as conn:
            row = conn.execute("SELECT * FROM summaries ORDER BY id DESC LIMIT 1").fetchone()
        return None if row is None else _summary(row)
