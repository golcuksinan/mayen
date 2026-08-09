"""Veritabanı bağlantısı: tek dosya, tek sahip, WAL (§16, Kural 1).

Süreç içinde **tek bağlantı** vardır ve bir muteksle korunur. SQLite'ta yazmalar zaten
serileşir — WAL'da bile aynı anda tek yazar olur — dolayısıyla bağlantı çoğaltmak
eşzamanlılık kazandırmaz, yalnızca kilit beklemesini `SQLITE_BUSY` hatasına çevirir.

Bunun karşılığında tek bir kural var:

    **Bir transaction hiçbir zaman bir LLM/HTTP/model çağrısını kapsamaz.**

Aç, oku ya da yaz, kapat. Uzun iş bağlantının dışında yapılır. Bu kural tutulduğu sürece
her işlem milisaniyeler sürer ve eşzamanlı iki iş birbirini fark etmez; tutulmazsa bağlantı
çoğaltmak da kurtarmaz.

Yedekleme kendi bağlantısını açar (`backup.py`); Kural 1 sürece dair bir kuraldır, bağlantı
sayısına dair değil.
"""

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Self

# Yazma kilidi başkasındayken beklenecek süre. Tek bağlantıda muteks zaten sıraya sokuyor;
# bu sınır yedekleme gibi ayrı bağlantılara karşı geçerli.
BUSY_TIMEOUT_MS = 5_000


class DatabaseError(Exception):
    """Veritabanı beklenen durumda değil. Sessizce devam edilmez."""


class Database:
    """Sahibi olunan SQLite dosyası. Süreç başına bir tane."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        # check_same_thread=False: bağlantı `asyncio.to_thread` üzerinden farklı iş
        # parçacıklarından çağrılır. Erişimi sıraya sokan şey sqlite3'ün kendi denetimi
        # değil, yukarıdaki muteks.
        self._conn = sqlite3.connect(path, autocommit=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._apply_pragmas()

    def _apply_pragmas(self) -> None:
        cur = self._conn.execute("PRAGMA journal_mode = WAL")
        mode = str(cur.fetchone()[0]).lower()
        if mode != "wal":
            # Ağ dosya sistemlerinde WAL sessizce reddedilir ve dayanıklılık varsayımı
            # çöker. Sessizce devam etmek Kural 13 ihlali.
            raise DatabaseError(f"WAL kipine geçilemedi, kip {mode!r} kaldı: {self.path}")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Tek bir işlem. Hata durumunda geri alınır ve yukarı fırlatılır (Kural 13).

        Okumalar da buradan geçer: tek bağlantıda erişim nasılsa sıraya giriyor, ayrı bir
        okuma yolu tutmanın kazancı yok.
        """
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                # Açık SQL, `Connection.rollback()` değil: `autocommit=True` altında
                # rollback()/commit() sessizce hiçbir şey yapmaz — işlem açık kalır ve
                # geri alındığı sanılan yazma bir sonraki COMMIT'e yapışır.
                self._conn.execute("ROLLBACK")
                raise
            self._conn.execute("COMMIT")

    def script(self, sql: str) -> None:
        """Çok ifadeli bir SQL betiğini tek işlem olarak çalıştırır.

        `executescript` bekleyen işlemi kendiliğinden COMMIT ettiği için `transaction()`
        içinden çağrılamaz — atomikliği sessizce bozar. İşlem denetimi bu yüzden betiğin
        kendi içinde. Migration'ların ihtiyacı olan tek şey bu.
        """
        with self._lock:
            try:
                self._conn.executescript(f"BEGIN IMMEDIATE;\n{sql}\nCOMMIT;")
            except BaseException:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise

    def backup_to(self, target: Path) -> None:
        """SQLite'ın kendi yedekleme API'siyle tutarlı bir kopya (§16).

        Dosyayı kopyalamak WAL'da yanlış: kopya, henüz ana dosyaya işlenmemiş
        `-wal` içeriğini kaçırır ve sessizce eski bir duruma döner.

        Muteks tutuluyor çünkü aynı bağlantı nesnesi eşzamanlı kullanılamaz. Yerel bir
        veritabanı için bu milisaniyeler sürer; büyürse ölçülür ve konuşulur.
        """
        with self._lock, sqlite3.connect(target) as destination:
            self._conn.backup(destination)
        destination.close()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
