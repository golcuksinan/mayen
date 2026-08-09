"""Kişiler ve ses profilleri (§10).

`Tier` burada tanımlı çünkü saklanan bir değer ve şemadaki CHECK kısıtı zaten bu sözlüğün
sahibi. Politika katmanı (§10.2 matrisi) buradan okur — `policy`, `data`'yı import edebilir,
tersi olamaz (§4).
"""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from mayen.data import clock
from mayen.data.db import Database


class Tier(StrEnum):
    """§10.2. `TANINMAYAN` burada yok: profili olmayan kişinin satırı da yoktur."""

    SAHIP = "SAHIP"
    KAYITLI_KISI = "KAYITLI_KISI"
    BEKLEYEN = "BEKLEYEN"


@dataclass(frozen=True, slots=True)
class Person:
    id: int
    name: str
    tier: Tier
    phone: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    person_id: int
    embedding: bytes
    sample_count: int
    model_version: str
    updated_at: str


def _person(row: sqlite3.Row) -> Person:
    return Person(
        id=row["id"],
        name=row["name"],
        tier=Tier(row["tier"]),
        phone=row["phone"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PeopleRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, name: str, tier: Tier, phone: str | None = None) -> Person:
        now = clock.now()
        with self._db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO people (name, tier, phone, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) RETURNING *",
                (name, tier.value, phone, now, now),
            )
            return _person(cur.fetchone())

    def get(self, person_id: int) -> Person | None:
        with self._db.transaction() as conn:
            row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        return None if row is None else _person(row)

    def list_all(self) -> list[Person]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT * FROM people ORDER BY name").fetchall()
        return [_person(row) for row in rows]

    def update(
        self, person_id: int, *, name: str | None = None, phone: str | None = None
    ) -> Person | None:
        """Verilmeyen alan değişmez. `phone=None` "temizle" demez — silmek ayrı bir iştir."""
        with self._db.transaction() as conn:
            cur = conn.execute(
                "UPDATE people SET name = coalesce(?, name), phone = coalesce(?, phone), "
                "updated_at = ? WHERE id = ? RETURNING *",
                (name, phone, clock.now(), person_id),
            )
            row = cur.fetchone()
        return None if row is None else _person(row)

    def set_tier(self, person_id: int, tier: Tier) -> Person | None:
        """Kademe değişimi ayrı bir işlem: §10.4'e göre geri alınamaz ve onaydan geçer.
        `update()`'in içine gizlenirse yetki yükseltme sıradan bir alan düzenlemesi gibi
        görünür."""
        with self._db.transaction() as conn:
            cur = conn.execute(
                "UPDATE people SET tier = ?, updated_at = ? WHERE id = ? RETURNING *",
                (tier.value, clock.now(), person_id),
            )
            row = cur.fetchone()
        return None if row is None else _person(row)

    def delete(self, person_id: int) -> bool:
        with self._db.transaction() as conn:
            cur = conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
            return cur.rowcount > 0


class VoiceProfileRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def save(
        self, person_id: int, embedding: bytes, sample_count: int, model_version: str
    ) -> VoiceProfile:
        """Kişi başına tek profil; yeniden kaydetmek eskisinin üstüne yazar (§10.5)."""
        now = clock.now()
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO voice_profiles "
                "(person_id, embedding, sample_count, model_version, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (person_id) DO UPDATE SET "
                "embedding = excluded.embedding, sample_count = excluded.sample_count, "
                "model_version = excluded.model_version, updated_at = excluded.updated_at",
                (person_id, embedding, sample_count, model_version, now, now),
            )
        return VoiceProfile(person_id, embedding, sample_count, model_version, now)

    def list_all(self) -> list[VoiceProfile]:
        """Konuşmacı tanıma her segmentte tüm profillere karşı skor üretir (§10.1)."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT person_id, embedding, sample_count, model_version, updated_at "
                "FROM voice_profiles ORDER BY person_id"
            ).fetchall()
        return [
            VoiceProfile(
                person_id=row["person_id"],
                embedding=row["embedding"],
                sample_count=row["sample_count"],
                model_version=row["model_version"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def delete(self, person_id: int) -> bool:
        with self._db.transaction() as conn:
            cur = conn.execute("DELETE FROM voice_profiles WHERE person_id = ?", (person_id,))
            return cur.rowcount > 0
