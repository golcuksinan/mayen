"""Zamanlanmış görevler (§12).

Görevler kalıcı: uygulama kapanıp açıldığında kaybolmaz. Vakti geçmiş bir görev açılışta
tolerans içindeyse çalıştırılır, değilse **düşürülür ve düşürüldüğü kaydedilir** — bu
yüzden `DUSURULDU` bir durum, sessiz bir silme değil.
"""

import json
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from mayen.data import clock
from mayen.data.db import Database


class TaskStatus(StrEnum):
    BEKLIYOR = "BEKLIYOR"
    CALISTI = "CALISTI"
    IPTAL = "IPTAL"
    DUSURULDU = "DUSURULDU"


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    id: int
    kind: str
    payload: dict[str, Any]
    due_at: str
    status: TaskStatus
    outcome: str | None
    person_id: int | None
    created_at: str
    settled_at: str | None


def _task(row: sqlite3.Row) -> ScheduledTask:
    return ScheduledTask(
        id=row["id"],
        kind=row["kind"],
        payload=json.loads(row["payload"]),
        due_at=row["due_at"],
        status=TaskStatus(row["status"]),
        outcome=row["outcome"],
        person_id=row["person_id"],
        created_at=row["created_at"],
        settled_at=row["settled_at"],
    )


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(
        self,
        kind: str,
        payload: dict[str, Any],
        due_at: str,
        *,
        person_id: int | None = None,
    ) -> ScheduledTask:
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO scheduled_tasks (kind, payload, due_at, status, person_id, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING *",
                (
                    kind,
                    json.dumps(payload, ensure_ascii=False),
                    due_at,
                    TaskStatus.BEKLIYOR.value,
                    person_id,
                    clock.now(),
                ),
            )
            return _task(cur.fetchone())

    def due(self, now: str | None = None) -> list[ScheduledTask]:
        """Vakti gelmiş ve hâlâ bekleyen görevler, en eskiden başlayarak."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE status = ? AND due_at <= ? "
                "ORDER BY due_at",
                (TaskStatus.BEKLIYOR.value, now or clock.now()),
            ).fetchall()
        return [_task(row) for row in rows]

    def pending(self) -> list[ScheduledTask]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE status = ? ORDER BY due_at",
                (TaskStatus.BEKLIYOR.value,),
            ).fetchall()
        return [_task(row) for row in rows]

    def settle(
        self, task_id: int, status: TaskStatus, *, outcome: str | None = None
    ) -> ScheduledTask | None:
        """Görevi sonlandırır. Bekleyen olmayan bir görev ikinci kez sonlandırılamaz —
        koşullu UPDATE, iki koşucunun aynı görevi çalıştırmasını da engeller."""
        if status is TaskStatus.BEKLIYOR:
            raise ValueError("BEKLIYOR bir sonuç değil")
        with self._db.transaction() as conn:
            cur = conn.execute(
                "UPDATE scheduled_tasks SET status = ?, outcome = ?, settled_at = ? "
                "WHERE id = ? AND status = ? RETURNING *",
                (status.value, outcome, clock.now(), task_id, TaskStatus.BEKLIYOR.value),
            )
            row = cur.fetchone()
        return None if row is None else _task(row)
