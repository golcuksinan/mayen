"""Migration koşucusu: sıralı, idempotent, sessiz yutma yok (§16, Kural 13)."""

from pathlib import Path

import pytest

from mayen.data.db import Database, DatabaseError
from mayen.data.migrate import MIGRATIONS, current_version, discover, migrate


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "mayen.db")


def _write(directory: Path, name: str, sql: str) -> None:
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(sql, encoding="utf-8")


def test_empty_file_reaches_the_latest_version(db: Database) -> None:
    version = migrate(db)

    assert version == len(discover())
    with db.transaction() as conn:
        assert current_version(conn) == version


def test_schema_v1_creates_every_documented_table(db: Database) -> None:
    """§16'nın saydığı veri gruplarının tamamı şemada karşılığını buluyor mu."""
    migrate(db)

    with db.transaction() as conn:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

    assert tables == {
        "boot_records",
        "course_sessions",
        "facts",
        "messages",
        "notes",
        "people",
        "scheduled_tasks",
        "summaries",
        "turn_trace_stages",
        "turn_traces",
        "voice_profiles",
    }


def test_running_twice_changes_nothing(db: Database) -> None:
    first = migrate(db)
    with db.transaction() as conn:
        before = conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()

    assert migrate(db) == first
    with db.transaction() as conn:
        assert conn.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall() == before


def test_pending_migrations_apply_in_order(db: Database, tmp_path: Path) -> None:
    directory = tmp_path / "m"
    _write(directory, "001_first.sql", "CREATE TABLE a (x TEXT);")
    assert migrate(db, directory) == 1

    _write(directory, "002_second.sql", "ALTER TABLE a ADD COLUMN y TEXT;")
    assert migrate(db, directory) == 2

    with db.transaction() as conn:
        assert [c["name"] for c in conn.execute("PRAGMA table_info(a)")] == ["x", "y"]


def test_failed_migration_rolls_back_and_raises(db: Database, tmp_path: Path) -> None:
    """Yarım uygulanmış migration olmamalı: ne tablo kalır, ne sürüm ilerler."""
    directory = tmp_path / "m"
    _write(directory, "001_broken.sql", "CREATE TABLE a (x TEXT);\nCREATE TABLE a (x TEXT);")

    with pytest.raises(DatabaseError, match=r"001_broken\.sql"):
        migrate(db, directory)

    with db.transaction() as conn:
        assert current_version(conn) == 0
        assert conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] == 0


def test_a_later_failure_keeps_the_earlier_version(db: Database, tmp_path: Path) -> None:
    directory = tmp_path / "m"
    _write(directory, "001_first.sql", "CREATE TABLE a (x TEXT);")
    _write(directory, "002_broken.sql", "CREATE TABLE a (x TEXT);")

    with pytest.raises(DatabaseError, match=r"002_broken\.sql"):
        migrate(db, directory)

    with db.transaction() as conn:
        assert current_version(conn) == 1
        rows = conn.execute("SELECT count(*) FROM sqlite_master WHERE name='a'")
        assert rows.fetchone()[0] == 1


def test_misnamed_file_is_rejected(tmp_path: Path) -> None:
    """Adlandırmaya uymayan dosya atlanmaz — atlanan migration hiç fark edilmez."""
    directory = tmp_path / "m"
    _write(directory, "001_first.sql", "CREATE TABLE a (x TEXT);")
    _write(directory, "sonra_bunu_duzeltiriz.sql", "CREATE TABLE b (x TEXT);")

    with pytest.raises(DatabaseError, match="adlandırmasına"):
        discover(directory)


def test_gap_in_versions_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "m"
    _write(directory, "001_first.sql", "CREATE TABLE a (x TEXT);")
    _write(directory, "003_third.sql", "CREATE TABLE c (x TEXT);")

    with pytest.raises(DatabaseError, match="kesintisiz"):
        discover(directory)


def test_database_newer_than_the_code_is_rejected(db: Database, tmp_path: Path) -> None:
    """Eski kod yeni veritabanına bağlanırsa dursun; devam ederse veri bozulur."""
    directory = tmp_path / "m"
    _write(directory, "001_first.sql", "CREATE TABLE a (x TEXT);")
    migrate(db, directory)
    db.script("PRAGMA user_version = 7;")

    with pytest.raises(DatabaseError, match="Eski kod"):
        migrate(db, directory)


def test_shipped_migrations_are_discoverable() -> None:
    """Paketlenmiş .sql dosyaları gerçekten yerinde mi (tekerlekte kaybolmasınlar)."""
    migrations = discover(MIGRATIONS)

    assert [m.version for m in migrations] == list(range(1, len(migrations) + 1))
    assert migrations[0].name == "001_initial.sql"
