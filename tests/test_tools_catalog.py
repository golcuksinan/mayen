"""§9.2 kataloğunun gövdeleri: gerçek veritabanı, fake yok — repository'ler zaten hızlı."""

from pathlib import Path

import httpx
import pytest

from mayen.config import Config
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.courses import CourseRepository, CourseSession
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository, Tier
from mayen.data.repositories.tasks import TaskRepository, TaskStatus
from mayen.policy.effects import Effect
from mayen.tools.catalog import builtin_registry
from mayen.tools.registry import Registry
from mayen.tools.spec import ToolArgumentError, ToolContext, ToolResult

TERM = "2026-guz"


def _no_network(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"test ağa çıktı: {request.url}")


@pytest.fixture
def context(tmp_path: Path) -> ToolContext:
    db = Database(tmp_path / "mayen.db")
    migrate(db)
    return ToolContext(
        config=Config(),
        http=httpx.AsyncClient(transport=httpx.MockTransport(_no_network)),
        people=PeopleRepository(db),
        notes=NoteRepository(db),
        courses=CourseRepository(db),
        tasks=TaskRepository(db),
        course_term=TERM,
    )


@pytest.fixture
def registry() -> Registry:
    return builtin_registry()


async def call(
    registry: Registry, context: ToolContext, tool_name: str, **raw: str
) -> ToolResult:
    """Çağrı yolunun tamamı: doğrula, sonra çalıştır (§8.5 adım 1)."""
    tool = registry.get(tool_name)
    return await tool.handler(context, tool.validate(raw))


def rows(result: ToolResult, key: str) -> list[dict[str, object]]:
    assert result.data is not None
    value = result.data[key]
    assert isinstance(value, list)
    return value


# --- kayıt defteri ---------------------------------------------------------------------


def test_catalog_is_built_fresh_each_time() -> None:
    assert [tool.name for tool in builtin_registry()] == [
        tool.name for tool in builtin_registry()
    ]
    assert builtin_registry() is not builtin_registry()


def test_destructive_tools_declare_the_irreversible_effect(registry: Registry) -> None:
    assert registry.get("contact_delete").effect is Effect.GERI_ALINAMAZ
    assert registry.get("note_delete").effect is Effect.GERI_ALINAMAZ
    assert registry.get("task_cancel").effect is Effect.YAZMA


# --- tarih/saat ------------------------------------------------------------------------


async def test_date_time_reports_utc(registry: Registry, context: ToolContext) -> None:
    result = await call(registry, context, "date_time")
    assert result.ok
    assert result.data is not None
    assert str(result.data["utc"]).endswith("Z")


# --- kişiler ---------------------------------------------------------------------------


async def test_contact_save_creates_as_pending_tier(
    registry: Registry, context: ToolContext
) -> None:
    """Kural 6 / §10.3: sesle eklenen kişi hiçbir yetki almaz."""
    await call(registry, context, "contact_save", name="Ali", phone="555")

    person = context.people.list_all()[0]
    assert person.tier is Tier.BEKLEYEN


async def test_contact_save_updates_existing_person(
    registry: Registry, context: ToolContext
) -> None:
    await call(registry, context, "contact_save", name="Ali", phone="555")
    await call(registry, context, "contact_save", name="Ali", phone="666")

    people = context.people.list_all()
    assert len(people) == 1
    assert people[0].phone == "666"


async def test_contact_get_filters_by_name(registry: Registry, context: ToolContext) -> None:
    await call(registry, context, "contact_save", name="Ali")
    await call(registry, context, "contact_save", name="Veli")

    result = await call(registry, context, "contact_get", name="Ve")

    assert [row["name"] for row in rows(result, "contacts")] == ["Veli"]


async def test_contact_delete_reports_missing_person(
    registry: Registry, context: ToolContext
) -> None:
    result = await call(registry, context, "contact_delete", name="Yok")
    assert not result.ok
    assert result.error is not None


# --- notlar ----------------------------------------------------------------------------


async def test_note_create_and_search(registry: Registry, context: ToolContext) -> None:
    await call(registry, context, "note_create", body="süt, ekmek ve yumurta al")

    result = await call(registry, context, "note_search", query="ekmek")

    assert len(rows(result, "notes")) == 1


async def test_note_delete_removes_the_note(registry: Registry, context: ToolContext) -> None:
    created = await call(registry, context, "note_create", body="not")
    assert created.data is not None

    result = await call(registry, context, "note_delete", id=str(created.data["id"]))

    assert result.ok
    assert context.notes.list_all() == []


async def test_note_delete_rejects_non_numeric_id(
    registry: Registry, context: ToolContext
) -> None:
    with pytest.raises(ToolArgumentError):
        await call(registry, context, "note_delete", id="birinci")


# --- ders programı ---------------------------------------------------------------------


async def test_course_schedule_filters_by_day(registry: Registry, context: ToolContext) -> None:
    context.courses.replace_term(
        TERM,
        [
            CourseSession("MAT101", "Matematik", 1, "09:00", "11:00", "A1"),
            CourseSession("FIZ101", "Fizik", 3, "13:00", "15:00", None),
        ],
    )

    result = await call(registry, context, "course_schedule", day="3")

    assert [row["course_code"] for row in rows(result, "sessions")] == ["FIZ101"]


async def test_course_schedule_rejects_day_out_of_range(
    registry: Registry, context: ToolContext
) -> None:
    result = await call(registry, context, "course_schedule", day="9")
    assert not result.ok


# --- zamanlanmış görevler --------------------------------------------------------------


async def test_task_create_rejects_malformed_time(
    registry: Registry, context: ToolContext
) -> None:
    result = await call(
        registry, context, "task_create", due="yarın sabah", message="çöpü çıkar"
    )

    assert not result.ok
    assert context.tasks.pending() == []


async def test_task_create_list_and_cancel(registry: Registry, context: ToolContext) -> None:
    created = await call(
        registry, context, "task_create", due="2026-08-10T07:00:00Z", message="çöpü çıkar"
    )
    assert created.data is not None
    listed = await call(registry, context, "task_list")
    assert len(rows(listed, "tasks")) == 1

    cancelled = await call(registry, context, "task_cancel", id=str(created.data["id"]))

    assert cancelled.ok
    assert context.tasks.pending() == []
    assert context.tasks.settle(int(str(created.data["id"])), TaskStatus.IPTAL) is None
