"""Bağlama ve açılış (§4, §14): config, skill keşfi, oturum kurulumu, çıkış kodu."""

import shutil
from pathlib import Path

import pytest
from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from mayen.adapters.storage.memory import MemoryNoteStore
from mayen.adapters.storage.sqlite import Database
from mayen.app.config import ConfigError, load
from mayen.app.main import EXIT_CONFIG, main
from mayen.app.wiring import Core, ToolCtx, Voice, discover_skills, voice_session
from mayen.core.events import SystemClock
from mayen.ports.tools import Caller, Role, Sensitivity, Status
from mayen.ports.triggers import Fate, TriggerSource
from mayen.skills import note_add, note_delete, note_search
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
        "time",
    ]


async def test_note_skills_share_the_store() -> None:
    ctx = ToolCtx(MemoryNoteStore(), SystemClock())
    added = await note_add.run(note_add.Args(text="Yarın saat üçte dişçi"), ctx)
    assert added.data == {"id": "1"}
    found = await note_search.run(note_search.Args(query="DİŞÇİ"), ctx)
    assert [r.data for r in found.records] == [{"id": "1", "text": "Yarın saat üçte dişçi"}]
    assert found.records[0].sensitivity is Sensitivity.PERSONAL
    assert (await note_delete.run(note_delete.Args(id="1"), ctx)).status is Status.OK
    assert (await note_delete.run(note_delete.Args(id="1"), ctx)).status is Status.ERROR
    assert (await time_skill.run(time_skill.NoArgs(), ctx)).status is Status.OK


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
