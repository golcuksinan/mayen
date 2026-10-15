"""SQLite deposu (§11.6): tek dosya, tek sahip, WAL; şema sürümlü, sözlük `ports`'tan.

Süreçte tek bağlantı vardır ve bir kilitle sıraya girer; SQLite'ta yazmalar WAL'da da tek
yazarlıdır, bağlantı çoğaltmak yalnızca kilit beklemesini hataya çevirir. Bunun karşılığı tek
kuraldır: bir transaction asla bir LLM ya da HTTP çağrısını kapsamaz.

`autocommit=True` altında `Connection.commit()`/`.rollback()` sessizce hiçbir şey yapmaz;
transaction düz `BEGIN`/`COMMIT`/`ROLLBACK` SQL'iyle yönetilir. `executescript` örtük COMMIT
yaptığı için kullanılmaz; migration'lar ifade ifade aynı transaction'da çalışır.
"""

import fcntl
import json
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import IO, Any, Self
from uuid import UUID

from mayen.ports.events import Event, EventId, EventKind, Header, parse_stamp, stamp
from mayen.ports.notes import Note
from mayen.ports.people import DeviceId, DevicePairedError, OwnerExistsError, Person
from mayen.ports.timers import Timer, TimerState
from mayen.ports.tools import Role, Sensitivity, Status
from mayen.ports.transcript import Party, Utterance, UtteranceId
from mayen.ports.triggers import Priority, TurnId

# Ayrı bir bağlantının (yedek gibi) tuttuğu yazma kilidi için beklenecek süre.
BUSY_TIMEOUT_MS = 5_000


class StorageError(Exception):
    """Veritabanı beklenen durumda değil; sessizce devam edilmez (§14)."""


def check_in(column: str, vocabulary: type[StrEnum]) -> str:
    """Saklanan sözlüğün CHECK kısıtı (§11.6). Açılışta veritabanındakiyle karşılaştırılır."""
    values = ", ".join(f"'{v.value}'" for v in vocabulary)
    return f"CHECK ({column} IN ({values}))"


# Hangi tablonun hangi sütunu hangi sözlüğe bağlı. Sözlük büyüyünce açılış kırılır ve kısıtı
# yeniden kuran bir migration gerekir; eski kısıt, yeni değeri yazma anında reddederdi.
VOCABULARIES: Sequence[tuple[str, str, type[StrEnum]]] = (
    ("events", "kind", EventKind),
    ("events", "status", Status),
    ("notes", "sensitivity", Sensitivity),
    ("timers", "priority", Priority),
    ("timers", "sensitivity", Sensitivity),
    ("timers", "state", TimerState),
    ("people", "role", Role),
    ("utterances", "party", Party),
    ("utterances", "role", Role),
)


def _events_tables(events: str, related: str) -> list[str]:
    """Olay kaydının iki tablosu, verilen adlarla; sözlük güncel `EventKind`'den."""
    return [
        f"""CREATE TABLE {events} (
            seq INTEGER PRIMARY KEY,
            id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL {check_in("kind", EventKind)},
            source TEXT NOT NULL,
            time TEXT NOT NULL,
            session TEXT,
            turn_id TEXT,
            duration_s REAL,
            status TEXT {check_in("status", Status)},
            body TEXT NOT NULL
        ) STRICT""",
        # İlgili kayıtlar ayrı tabloda: sil, bir kaydın kopyalarını dizinle bulur (§11.4).
        f"""CREATE TABLE {related} (
            event_seq INTEGER NOT NULL REFERENCES {events} (seq) ON DELETE CASCADE,
            record_id TEXT NOT NULL,
            PRIMARY KEY (event_seq, record_id)
        ) STRICT""",
    ]


_EVENTS_INDEXES = (
    "CREATE INDEX events_time ON events (time, seq)",
    "CREATE INDEX events_session ON events (session, time, seq)",
    "CREATE INDEX events_turn ON events (turn_id, time, seq)",
    "CREATE INDEX event_related_record ON event_related (record_id)",
)


def rebuild_events() -> list[str]:
    """`EventKind` büyüyünce olay tablolarını yeni kısıtla yeniden kurar; satırlar korunur.

    SQLite bir kısıtı yerinde değiştiremez. Bağlı tablo önce yenisine taşınır ve eskisi
    düşürülür; eski olay tablosu ancak ondan sonra düşer, yoksa yabancı anahtarın silme
    zinciri ilgili kayıtları silerdi. Ad değişince SQLite, yeni bağlı tablonun anahtarını da
    yeni ada çevirir.
    """
    return [
        *_events_tables("events_new", "event_related_new"),
        "INSERT INTO events_new SELECT * FROM events",
        "INSERT INTO event_related_new SELECT * FROM event_related",
        "DROP TABLE event_related",
        "DROP TABLE events",
        "ALTER TABLE events_new RENAME TO events",
        "ALTER TABLE event_related_new RENAME TO event_related",
        *_EVENTS_INDEXES,
    ]


# Sürüm = sıradaki yeri (1'den başlar). Uygulanmış bir migration değiştirilmez; düzeltme
# yeni bir migration'dır.
MIGRATIONS: Sequence[Sequence[str]] = (
    (*_events_tables("events", "event_related"), *_EVENTS_INDEXES),
    (
        # AUTOINCREMENT: silinmiş bir kaydın numarası yeniden verilmez; verilseydi eski
        # numarayla yapılan bir silme yeni kaydı silerdi.
        f"""CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            sensitivity TEXT NOT NULL {check_in("sensitivity", Sensitivity)}
        ) STRICT""",
        f"""CREATE TABLE timers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            due TEXT NOT NULL,
            text TEXT NOT NULL,
            priority TEXT NOT NULL {check_in("priority", Priority)},
            tolerance_s REAL NOT NULL CHECK (tolerance_s >= 0),
            sensitivity TEXT NOT NULL {check_in("sensitivity", Sensitivity)},
            person_id TEXT,
            state TEXT NOT NULL {check_in("state", TimerState)}
        ) STRICT""",
        "CREATE INDEX timers_state ON timers (state, due, id)",
    ),
    (
        f"""CREATE TABLE people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL {check_in("role", Role)},
            language TEXT NOT NULL,
            address_as TEXT
        ) STRICT""",
        # Tek sahip veritabanında da zorlanır: kurulum komutunun denetimi tek başına bir
        # yarışı engellemez (§10.2).
        "CREATE UNIQUE INDEX people_one_owner ON people (role)"
        f" WHERE role = '{Role.OWNER.value}'",
        # Cihaz birincil anahtar: bir cihaz en çok bir kişinin kişisel cihazıdır (§10.1).
        """CREATE TABLE devices (
            id TEXT PRIMARY KEY,
            person_id INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE
        ) STRICT""",
        "CREATE INDEX devices_person ON devices (person_id, id)",
    ),
    (
        # Kişinin sözünde rol vardır, Mayen'inkinde yoktur; ikisi tabloda da birbirini tutar.
        f"""CREATE TABLE utterances (
            seq INTEGER PRIMARY KEY,
            id TEXT NOT NULL UNIQUE,
            time TEXT NOT NULL,
            session TEXT NOT NULL,
            turn_id TEXT,
            party TEXT NOT NULL {check_in("party", Party)},
            role TEXT {check_in("role", Role)},
            person_id TEXT,
            text TEXT NOT NULL,
            interrupted INTEGER NOT NULL CHECK (interrupted IN (0, 1)),
            CHECK ((party = '{Party.PERSON.value}') = (role IS NOT NULL))
        ) STRICT""",
        "CREATE INDEX utterances_time ON utterances (time, seq)",
        "CREATE INDEX utterances_session ON utterances (session, time, seq)",
        "CREATE INDEX utterances_turn ON utterances (turn_id, time, seq)",
    ),
    rebuild_events(),  # tool.requested
    rebuild_events(),  # state.changed
)


def _own(path: Path) -> IO[str]:
    """Dosyanın tek sahibi olunduğunu kilitle zorlar (§3): ikinci süreç açamaz."""
    lock_path = path.with_name(f"{path.name}.lock")
    handle = lock_path.open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise StorageError(f"database is open in another process: {path}") from None
    return handle


class Database:
    """Sahibi olunan SQLite dosyası; açılışta bekleyen migration'lar uygulanır."""

    def __init__(self, path: Path, migrations: Sequence[Sequence[str]] = MIGRATIONS) -> None:
        self.path = path
        self._lock = threading.Lock()
        # Kilit bağlantıdan sonra: yanlış yolun hatası kilit dosyasının hatası gibi görünmesin.
        self._conn = sqlite3.connect(path, autocommit=True, check_same_thread=False)
        try:
            self._owner = _own(path)
        except StorageError:
            self._conn.close()
            raise
        try:
            self._configure()
            self.migrate(migrations)
            self._check_vocabularies()
        except BaseException:
            self.close()
            raise

    def _configure(self) -> None:
        mode = str(self._conn.execute("PRAGMA journal_mode = WAL").fetchone()[0])
        if mode.lower() != "wal":
            # Ağ dosya sistemlerinde WAL sessizce reddedilir.
            raise StorageError(f"could not enable WAL, journal mode is {mode!r}: {self.path}")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Tek bir işlem; hata olursa geri alınır ve yükselir. Okumalar da buradan geçer."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            self._conn.execute("COMMIT")

    def version(self) -> int:
        with self.transaction() as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])

    def migrate(self, migrations: Sequence[Sequence[str]]) -> None:
        """Bekleyen migration'lar sırayla; her biri sürüm damgasıyla aynı transaction'da."""
        current = self.version()
        if current > len(migrations):
            # Eski kodun yeni şemayı tanıdığını varsaymak sessiz bozulmanın en kısa yolu.
            raise StorageError(
                f"database version {current} is newer than the code ({len(migrations)})"
            )
        for number, statements in enumerate(migrations[current:], start=current + 1):
            try:
                with self.transaction() as conn:
                    for statement in statements:
                        conn.execute(statement)
                    # PRAGMA bağlama kabul etmez; değer koddaki sıradan gelir.
                    conn.execute(f"PRAGMA user_version = {number}")
            except sqlite3.Error as e:
                raise StorageError(f"migration {number} failed: {e}") from e

    def _check_vocabularies(self) -> None:
        with self.transaction() as conn:
            for table, column, vocabulary in VOCABULARIES:
                row = conn.execute(
                    "SELECT sql FROM sqlite_schema WHERE type = 'table' AND name = ?", (table,)
                ).fetchone()
                if row is None or check_in(column, vocabulary) not in row[0]:
                    raise StorageError(
                        f"{table}.{column} constraint differs from {vocabulary.__name__}; "
                        "a migration must rebuild it"
                    )

    def close(self) -> None:
        self._conn.close()
        # Kilit bağlantıdan sonra bırakılır; tersinde kapanan dosyayı başkası açabilirdi.
        self._owner.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class SqliteEventLog:
    """Olay kaydı (§11) SQLite'ta."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, event: Event) -> None:
        h = event.header
        body = json.dumps(event.body, ensure_ascii=False, allow_nan=False)
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO events (id, kind, source, time, session, turn_id, duration_s,"
                " status, body) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(h.id),
                    h.kind.value,
                    h.source,
                    stamp(h.time),
                    h.session,
                    None if h.turn_id is None else str(h.turn_id),
                    h.duration_s,
                    None if h.status is None else h.status.value,
                    body,
                ),
            )
            conn.executemany(
                "INSERT INTO event_related (event_seq, record_id) VALUES (?, ?)",
                [(cursor.lastrowid, record) for record in dict.fromkeys(h.related)],
            )

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Event]:
        condition, params = _range(session, turn_id, since, until)
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT seq, id, kind, source, time, session, turn_id, duration_s, status, body"
                f" FROM events {condition} ORDER BY time, seq",
                params,
            ).fetchall()
            related: dict[int, list[str]] = {}
            for seq, record in conn.execute(
                "SELECT event_seq, record_id FROM event_related"
                f" WHERE event_seq IN (SELECT seq FROM events {condition})"
                " ORDER BY rowid",
                params,
            ):
                related.setdefault(seq, []).append(record)
        return [_event(row, related.get(row[0], [])) for row in rows]


def _event(row: tuple[Any, ...], related: list[str]) -> Event:
    # STRICT tablo sütun tiplerini zorlar; satır burada dataclass'a çevrilir ve yukarı çıkmaz.
    _, id_, kind, source, time, session, turn_id, duration_s, status, body = row
    header = Header(
        id=EventId(UUID(id_)),
        kind=EventKind(kind),
        source=source,
        time=parse_stamp(time),
        session=session,
        turn_id=None if turn_id is None else TurnId(UUID(turn_id)),
        duration_s=duration_s,
        status=None if status is None else Status(status),
        related=tuple(related),
    )
    return Event(header, json.loads(body))


def _range(
    session: str | None,
    turn_id: TurnId | None,
    since: datetime | None,
    until: datetime | None,
) -> tuple[str, list[str]]:
    """Olay kaydının ve transkriptin ortak süzgeci: oturum, tur ve `[since, until)`."""
    where: list[str] = []
    params: list[str] = []
    if session is not None:
        where.append("session = ?")
        params.append(session)
    if turn_id is not None:
        where.append("turn_id = ?")
        params.append(str(turn_id))
    if since is not None:
        where.append("time >= ?")
        params.append(stamp(since))
    if until is not None:
        where.append("time < ?")
        params.append(stamp(until))
    return (f"WHERE {' AND '.join(where)}" if where else ""), params


class SqliteTranscript:
    """Transkript (§11) SQLite'ta."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def append(self, utterance: Utterance) -> None:
        u = utterance
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO utterances (id, time, session, turn_id, party, role, person_id,"
                " text, interrupted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(u.id),
                    stamp(u.time),
                    u.session,
                    None if u.turn_id is None else str(u.turn_id),
                    u.party.value,
                    None if u.role is None else u.role.value,
                    u.person_id,
                    u.text,
                    int(u.interrupted),
                ),
            )

    def read(
        self,
        *,
        session: str | None = None,
        turn_id: TurnId | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Utterance]:
        condition, params = _range(session, turn_id, since, until)
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT id, time, session, turn_id, party, role, person_id, text, interrupted"
                f" FROM utterances {condition} ORDER BY time, seq",
                params,
            ).fetchall()
        return [_utterance(row) for row in rows]


def _utterance(row: tuple[Any, ...]) -> Utterance:
    id_, time, session, turn_id, party, role, person_id, text, interrupted = row
    return Utterance(
        id=UtteranceId(UUID(id_)),
        time=parse_stamp(time),
        session=session,
        turn_id=None if turn_id is None else TurnId(UUID(turn_id)),
        party=Party(party),
        role=None if role is None else Role(role),
        person_id=person_id,
        text=text,
        interrupted=bool(interrupted),
    )


def _fold(text: str) -> str:
    # "İ".casefold() "i" + birleşen nokta verir; nokta atılmazsa "DİŞÇİ" "dişçi"yi bulamaz.
    return text.casefold().replace("\u0307", "")


class SqliteNoteStore:
    """Not deposu (§11). Arama Python'da: SQLite'ın `LIKE`'ı yalnızca ASCII harfleri katlar."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, text: str, sensitivity: Sensitivity) -> Note:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO notes (text, sensitivity) VALUES (?, ?)", (text, sensitivity.value)
            )
        return Note(str(cursor.lastrowid), text, sensitivity)

    def search(self, query: str) -> list[Note]:
        needle = _fold(query)
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT id, text, sensitivity FROM notes ORDER BY id"
            ).fetchall()
        return [
            Note(str(id_), text, Sensitivity(sensitivity))
            for id_, text, sensitivity in rows
            if needle in _fold(text)
        ]

    def delete(self, note_id: str) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute("DELETE FROM notes WHERE id = ?", (_number(note_id),))
        return cursor.rowcount > 0


def _number(record_id: str) -> int | None:
    # Numara olmayan bir kimlik hiçbir kayda denk gelmez; hata değil, "yok"tur.
    return int(record_id) if record_id.isdecimal() else None


_TIMER_COLUMNS = "id, due, text, priority, tolerance_s, sensitivity, person_id, state"


class SqliteTimerStore:
    """İş ve zamanlayıcı deposu (§11, §12)."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def add(
        self,
        due: datetime,
        text: str,
        priority: Priority,
        tolerance_s: float,
        sensitivity: Sensitivity,
        person_id: str | None,
    ) -> Timer:
        with self._db.transaction() as conn:
            row = conn.execute(
                "INSERT INTO timers (due, text, priority, tolerance_s, sensitivity, person_id,"
                f" state) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING {_TIMER_COLUMNS}",
                (
                    stamp(due),
                    text,
                    priority.value,
                    tolerance_s,
                    sensitivity.value,
                    person_id,
                    TimerState.PENDING.value,
                ),
            ).fetchone()
        return _timer(row)

    def get(self, timer_id: str) -> Timer | None:
        with self._db.transaction() as conn:
            row = conn.execute(
                f"SELECT {_TIMER_COLUMNS} FROM timers WHERE id = ?", (_number(timer_id),)
            ).fetchone()
        return None if row is None else _timer(row)

    def pending(self) -> list[Timer]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                f"SELECT {_TIMER_COLUMNS} FROM timers WHERE state = ? ORDER BY due, id",
                (TimerState.PENDING.value,),
            ).fetchall()
        return [_timer(row) for row in rows]

    def delete(self, timer_id: str) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM timers WHERE id = ? AND state = ?",
                (_number(timer_id), TimerState.PENDING.value),
            )
        return cursor.rowcount > 0

    def close(self, timer_id: str, state: TimerState) -> None:
        if state is TimerState.PENDING:
            raise ValueError("a timer is closed with its outcome, not reopened")
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "UPDATE timers SET state = ? WHERE id = ? AND state = ?",
                (state.value, _number(timer_id), TimerState.PENDING.value),
            )
            if cursor.rowcount == 0:
                # İki kez kapatmak, aynı hatırlatmanın iki kez çaldığı demektir.
                raise StorageError(f"timer {timer_id} is not pending")


def _timer(row: tuple[Any, ...]) -> Timer:
    id_, due, text, priority, tolerance_s, sensitivity, person_id, state = row
    return Timer(
        id=str(id_),
        due=parse_stamp(due),
        text=text,
        priority=Priority(priority),
        tolerance_s=tolerance_s,
        sensitivity=Sensitivity(sensitivity),
        person_id=person_id,
        state=TimerState(state),
    )


class SqlitePersonStore:
    """Kişi profili deposu (§11.1)."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_owner(
        self, name: str, language: str, address_as: str | None, devices: tuple[DeviceId, ...]
    ) -> Person:
        try:
            with self._db.transaction() as conn:
                cursor = conn.execute(
                    "INSERT INTO people (name, role, language, address_as) VALUES (?, ?, ?, ?)",
                    (name, Role.OWNER.value, language, address_as),
                )
                conn.executemany(
                    "INSERT INTO devices (id, person_id) VALUES (?, ?)",
                    [(device, cursor.lastrowid) for device in dict.fromkeys(devices)],
                )
        except sqlite3.IntegrityError as e:
            # SQLite kısıtı adıyla değil sütunuyla bildirir.
            if "people.role" in str(e):
                raise OwnerExistsError("an owner is already set up") from e
            if "devices.id" in str(e):
                raise DevicePairedError("a device is already paired to someone") from e
            raise
        return Person(
            str(cursor.lastrowid),
            name,
            Role.OWNER,
            language,
            address_as,
            tuple(dict.fromkeys(devices)),
        )

    def owner(self) -> Person | None:
        return self._one("role = ?", Role.OWNER.value)

    def get(self, person_id: str) -> Person | None:
        number = _number(person_id)
        return None if number is None else self._one("id = ?", number)

    def by_device(self, device: DeviceId) -> Person | None:
        return self._one("id = (SELECT person_id FROM devices WHERE id = ?)", device)

    def _one(self, condition: str, value: str | int) -> Person | None:
        with self._db.transaction() as conn:
            row = conn.execute(
                f"SELECT id, name, role, language, address_as FROM people WHERE {condition}",
                (value,),
            ).fetchone()
            if row is None:
                return None
            devices = conn.execute(
                "SELECT id FROM devices WHERE person_id = ? ORDER BY id", (row[0],)
            ).fetchall()
        id_, name, role, language, address_as = row
        return Person(
            str(id_),
            name,
            Role(role),
            language,
            address_as,
            tuple(DeviceId(d) for (d,) in devices),
        )
