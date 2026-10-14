"""Kişi profili (§11.1, §10.2), hatırlatmanın hedefi (§12, §7) ve profilden çağırana."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from mayen.adapters.storage.sqlite import Database, SqlitePersonStore
from mayen.core.presence import Presence
from mayen.core.profile import UNKNOWN, caller, speaker
from mayen.ports.people import (
    LOCAL_DEVICE,
    DeviceId,
    DevicePairedError,
    OwnerExistsError,
    Person,
)
from mayen.ports.tools import Caller, Role, Sensitivity

PHONE = DeviceId("nPhone")


@pytest.fixture
def people(tmp_path: Path) -> Iterator[SqlitePersonStore]:
    with Database(tmp_path / "m.db") as db:
        yield SqlitePersonStore(db)


def test_owner_is_set_up_once_with_devices(people: SqlitePersonStore) -> None:
    owner = people.create_owner("Sinan", "tr", "Sinan", (LOCAL_DEVICE, PHONE, PHONE))
    assert owner.devices == (LOCAL_DEVICE, PHONE)
    assert people.owner() == owner == people.get(owner.id)
    assert people.by_device(PHONE) == owner
    with pytest.raises(OwnerExistsError):
        people.create_owner("Biri", "tr", None, ())
    assert people.owner() == owner


def test_unpaired_device_and_unknown_id_find_nobody(people: SqlitePersonStore) -> None:
    people.create_owner("Sinan", "tr", None, (LOCAL_DEVICE,))
    assert people.by_device(PHONE) is None
    assert people.get("abc") is None and people.get("99") is None


def test_owner_survives_reopening(tmp_path: Path) -> None:
    with Database(tmp_path / "m.db") as db:
        SqlitePersonStore(db).create_owner("Sinan", "tr", None, (PHONE,))
    with Database(tmp_path / "m.db") as db:
        owner = SqlitePersonStore(db).owner()
    assert owner is not None and owner.devices == (PHONE,)


def test_device_paired_to_someone_else_is_refused(tmp_path: Path) -> None:
    """Kişisel cihaz tek kişinindir (§10.1); çakışan kurulum yarım iz bırakmaz."""
    with Database(tmp_path / "m.db") as db:
        people = SqlitePersonStore(db)
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO people (name, role, language) VALUES ('Biri', 'unknown', 'tr')"
            )
            conn.execute(
                "INSERT INTO devices (id, person_id) VALUES (?, last_insert_rowid())", (PHONE,)
            )
        with pytest.raises(DevicePairedError):
            people.create_owner("Sinan", "tr", None, (PHONE,))
        assert people.owner() is None


def person(devices: tuple[DeviceId, ...] = (PHONE,), address_as: str | None = None) -> Person:
    return Person("1", "Sinan", Role.OWNER, "tr", address_as, devices)


def test_caller_comes_from_the_profile() -> None:
    assert caller(person()) == Caller(Role.OWNER, "1", has_personal_device=True)
    assert caller(person(devices=())).has_personal_device is False
    assert caller(None) == UNKNOWN


def test_speaker_facts_carry_no_devices_or_rights() -> None:
    assert speaker(person()) == {"name": "Sinan", "role": "owner", "language": "tr"}
    assert speaker(person(address_as="efendim"))["address_as"] == "efendim"


def test_target_is_the_persons_last_session() -> None:
    p = Presence()
    p.connected("phone", PHONE, "1")
    p.connected("kitchen", DeviceId("nKitchen"), None)
    p.interacted("1", "kitchen")
    assert p.target("1", Sensitivity.GENERAL) == "kitchen"
    # Kişisel içerik ortak cihaza gitmez; kişinin kendi cihazına gider (§7).
    assert p.target("1", Sensitivity.PERSONAL) == "phone"


def test_someone_elses_last_session_is_not_a_target() -> None:
    p = Presence()
    p.connected("kitchen", DeviceId("nKitchen"), None)
    p.interacted("2", "kitchen")
    assert p.target("1", Sensitivity.GENERAL) is None
    assert p.target(None, Sensitivity.GENERAL) is None


def test_disconnected_session_is_not_a_target() -> None:
    p = Presence()
    p.connected("phone", PHONE, "1")
    p.connected("local", LOCAL_DEVICE, "1")
    p.interacted("1", "phone")
    p.disconnected("phone")
    assert p.target("1", Sensitivity.PERSONAL) == "local"
    p.disconnected("local")
    assert p.target("1", Sensitivity.GENERAL) is None


def test_interaction_in_an_unknown_session_is_ignored() -> None:
    p = Presence()
    p.interacted("1", "gone")
    p.connected("phone", PHONE, "1")
    assert p.target("1", Sensitivity.GENERAL) == "phone"


def test_unverified_connection_cannot_be_personal() -> None:
    with pytest.raises(ValueError):
        Presence().connected("s", None, "1")
