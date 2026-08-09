"""Migration koşucusu: sıralı, idempotent, hata sessizce yutulmaz (§16, Kural 13).

Sürüm `PRAGMA user_version`'da tutulur — SQLite'ın kendi alanı, ayrı bir tabloya ve o
tablonun kendi migration'ına gerek yok. Uygulanmış migration listesi tutulmaz; sürüm
numarası tek gerçektir ve dosya adındaki sayıya karşılık gelir.

Her migration kendi transaction'ı içinde çalışır ve sürüm damgası **aynı** transaction'da
atılır. Yarım uygulanmış bir migration diye bir durum yok: ya dosyanın tamamı ve yeni
sürüm birlikte yazılır, ya da hiçbiri.
"""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from mayen.data.db import Database, DatabaseError
from mayen.obs.log import get_logger

MIGRATIONS = Path(__file__).parent / "migrations"
FILENAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    path: Path

    @property
    def name(self) -> str:
        return self.path.name


def discover(directory: Path = MIGRATIONS) -> list[Migration]:
    """Dizindeki migration'lar, sürüm sırasına dizili.

    Adlandırmaya uymayan dosya sessizce atlanmaz: yanlış adlandırılmış bir migration,
    hiç çalıştırılmayan bir migration demektir ve bunu fark etmek aylar sürer.
    """
    found: list[Migration] = []
    for path in sorted(directory.iterdir()):
        match = FILENAME.match(path.name)
        if match is None:
            raise DatabaseError(
                f"Migration adlandırmasına uymayan dosya: {path} "
                f"(beklenen biçim: 001_ad_soyad.sql)"
            )
        found.append(Migration(int(match.group(1)), path))

    expected = list(range(1, len(found) + 1))
    if [m.version for m in found] != expected:
        raise DatabaseError(
            f"Migration sürümleri 1'den başlayarak kesintisiz olmalı, bulunan: "
            f"{[m.version for m in found]}"
        )
    return found


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(db: Database, directory: Path = MIGRATIONS) -> int:
    """Bekleyen migration'ları uygular, ulaşılan sürümü döndürür.

    Tekrar çağrılmak zararsızdır: uygulanacak bir şey kalmamışsa hiçbir şey yapmaz.
    """
    migrations = discover(directory)
    with db.transaction() as conn:
        version = current_version(conn)

    if version > len(migrations):
        # Veritabanı koddan yeni. Eski kodun yeni şemayı "tanıdığını" varsayıp devam
        # etmesi, sessiz veri bozulmasına giden en kısa yol.
        raise DatabaseError(
            f"Veritabanı sürümü {version}, kodda yalnızca {len(migrations)} migration var. "
            f"Eski kod yeni veritabanına bağlanmış olabilir."
        )

    for migration in migrations[version:]:
        _apply(db, migration)
        version = migration.version
    return version


def _apply(db: Database, migration: Migration) -> None:
    sql = migration.path.read_text(encoding="utf-8")
    # Sürüm damgası betiğin kendi işleminin içinde: DDL ile damga ya birlikte yazılır ya
    # da hiç yazılmaz. `user_version` SQLite'ta işleme dahildir, geri alınır.
    #
    # PRAGMA parametre bağlamayı kabul etmiyor; değer dosya adından ayrıştırılmış bir
    # tamsayı, kullanıcı girdisi değil.
    try:
        db.script(f"{sql}\nPRAGMA user_version = {migration.version};")
    except sqlite3.Error as exc:
        # Sarmalamanın sebebi hatayı yumuşatmak değil, hangi dosyada olduğunu söylemek;
        # özgün hata `__cause__` olarak korunur.
        raise DatabaseError(f"Migration başarısız: {migration.name}: {exc}") from exc
    log.info("migration uygulandı", migration=migration.name, version=migration.version)
