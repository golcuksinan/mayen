"""Bağlama ve açılış (§4, §14): config, skill keşfi, oturum kurulumu, çıkış kodu."""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from fakes import FakeClock
from mayen.adapters.storage.sqlite import Database, SqliteNoteStore, SqliteTimerStore
from mayen.app.config import ConfigError, load
from mayen.app.main import EXIT_CONFIG, main
from mayen.app.wiring import (
    Core,
    ToolCtx,
    Voice,
    discover_skills,
    skill_defaults,
    voice_session,
)
from mayen.core.policy import ROLE_TABLE
from mayen.ports.tools import Caller, Effect, Role, Sensitivity, Status
from mayen.ports.triggers import Fate, Priority, TriggerSource
from mayen.skills import (
    note_add,
    note_delete,
    note_search,
    reminder_add,
    reminder_delete,
    reminder_list,
)
from mayen.skills import time as time_skill

EXAMPLE = Path(__file__).resolve().parent.parent / "config" / "mayen.yaml.example"
OWNER = Caller(Role.OWNER, "owner", has_personal_device=False)


def config_dir(tmp_path: Path, text: str | None = None) -> Path:
    """Örnek config, veritabanı geçici klasörde; istenirse metni değiştirilmiş."""
    path = tmp_path / "mayen.yaml"
    shutil.copy(EXAMPLE, path)
    body = path.read_text(encoding="utf-8").replace(
        "~/.local/share/mayen/mayen.db", str(tmp_path / "data" / "mayen.db")
    )
    path.write_text(body if text is None else text, encoding="utf-8")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "system.txt").write_text("You are Mayen.", encoding="utf-8")
    return path


def test_example_config_loads(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    assert config.system_prompt == "You are Mayen."
    assert config.storage_path == tmp_path / "data" / "mayen.db"
    assert config.triggers.fates[TriggerSource.TEXT] is Fate.RESTART


def test_home_in_storage_path_is_expanded(tmp_path: Path) -> None:
    shutil.copy(EXAMPLE, tmp_path / "mayen.yaml")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "system.txt").write_text("x", encoding="utf-8")
    config = load(tmp_path / "mayen.yaml", {"MAYEN_MODEL": "local"})
    assert config.storage_path == Path.home() / ".local/share/mayen/mayen.db"


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (("settle_s: 1.0", "settle: 1.0"), "settle"),  # yanlış yazılmış anahtar
        (("    event: restart\n", ""), "event"),  # akıbeti eksik kaynak
        (("timer: restart", "timer: resume"), "timer"),  # hatta karşılığı olmayan akıbet
        (("system: prompts/system.txt", "system: prompts/none.txt"), "none.txt"),
        (("timer: {READ: [GENERAL]}", "timer: {READ: [SECRET]}"), "SECRET"),
    ],
)
def test_bad_config_is_a_config_error(
    tmp_path: Path, change: tuple[str, str], match: str
) -> None:
    text = EXAMPLE.read_text(encoding="utf-8").replace(*change)
    with pytest.raises(ConfigError, match=match):
        load(config_dir(tmp_path, text), {"MAYEN_MODEL": "local"})


def test_main_exits_with_the_config_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = config_dir(tmp_path)
    monkeypatch.delenv("MAYEN_MODEL", raising=False)
    assert main(["--config", str(path)]) == EXIT_CONFIG
    monkeypatch.setenv("MAYEN_MODEL", "local")
    assert main(["--config", str(path)]) == 0
    assert (tmp_path / "data" / "mayen.db").exists()


def test_skills_are_discovered_from_the_folder() -> None:
    assert sorted(s.name for s in discover_skills()) == [
        "note_add",
        "note_delete",
        "note_search",
        "reminder_add",
        "reminder_delete",
        "reminder_list",
        "time",
    ]


def ctx_for(db: Database, defaults: dict[str, object] | None = None) -> ToolCtx:
    return ToolCtx(
        SqliteNoteStore(db), SqliteTimerStore(db), FakeClock(), OWNER, defaults or {}
    )


async def test_note_skills_share_the_store(tmp_path: Path) -> None:
    with Database(tmp_path / "m.db") as db:
        ctx = ctx_for(db)
        added = await note_add.run(note_add.Args(text="Yarın saat üçte dişçi"), ctx)
        assert added.data == {"id": "1"}
        found = await note_search.run(note_search.Args(query="DİŞÇİ"), ctx)
        assert [r.data for r in found.records] == [{"id": "1", "text": "Yarın saat üçte dişçi"}]
        assert found.records[0].sensitivity is Sensitivity.PERSONAL
        assert (await note_delete.run(note_delete.Args(id="1"), ctx)).status is Status.OK
        assert (await note_delete.run(note_delete.Args(id="1"), ctx)).status is Status.ERROR
        assert (await time_skill.run(time_skill.NoArgs(), ctx)).status is Status.OK


async def test_reminder_skills(tmp_path: Path) -> None:
    with Database(tmp_path / "m.db") as db:
        ctx = ctx_for(db, {"tolerance_minutes": 30.0})
        added = await reminder_add.run(reminder_add.Args(text="ilacını iç", in_minutes=10), ctx)
        assert added.status is Status.OK
        [timer] = ctx.timers.pending()
        # Öncelik sırası kayıt, config, skill (§9.1): kayıtta söylenmediyse bağlamdan.
        assert (timer.tolerance_s, timer.person_id) == (1800.0, "owner")
        assert timer.due == ctx.clock.now() + timedelta(minutes=10)
        own = await reminder_add.run(
            reminder_add.Args(
                text="uyan", in_minutes=60, priority=Priority.URGENT, tolerance_minutes=0
            ),
            ctx,
        )
        assert ctx.timers.pending()[1].tolerance_s == 0.0
        listed = await reminder_list.run(reminder_list.NoArgs(), ctx)
        assert [r.data["text"] for r in listed.records] == ["ilacını iç", "uyan"]
        assert listed.records[1].data["priority"] == "urgent"
        deleted = await reminder_delete.run(reminder_delete.Args(id=own.data["id"]), ctx)
        assert deleted.status is Status.OK
        assert len(ctx.timers.pending()) == 1


@pytest.mark.parametrize(
    ("at", "in_minutes", "error"),
    [
        (None, None, "exactly one"),
        ("2026-10-13 15:00", 5.0, "exactly one"),
        ("yarın üçte", None, "look like"),
        ("2020-01-01 10:00", None, "past"),
    ],
)
async def test_reminder_needs_one_future_time(
    tmp_path: Path, at: str | None, in_minutes: float | None, error: str
) -> None:
    with Database(tmp_path / "m.db") as db:
        ctx = ctx_for(db, {"tolerance_minutes": 30.0})
        args = reminder_add.Args(text="x", at=at, in_minutes=in_minutes)
        result = await reminder_add.run(args, ctx)
        assert result.status is Status.ERROR and error in (result.error or "")
        assert ctx.timers.pending() == []


def test_config_overrides_skill_defaults() -> None:
    specs = discover_skills()
    merged = skill_defaults(specs, {"reminder_add": {"tolerance_minutes": 5}})
    assert merged["reminder_add"] == {"tolerance_minutes": 5}
    assert merged["note_add"] == {}


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"nope": {}}, "no such skill"),
        ({"reminder_add": {"tolerance": 5}}, "no such default"),
        ({"reminder_add": {"tolerance_minutes": "5"}}, "expected float"),
    ],
)
def test_bad_skill_override_is_a_config_error(
    overrides: dict[str, dict[str, object]], match: str
) -> None:
    with pytest.raises(ConfigError, match=match):
        skill_defaults(discover_skills(), overrides)


def test_timer_without_system_permissions_is_a_config_error(tmp_path: Path) -> None:
    text = EXAMPLE.read_text(encoding="utf-8").replace(
        "system_role:\n  timer: {READ: [GENERAL]}\n", "system_role: {}\n"
    )
    config = load(config_dir(tmp_path, text), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db, pytest.raises(ConfigError, match="timer"):
        Core(config, db)


def test_system_role_rights_follow_the_turn_source(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        core = Core(config, db)
        assert core.table("s1") is ROLE_TABLE
        timer_table = core.tables[TriggerSource.TIMER]
        assert timer_table[(Role.SYSTEM, Effect.READ, Sensitivity.GENERAL)]
        assert not timer_table[(Role.SYSTEM, Effect.READ, Sensitivity.PERSONAL)]
        assert not timer_table[(Role.SYSTEM, Effect.WRITE, Sensitivity.GENERAL)]


class Passing(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)


class SilentVAD(VADAnalyzer):
    def num_frames_required(self) -> int:
        return 160

    def voice_confidence(self, buffer: bytes) -> float:
        return 0.0


def test_voice_session_is_wired(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        core = Core(config, db)

        def caller(_: TranscriptionFrame) -> Caller:
            return OWNER

        voice = Voice(Passing(), Passing(), Passing(), Passing(), SilentVAD(), caller)
        session = voice_session(core, "s1", voice)
        assert session.gate.session == "s1"
        assert core.sessions.running("s1") is None
