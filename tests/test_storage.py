"""SQLite deposu (§11.6): kurallar burada testle kilitlenir."""

import ast
import dataclasses
import sqlite3
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mayen.adapters.storage import sqlite as storage
from mayen.adapters.storage.sqlite import (
    MIGRATIONS,
    VOCABULARIES,
    Database,
    SqliteEventLog,
    StorageError,
    check_in,
)
from mayen.app.config import storage_path
from mayen.ports.events import Event, EventId, EventKind, Header
from mayen.ports.tools import Status
from mayen.ports.triggers import TurnId

T0 = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


def event(
    kind: EventKind = EventKind.TURN_STARTED,
    *,
    at: float = 0,
    session: str | None = "s1",
    turn_id: TurnId | None = None,
    related: tuple[str, ...] = (),
    body: dict[str, object] | None = None,
) -> Event:
    return Event(
        Header(
            id=EventId(uuid.uuid4()),
            kind=kind,
            source="test",
            time=T0 + timedelta(seconds=at),
            session=session,
            turn_id=turn_id,
            duration_s=0.5,
            status=Status.OK,
            related=related,
        ),
        body or {"n": at},
    )


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    with Database(tmp_path / "m.db") as opened:
        yield opened


def test_wal_mode(db: Database) -> None:
    with db.transaction() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_round_trip_returns_frozen_dataclass(db: Database) -> None:
    log = SqliteEventLog(db)
    written = event(turn_id=TurnId(uuid.uuid4()), related=("a", "b"), body={"t": "çğış"})
    log.append(written)
    [read] = log.read()
    assert read == written
    assert isinstance(read, Event) and not isinstance(read, sqlite3.Row)
    with pytest.raises(dataclasses.FrozenInstanceError):
        read.header.kind = EventKind.TURN_FINISHED  # type: ignore[misc]


def test_read_filters_and_orders_by_time(db: Database) -> None:
    log = SqliteEventLog(db)
    turn = TurnId(uuid.uuid4())
    late = event(at=3, turn_id=turn)
    early = event(at=1, turn_id=turn)
    other = event(at=2, session="s2")
    for e in (late, other, early):
        log.append(e)

    assert log.read() == [early, other, late]
    assert log.read(session="s1") == [early, late]
    assert log.read(turn_id=turn) == [early, late]
    assert log.read(since=T0 + timedelta(seconds=2)) == [other, late]
    assert log.read(until=T0 + timedelta(seconds=2)) == [early]


def test_related_records_are_indexed_apart_from_body(db: Database) -> None:
    log = SqliteEventLog(db)
    tagged = event(related=("note:7",))
    log.append(tagged)
    log.append(event(at=1))
    with db.transaction() as conn:
        found = conn.execute(
            "SELECT e.id FROM events e JOIN event_related r ON r.event_seq = e.seq"
            " WHERE r.record_id = ?",
            ("note:7",),
        ).fetchall()
    assert found == [(str(tagged.header.id),)]


def test_body_that_is_not_json_writes_nothing(db: Database) -> None:
    log = SqliteEventLog(db)
    with pytest.raises(TypeError):
        log.append(event(body={"x": object()}))
    assert log.read() == []


def test_failed_transaction_rolls_back_under_autocommit(db: Database) -> None:
    log = SqliteEventLog(db)
    with pytest.raises(RuntimeError), db.transaction() as conn:
        conn.execute(
            "INSERT INTO events (id, kind, source, time, body) VALUES (?, ?, ?, ?, ?)",
            ("x", "turn.started", "test", "t", "{}"),
        )
        raise RuntimeError
    assert log.read() == []
    assert not db._conn.in_transaction


def test_no_executescript_and_no_connection_commit() -> None:
    """`executescript` örtük COMMIT yapar; `commit()`/`rollback()` autocommit'te boştur."""
    forbidden = {"executescript", "commit", "rollback"}
    for path in Path(storage.__file__).parent.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert not called & forbidden, f"{path.name}: {called & forbidden}"


def test_schema_is_versioned_and_reopening_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "m.db"
    with Database(path) as db:
        assert db.version() == len(MIGRATIONS)
        SqliteEventLog(db).append(event())
    with Database(path) as db:
        assert db.version() == len(MIGRATIONS)
        assert len(SqliteEventLog(db).read()) == 1


def test_failed_migration_leaves_no_trace(tmp_path: Path) -> None:
    broken = [*MIGRATIONS, ["CREATE TABLE half (a INTEGER) STRICT", "NOT SQL"]]
    with pytest.raises(StorageError, match=f"migration {len(broken)}"):
        Database(tmp_path / "m.db", broken)
    with Database(tmp_path / "m.db") as db:
        assert db.version() == len(MIGRATIONS)
        with db.transaction() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_schema")}
        assert "half" not in tables


def test_database_newer_than_code_is_refused(tmp_path: Path) -> None:
    with Database(tmp_path / "m.db", [*MIGRATIONS, ["CREATE TABLE later (a INTEGER)"]]):
        pass
    with pytest.raises(StorageError, match="newer"):
        Database(tmp_path / "m.db")


def test_constraints_match_vocabularies(db: Database) -> None:
    with db.transaction() as conn:
        for table, column, vocabulary in VOCABULARIES:
            [sql] = conn.execute(
                "SELECT sql FROM sqlite_schema WHERE name = ?", (table,)
            ).fetchone()
            assert check_in(column, vocabulary) in sql
    with pytest.raises(sqlite3.IntegrityError), db.transaction() as conn:
        conn.execute(
            "INSERT INTO events (id, kind, source, time, body) VALUES (?, ?, ?, ?, ?)",
            ("x", "not.a.kind", "test", "t", "{}"),
        )


def test_constraint_out_of_date_with_vocabulary_is_refused(tmp_path: Path) -> None:
    """Sözlük büyüdü ama kısıtı yeniden kuran migration yazılmadı: açılış kırılır."""
    old = MIGRATIONS[0][0].replace(check_in("kind", EventKind), "CHECK (kind IN ('x'))")
    with pytest.raises(StorageError, match=r"events\.kind"):
        Database(tmp_path / "m.db", [[old, *MIGRATIONS[0][1:]]])


def test_second_owner_is_refused(db: Database) -> None:
    with pytest.raises(StorageError, match="another process"):
        Database(db.path)


def test_storage_path_is_relative_to_config(tmp_path: Path) -> None:
    config = tmp_path / "conf" / "mayen.yaml"
    config.parent.mkdir()
    config.write_text("storage:\n  path: data/mayen.db\n", encoding="utf-8")
    assert storage_path(config) == tmp_path / "conf" / "data" / "mayen.db"
