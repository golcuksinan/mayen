"""Geri sarma (Faz A/A1): kopyayı bir turun öncesine döndürür.

Ölçülen davranış üç sınırda toplanıyor — hedef mesajın **kendisi de** siliniyor, özet ve
olguların sınırı `id` değil `created_at`, ve geride kalan hiçbir satır kırpılmıyor.
Üçüncüsü sessizce bozulabilecek tek şey: fazladan silen bir geri sarma, ölçümün üretimden
daha kısa bir geçmiş görmesi demek olurdu ve rapor bunu hiçbir yerde göstermezdi.
"""

from pathlib import Path

import pytest

from mayen.data.db import Database, DatabaseError
from mayen.data.migrate import migrate
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.facts import FactRepository
from mayen.data.rewind import rewind


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    return database


def test_rewind_drops_the_target_turn_and_everything_after(db: Database) -> None:
    messages = MessageRepository(db)
    first = messages.append("t1", "user", "bugün derslerim neler")
    messages.append("t1", "assistant", "Pazar, ders yok")
    target = messages.append("t2", "user", "sesi kıs")
    messages.append("t2", "assistant", "I will lower the volume")

    rewound = rewind(db, target.id)

    assert rewound.content == "sesi kıs"
    assert rewound.role == "user"
    assert rewound.messages == 2
    assert [m.id for m in messages.recent(10)] == [first.id, first.id + 1]


def test_summaries_written_after_the_turn_are_dropped(db: Database) -> None:
    """Özet, kapsadığı mesajlardan **sonra** yazılıyor: sınır `to_message` değil zaman."""
    messages = MessageRepository(db)
    summaries = SummaryRepository(db)
    old = messages.append("t1", "user", "eski")
    target = messages.append("t2", "user", "hedef")
    before = summaries.create([old.id], "turdan önce yazıldı")

    # Hedefin damgasından sonraki bir özet: kapsadığı mesaj eski olsa bile o turda yoktu.
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO summaries (from_message, to_message, content, created_at)"
            " VALUES (?, ?, ?, ?)",
            (old.id, old.id, "turdan sonra yazıldı", "2999-01-01T00:00:00Z"),
        )

    rewind(db, target.id)

    latest = summaries.latest()
    assert latest is not None
    assert latest.id == before.id


def test_facts_written_after_the_turn_are_dropped(db: Database) -> None:
    facts = FactRepository(db)
    messages = MessageRepository(db)
    target = messages.append("t1", "user", "hedef")
    kept = facts.create("kahveyi sade içer")
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO facts (content, created_at) VALUES (?, ?)",
            ("sonradan uydurulan olgu", "2999-01-01T00:00:00Z"),
        )

    rewound = rewind(db, target.id)

    assert rewound.facts == 1
    assert [f.id for f in facts.list_all()] == [kept.id]


def test_a_missing_message_is_an_error_not_an_empty_rewind(db: Database) -> None:
    """Sessizce her şeyi silen bir geri sarma, yanlış id yazan kişiye boş bir önek
    gösterirdi ve o önek bir ölçüm gibi okunurdu (Kural 13)."""
    with pytest.raises(DatabaseError, match="Mesaj bulunamadı"):
        rewind(db, 404)
