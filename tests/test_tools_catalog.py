"""§9.2 kataloğunun gövdeleri: gerçek veritabanı, fake yok — repository'ler zaten hızlı."""

from pathlib import Path

import httpx
import pytest

from mayen.adapters.fakes.desktop import FakeDesktop
from mayen.config import Config
from mayen.data import clock
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.courses import CourseRepository, CourseSession
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository, Tier
from mayen.data.repositories.tasks import TaskRepository, TaskStatus
from mayen.policy.effects import Effect
from mayen.tools.catalog import builtin_registry
from mayen.tools.registry import Registry
from mayen.tools.spec import (
    Arg,
    ArgType,
    ToolArgumentError,
    ToolContext,
    ToolResult,
    ToolSpecError,
)

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
        desktop=FakeDesktop(),
        people=PeopleRepository(db),
        notes=NoteRepository(db),
        facts=FactRepository(db),
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
        registry, context, "task_create", due="2026-08-10 07:00", message="çöpü çıkar"
    )
    assert created.data is not None
    listed = await call(registry, context, "task_list")
    assert len(rows(listed, "tasks")) == 1

    cancelled = await call(registry, context, "task_cancel", id=str(created.data["id"]))

    assert cancelled.ok
    assert context.tasks.pending() == []
    assert context.tasks.settle(int(str(created.data["id"])), TaskStatus.IPTAL) is None


# --- kalıcı bellek (§11.3) -------------------------------------------------------------


async def test_fact_list_shows_source_and_date(
    registry: Registry, context: ToolContext
) -> None:
    """§11.3: göremediği belleği kullanıcı hata ayıklayamaz."""
    ali = context.people.create("Ali", Tier.KAYITLI_KISI)
    context.facts.create("kahveyi sade içer", person_id=ali.id)

    result = await call(registry, context, "fact_list")
    assert result.ok
    listed = rows(result, "olgular")
    assert listed[0]["kisi"] == "Ali"
    assert listed[0]["icerik"] == "kahveyi sade içer"
    assert listed[0]["tarih"]


async def test_fact_forget_deletes_by_number(registry: Registry, context: ToolContext) -> None:
    fact = context.facts.create("kahveyi sade içer")
    assert (await call(registry, context, "fact_forget", id=str(fact.id))).ok
    assert context.facts.list_all() == []


async def test_fact_forget_reports_a_missing_fact(
    registry: Registry, context: ToolContext
) -> None:
    result = await call(registry, context, "fact_forget", id="404")
    assert not result.ok
    assert "404" in (result.error or "")


def test_forgetting_is_irreversible(registry: Registry) -> None:
    """Silinen olgunun geri getirileceği yer yok; §10.2'ye göre sahipte bile onay ister."""
    assert registry.get("fact_forget").effect is Effect.GERI_ALINAMAZ
    assert registry.get("fact_list").effect is Effect.OKUMA


async def test_fact_save_writes_what_the_user_asked_to_remember(
    registry: Registry, context: ToolContext
) -> None:
    result = await call(registry, context, "fact_save", content="kahveyi sade içerim")
    assert result.ok
    assert [fact.content for fact in context.facts.list_all()] == ["kahveyi sade içerim"]


async def test_a_saved_fact_is_not_attributed_to_anyone(
    registry: Registry, context: ToolContext
) -> None:
    """Bilinen eksik, sessiz değil: `ToolContext` süreç başına kuruluyor, konuşanı görmüyor.
    §19.3 açık olduğu sürece zaten `person_id` üretilmiyor."""
    await call(registry, context, "fact_save", content="x")
    assert context.facts.list_all()[0].person_id is None


# --- seçenekli alan (ArgType.ENUM) ------------------------------------------------------


def test_an_invalid_choice_is_refused_by_the_definition_too(registry: Registry) -> None:
    """Gramer onu üretilemez kılıyor ama gramer bir güvenlik sınırı değil (Değişmez 4);
    doğrulama da reddetmeli."""
    tool = registry.get("media_control")
    with pytest.raises(ToolArgumentError) as error:
        tool.validate({"action": "explode"})
    assert "play-pause" in str(error.value)


def test_the_catalog_shows_the_choices_not_the_type_name(registry: Registry) -> None:
    """Modelin `<enum>` görmesi ona hiçbir şey söylemezdi; katalog `usage()`'dan üretiliyor."""
    usage = registry.get("media_control").usage()
    assert "--action <play-pause|pause|next|previous|stop>" in usage


def test_choices_belong_to_enum_fields_only() -> None:
    with pytest.raises(ToolSpecError):
        Arg("action", ArgType.STRING, "eylem", choices=("close",))
    with pytest.raises(ToolSpecError):
        Arg("action", ArgType.ENUM, "eylem")


def test_a_choice_that_would_break_the_grammar_is_refused_at_definition_time() -> None:
    """Boşluk değeri böler, `<` ve `"` iki biçimin ayraçları. Tanım anında patlıyor."""
    for bad in ("show desktop", "close<", 'a"b'):
        with pytest.raises(ToolSpecError):
            Arg("action", ArgType.ENUM, "eylem", choices=(bad,))


# --- göreli zaman (2026-08-16) ----------------------------------------------------------


async def test_task_create_accepts_a_relative_time(
    registry: Registry, context: ToolContext
) -> None:
    """Toplama modelden alınıyor: `+8s` damgaya burada çevriliyor.

    Sebebi ölçüm: mutlak damga tek biçimken model altıda birinde dakika hanesini
    taşıyamıyordu — istenen 8 saniye, kurulan +65.
    """
    before = clock.parse(clock.now())
    result = await call(registry, context, "task_create", due="+8s", message="su iç")

    assert result.ok, result.error
    pending = context.tasks.pending()
    assert len(pending) == 1
    delta = (clock.parse(pending[0].due_at) - before).total_seconds()
    assert 8 <= delta <= 10, delta


async def test_relative_units_cover_minutes_hours_and_days(
    registry: Registry, context: ToolContext
) -> None:
    base = clock.parse(clock.now())
    for due in ("+5m", "+2h", "+3d"):
        result = await call(registry, context, "task_create", due=due, message="iş")
        assert result.ok, result.error
    stamps = sorted(clock.parse(task.due_at) for task in context.tasks.pending())
    assert [round((stamp - base).total_seconds(), -1) for stamp in stamps] == [
        300,
        7200,
        259200,
    ]


async def test_an_absolute_local_time_still_works(
    registry: Registry, context: ToolContext
) -> None:
    """Göreli biçim mutlağın yerine geçmiyor: "yarın dokuzda" göreli yazılamaz."""
    result = await call(
        registry, context, "task_create", due="2026-08-10 07:00", message="çöpü çıkar"
    )
    assert result.ok
    assert context.tasks.pending()[0].due_at == clock.from_local("2026-08-10 07:00")


async def test_a_utc_stamp_is_rejected(registry: Registry, context: ToolContext) -> None:
    """**2026-08-17:** damga kabul edildiği sürece model damga yazıyor ve yerel saati
    oraya koyuyor — `2026-08-18T09:00:00Z`, istenen dokuz, kurulan on iki.

    Çevrilmiş bir damga ile çevrilmemiş bir yerel saat ayırt edilemez; birini sessizce
    seçmek üç saat sapmayı sessizce seçmektir. Red §8.3'ün geri beslemesine düşüyor.
    """
    result = await call(
        registry, context, "task_create", due="2026-08-10T07:00:00Z", message="çöpü çıkar"
    )
    assert not result.ok
    assert context.tasks.pending() == []


async def test_a_relative_time_without_a_unit_is_rejected(
    registry: Registry, context: ToolContext
) -> None:
    """`+8` belirsiz: saniye mi dakika mı. Tahmin etmek sessizce yanlış saat kurmaktır."""
    result = await call(registry, context, "task_create", due="+8", message="iş")
    assert not result.ok
    assert context.tasks.pending() == []
