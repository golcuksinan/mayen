"""Ders programı (§19.8).

Kaynak depodaki program dosyası; DB açılışta ondan doldurulur. Buradan yazan bir tool yok,
o yüzden tekil ekleme/güncelleme de yok: yükleyici dönemi bir bütün olarak değiştirir.
"""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from mayen.data.db import Database


@dataclass(frozen=True, slots=True)
class CourseSession:
    """`day_of_week` 1=Pazartesi … 7=Pazar (ISO-8601). Saatler 'HH:MM'."""

    course_code: str
    title: str
    day_of_week: int
    start_time: str
    end_time: str
    location: str | None


def _session(row: sqlite3.Row) -> CourseSession:
    return CourseSession(
        course_code=row["course_code"],
        title=row["title"],
        day_of_week=row["day_of_week"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        location=row["location"],
    )


class CourseRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def replace_term(self, term: str, sessions: Sequence[CourseSession]) -> None:
        """Dönemin tamamını tek işlemde değiştirir.

        Sil-sonra-yaz ayrı işlemlerde olsaydı arada bir çökme programı boş bırakırdı ve
        sistem "bugün dersin yok" derdi — sessiz ve inandırıcı bir yanlış.
        """
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM course_sessions WHERE term = ?", (term,))
            conn.executemany(
                "INSERT INTO course_sessions (term, course_code, title, day_of_week, "
                "start_time, end_time, location) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        term,
                        s.course_code,
                        s.title,
                        s.day_of_week,
                        s.start_time,
                        s.end_time,
                        s.location,
                    )
                    for s in sessions
                ],
            )

    def for_day(self, term: str, day_of_week: int) -> list[CourseSession]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM course_sessions WHERE term = ? AND day_of_week = ? "
                "ORDER BY start_time",
                (term, day_of_week),
            ).fetchall()
        return [_session(row) for row in rows]

    def for_term(self, term: str) -> list[CourseSession]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM course_sessions WHERE term = ? ORDER BY day_of_week, start_time",
                (term,),
            ).fetchall()
        return [_session(row) for row in rows]
