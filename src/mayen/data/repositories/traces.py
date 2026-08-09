"""Tur izleri (§15).

İz mesaj gövdelerini kopyalamaz: gövde `messages`'ta durur, burada yalnızca `turn_id` var.
Kopyalamak §15'in kayıt hacmi kuralıyla çakışır ve her turun tam metnini iki kere yazar.

Aşama sayısı tur başına değişken (kaç tool çalıştıysa o kadar), bu yüzden aşamalar ayrı
tabloda.
"""

import sqlite3
from dataclasses import dataclass

from mayen.data import clock
from mayen.data.db import Database


@dataclass(frozen=True, slots=True)
class Stage:
    seq: int
    name: str
    started_at: str
    duration_ms: int | None
    detail: str | None


@dataclass(frozen=True, slots=True)
class TurnTrace:
    turn_id: str
    device_id: str
    person_id: int | None
    started_at: str
    ended_at: str | None
    outcome: str | None
    stages: tuple[Stage, ...]


def _stage(row: sqlite3.Row) -> Stage:
    return Stage(
        seq=row["seq"],
        name=row["name"],
        started_at=row["started_at"],
        duration_ms=row["duration_ms"],
        detail=row["detail"],
    )


class TraceRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def start(self, turn_id: str, device_id: str, *, person_id: int | None = None) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO turn_traces (turn_id, device_id, person_id, started_at) "
                "VALUES (?, ?, ?, ?)",
                (turn_id, device_id, person_id, clock.now()),
            )

    def add_stage(
        self,
        turn_id: str,
        name: str,
        *,
        duration_ms: int | None = None,
        detail: str | None = None,
    ) -> None:
        """`seq`'i çağıran vermez, depo verir: iki bileşenin aynı sırayı yazması ihtimali
        turun kendi izini bozmasına yol açardı."""
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO turn_trace_stages (turn_id, seq, name, started_at, duration_ms, "
                "detail) VALUES (?, (SELECT coalesce(max(seq), 0) + 1 FROM turn_trace_stages "
                "WHERE turn_id = ?), ?, ?, ?, ?)",
                (turn_id, turn_id, name, clock.now(), duration_ms, detail),
            )

    def finish(self, turn_id: str, outcome: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE turn_traces SET ended_at = ?, outcome = ? WHERE turn_id = ?",
                (clock.now(), outcome, turn_id),
            )

    def get(self, turn_id: str) -> TurnTrace | None:
        """İz + aşamaları. Yeniden oynatma (§15) bunun tamamını ister."""
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM turn_traces WHERE turn_id = ?", (turn_id,)
            ).fetchone()
            if row is None:
                return None
            stages = conn.execute(
                "SELECT * FROM turn_trace_stages WHERE turn_id = ? ORDER BY seq", (turn_id,)
            ).fetchall()
        return TurnTrace(
            turn_id=row["turn_id"],
            device_id=row["device_id"],
            person_id=row["person_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            outcome=row["outcome"],
            stages=tuple(_stage(s) for s in stages),
        )
