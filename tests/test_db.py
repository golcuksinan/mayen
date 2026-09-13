"""Bağlantı kurulumu ve işlem sınırları."""

import sqlite3
from pathlib import Path

import pytest

from mayen.data.db import Database, DatabaseError


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "mayen.db")


def test_wal_and_foreign_keys_are_on(db: Database) -> None:
    with db.transaction() as conn:
        assert str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_rows_are_addressable_by_column_name(db: Database) -> None:
    with db.transaction() as conn:
        conn.execute("CREATE TABLE t (x TEXT)")
        conn.execute("INSERT INTO t VALUES ('a')")
        assert conn.execute("SELECT x FROM t").fetchone()["x"] == "a"


def test_failed_transaction_leaves_nothing_behind(db: Database) -> None:
    """`autocommit=True` altında `Connection.rollback()` sessiz bir no-op — bu test o
    tuzağa geri düşülmesini engelliyor."""
    with db.transaction() as conn:
        conn.execute("CREATE TABLE t (x TEXT)")

    with pytest.raises(RuntimeError), db.transaction() as conn:
        conn.execute("INSERT INTO t VALUES ('a')")
        raise RuntimeError("tur iptal edildi")

    with db.transaction() as conn:
        assert conn.execute("SELECT count(*) FROM t").fetchone()[0] == 0


def test_transaction_is_usable_after_a_failed_one(db: Database) -> None:
    """Geri alma işlemi gerçekten kapatmalı; kapatmazsa sıradaki BEGIN patlar."""
    with pytest.raises(RuntimeError), db.transaction():
        raise RuntimeError("bir şey oldu")

    with db.transaction() as conn:
        conn.execute("CREATE TABLE t (x TEXT)")


def test_script_is_atomic(db: Database) -> None:
    with pytest.raises(sqlite3.Error):
        db.script("CREATE TABLE a (x TEXT);\nCREATE TABLE a (x TEXT);")

    with db.transaction() as conn:
        assert conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] == 0


def test_script_commits_on_success(db: Database) -> None:
    db.script("CREATE TABLE a (x TEXT);\nINSERT INTO a VALUES ('v');")

    with db.transaction() as conn:
        assert conn.execute("SELECT x FROM a").fetchone()["x"] == "v"


def test_reopening_sees_committed_data(tmp_path: Path) -> None:
    path = tmp_path / "mayen.db"
    with Database(path) as first:
        first.script("CREATE TABLE a (x TEXT);\nINSERT INTO a VALUES ('v');")

    with Database(path) as second, second.transaction() as conn:
        assert conn.execute("SELECT x FROM a").fetchone()["x"] == "v"


def test_missing_directory_is_an_error(tmp_path: Path) -> None:
    """Dizin kendiliğinden oluşturulmaz; yanlış yola sessizce boş bir DB açmak, verinin
    kaybolduğunu haftalar sonra fark etmek demek."""
    with pytest.raises(sqlite3.OperationalError):
        Database(tmp_path / "yok" / "mayen.db")


def test_a_second_process_cannot_open_the_same_file(tmp_path: Path) -> None:
    """Kural 1'in kendisi: dosyanın tek sahibi var.

    Servis koşarken elle `python -m mayen` yazmak tam olarak bunu yapardı; iki sürecin aynı
    dosyaya yazması sessizce bozardı. Kilit süreç ömrü boyunca tutuluyor, yani aynı süreçte
    ikinci bir `Database` de aynı hatayı alır.
    """
    path = tmp_path / "mayen.db"
    with Database(path), pytest.raises(DatabaseError, match="başka bir süreçte açık"):
        Database(path)


def test_closing_releases_the_lock(tmp_path: Path) -> None:
    """Kilit bırakılmazsa yeniden başlatma çalışmaz — servis için asıl mesele bu."""
    path = tmp_path / "mayen.db"
    Database(path).close()
    Database(path).close()


def test_a_failed_open_does_not_hold_the_lock(tmp_path: Path) -> None:
    """Yanlış yol yüzünden açılamayan bir bağlantı kilidi tutsaydı, yolu düzeltmek
    yetmezdi — süreci yeniden başlatmak gerekirdi."""
    with pytest.raises(sqlite3.OperationalError):
        Database(tmp_path / "yok" / "mayen.db")
    Database(tmp_path / "mayen.db").close()
