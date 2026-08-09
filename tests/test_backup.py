"""Yedekleme: geri dönülebilirlik ve rotasyon (§16)."""

from pathlib import Path

import pytest

from mayen.data import backup
from mayen.data.db import Database, DatabaseError
from mayen.data.migrate import migrate
from mayen.data.repositories.people import PeopleRepository, Tier


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    return database


def test_a_backup_opens_and_reads(db: Database, tmp_path: Path) -> None:
    """Yedeğin bitti kriteri bu: dosyanın var olması değil, geri dönülebilmesi."""
    PeopleRepository(db).create("Ali", Tier.KAYITLI_KISI, phone="555")

    target = backup.run(db, tmp_path / "backups", keep=3)

    with Database(target) as restored:
        people = PeopleRepository(restored).list_all()
    assert [(p.name, p.phone) for p in people] == [("Ali", "555")]


def test_a_backup_captures_writes_still_in_the_wal(db: Database, tmp_path: Path) -> None:
    """Dosya kopyalamak burada başarısız olurdu: yazma henüz ana dosyada değil, `-wal`de."""
    PeopleRepository(db).create("Ali", Tier.KAYITLI_KISI)

    target = backup.run(db, tmp_path / "backups", keep=3)

    with Database(target) as restored:
        assert len(PeopleRepository(restored).list_all()) == 1


def test_the_backup_is_a_snapshot_not_a_link(db: Database, tmp_path: Path) -> None:
    people = PeopleRepository(db)
    people.create("Ali", Tier.KAYITLI_KISI)
    target = backup.run(db, tmp_path / "backups", keep=3)

    people.create("Veli", Tier.BEKLEYEN)

    with Database(target) as restored:
        assert [p.name for p in PeopleRepository(restored).list_all()] == ["Ali"]


def test_rotation_keeps_the_newest(db: Database, tmp_path: Path) -> None:
    directory = tmp_path / "backups"
    for stamp in ("20260801T000000Z", "20260802T000000Z", "20260803T000000Z"):
        directory.mkdir(exist_ok=True)
        (directory / f"mayen-{stamp}.db").touch()

    backup.run(db, directory, keep=2)

    names = [p.name for p in backup.existing(directory)]
    assert len(names) == 2
    assert names[0] == "mayen-20260803T000000Z.db"


def test_foreign_files_are_left_alone(db: Database, tmp_path: Path) -> None:
    """Rotasyon yalnızca kendi yazdığı dosyaları siler; yedek dizini bir çöp kutusu değil,
    ama orada başka bir şey varsa onu silmek de bu kodun işi değil."""
    directory = tmp_path / "backups"
    directory.mkdir()
    stranger = directory / "elle-alinmis-kopya.db"
    stranger.touch()

    backup.run(db, directory, keep=1)

    assert stranger.exists()


def test_no_partial_file_is_left_behind(db: Database, tmp_path: Path) -> None:
    directory = tmp_path / "backups"

    backup.run(db, directory, keep=2)

    assert list(directory.glob("*.partial")) == []


def test_keeping_zero_backups_is_rejected(db: Database, tmp_path: Path) -> None:
    """`keep=0` "yedek alma" demek değil, ayarın yanlış yazıldığı anlamına gelir."""
    with pytest.raises(DatabaseError, match="En az bir yedek"):
        backup.run(db, tmp_path / "backups", keep=0)


def test_existing_on_a_missing_directory_is_empty(tmp_path: Path) -> None:
    assert backup.existing(tmp_path / "yok") == []
