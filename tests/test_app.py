"""Bağlama ve açılış (§4, §14): config, skill keşfi, oturum kurulumu, çıkış kodu."""

import asyncio
import shutil
import sys
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest
import uvicorn
from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
from websockets.typing import Origin

from fakes import FakeClock, speech_service
from mayen.adapters.storage.sqlite import (
    Database,
    SqliteNoteStore,
    SqlitePersonStore,
    SqliteTimerStore,
)
from mayen.app.config import ConfigError, load
from mayen.app.main import EXIT_CONFIG, EXIT_REFUSED, main
from mayen.app.server import TEXT_PATH, VOICE_PATH, LoopbackIsLocal, core_app
from mayen.app.wiring import (
    Core,
    ToolCtx,
    Voice,
    discover_skills,
    skill_defaults,
    voice_session,
)
from mayen.core.devices import NO_DEVICE
from mayen.core.policy import ROLE_TABLE
from mayen.pipeline.speech import ServiceTurn
from mayen.ports.channels import VoiceHello
from mayen.ports.devices import Capabilities, Capability, Command, CommandResult
from mayen.ports.people import LOCAL_DEVICE, DeviceId
from mayen.ports.tools import Caller, Effect, Role, Sensitivity, SkillConfig, Status
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
    rule = "Answer in {language}."
    (tmp_path / "prompts" / "language.txt").write_text(rule, encoding="utf-8")
    return path


def test_example_config_loads(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    assert config.system_prompt == "You are Mayen."
    assert config.language_rule == "Answer in {language}."
    assert config.storage_path == tmp_path / "data" / "mayen.db"
    assert config.triggers.fates[TriggerSource.TEXT] is Fate.RESTART


def test_home_in_storage_path_is_expanded(tmp_path: Path) -> None:
    shutil.copy(EXAMPLE, tmp_path / "mayen.yaml")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "system.txt").write_text("x", encoding="utf-8")
    (tmp_path / "prompts" / "language.txt").write_text("{language}", encoding="utf-8")
    config = load(tmp_path / "mayen.yaml", {"MAYEN_MODEL": "local"})
    assert config.storage_path == Path.home() / ".local/share/mayen/mayen.db"


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (("settle_s: 1.0", "settle: 1.0"), "settle"),  # yanlış yazılmış anahtar
        (("    event: restart\n", ""), "event"),  # akıbeti eksik kaynak
        (("timer: restart", "timer: resume"), "timer"),  # hatta karşılığı olmayan akıbet
        (("system: prompts/system.txt", "system: prompts/none.txt"), "none.txt"),
        (("timer: {}", "timer: {READ: [SECRET]}"), "SECRET"),
        # tanınmayan kişinin dilinde ses yok: ilk yabancıya asistan susar
        (("    English: default", "    Turkish: default"), "default_language"),
    ],
)
def test_bad_config_is_a_config_error(
    tmp_path: Path, change: tuple[str, str], match: str
) -> None:
    text = EXAMPLE.read_text(encoding="utf-8").replace(*change)
    with pytest.raises(ConfigError, match=match):
        load(config_dir(tmp_path, text), {"MAYEN_MODEL": "local"})


def test_language_rule_without_the_slot_is_a_config_error(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    (tmp_path / "prompts" / "language.txt").write_text("Answer in English.", encoding="utf-8")
    with pytest.raises(ConfigError, match="language"):
        load(path, {"MAYEN_MODEL": "local"})


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
        "audio_output",
        "media",
        "note_add",
        "note_delete",
        "note_search",
        "reminder_add",
        "reminder_delete",
        "reminder_list",
        "time",
        "volume",
        "window",
        "window_close",
    ]


def ctx_for(db: Database, defaults: dict[str, object] | None = None) -> ToolCtx:
    return ToolCtx(
        SqliteNoteStore(db),
        SqliteTimerStore(db),
        FakeClock(),
        NO_DEVICE,
        None,
        None,
        OWNER,
        defaults or {},
    )


async def test_note_skills_share_the_store(tmp_path: Path) -> None:
    with Database(tmp_path / "m.db") as db:
        ctx = ctx_for(db)
        added = await note_add.run(note_add.Args(text="Yarın saat üçte dişçi"), ctx)
        assert added.data == {"id": "1"}
        found = await note_search.run(note_search.Args(query="DİŞÇİ"), ctx)
        assert [r.data for r in found.records] == [{"id": "1", "text": "Yarın saat üçte dişçi"}]
        assert found.records[0].sensitivity is Sensitivity.PERSONAL
        assert found.data == {"found": 1}
        missing = await note_search.run(note_search.Args(query="berber"), ctx)
        assert missing.data == {"found": 0}
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
        "system_role:\n  timer: {}", "system_role: {}"
    )
    config = load(config_dir(tmp_path, text), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db, pytest.raises(ConfigError, match="timer"):
        Core(config, db)


def test_system_role_rights_follow_the_turn_source(tmp_path: Path) -> None:
    text = EXAMPLE.read_text(encoding="utf-8").replace("timer: {}", "timer: {READ: [GENERAL]}")
    config = load(config_dir(tmp_path, text), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        core = Core(config, db)
        assert core.table("s1") is ROLE_TABLE
        timer_table = core.tables[TriggerSource.TIMER]
        assert timer_table[(Role.SYSTEM, Effect.READ, Sensitivity.GENERAL)]
        assert not timer_table[(Role.SYSTEM, Effect.READ, Sensitivity.PERSONAL)]
        assert not timer_table[(Role.SYSTEM, Effect.WRITE, Sensitivity.GENERAL)]


def test_empty_system_role_closes_every_cell(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        timer_table = Core(config, db).tables[TriggerSource.TIMER]
        assert not any(v for (role, _, _), v in timer_table.items() if role is Role.SYSTEM)


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

        languages: list[str] = []

        def tts(language: Callable[[], str]) -> FrameProcessor:
            languages.append(language())
            return Passing()

        turn = ServiceTurn("http://127.0.0.1:9")
        voice = Voice(
            Passing(), Passing(), tts, Passing(), SilentVAD(), turn, caller, LOCAL_DEVICE
        )
        session = voice_session(core, "s1", voice)
        assert session.gate.session == "s1"
        assert core.sessions.running("s1") is None
        # Turu yokken dinleyen bilinmez: ses varsayılan dilden seçilir (§8.6).
        assert languages == [config.default_language]
        # Sözün bitişini bulan model çekirdekte yüklenmez (§18); Pipecat'in varsayılanı yükler.
        assert "pipecat.audio.turn.smart_turn.local_smart_turn_v3" not in sys.modules


def test_wake_word_is_read_and_wired(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    body = path.read_text(encoding="utf-8").replace(
        "  # wake:", "  wake:\n    threshold: 0.5\n    follow_up_s: 3\n  # wake:"
    )
    path.write_text(body, encoding="utf-8")
    config = load(path, {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        core = Core(config, db)
        wake = core.wake()
        assert wake is not None and wake.follow_up_s == 3
        voice = Voice(
            Passing(),
            Passing(),
            lambda _: Passing(),
            Passing(),
            SilentVAD(),
            ServiceTurn("http://127.0.0.1:9"),
            None,
            LOCAL_DEVICE,
            wake,
        )
        assert voice_session(core, "s1", voice).gate.session == "s1"


def test_speaker_recognition_is_read_and_its_threshold_is_required(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    plain = path.read_text(encoding="utf-8")
    path.write_text(plain + "speaker:\n  url: http://127.0.0.1:9\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="threshold"):
        load(path, {"MAYEN_MODEL": "local"})
    path.write_text(
        plain + "speaker:\n  url: http://127.0.0.1:9\n  threshold: 0.5\n", encoding="utf-8"
    )
    config = load(path, {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        core = Core(config, db)
        assert core.matcher is not None and core.matcher.threshold == 0.5
        assert core.recognizer() is not None


def test_without_speaker_recognition_the_words_belong_to_the_device(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        assert Core(config, db).recognizer() is None


def test_without_wake_word_in_the_config_there_is_none(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    with Database(tmp_path / "m.db") as db:
        assert Core(config, db).wake() is None


def test_setup_sets_up_the_owner_once(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    args = ["--config", str(path), "setup", "--name", "Sinan", "--language", "tr"]
    assert main([*args, "--device", "local", "--device", "nPhone"]) == 0
    assert main(args) == EXIT_REFUSED
    with Database(tmp_path / "data" / "mayen.db") as db:
        owner = SqlitePersonStore(db).owner()
    assert owner is not None and owner.devices == (LOCAL_DEVICE, DeviceId("nPhone"))


def test_setup_needs_no_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAYEN_MODEL", raising=False)
    path = config_dir(tmp_path)
    assert main(["--config", str(path), "setup", "--name", "S", "--language", "tr"]) == 0


def test_setup_with_a_broken_config_is_a_config_error(tmp_path: Path) -> None:
    path = config_dir(tmp_path, "storage: {}\n")
    assert main(["--config", str(path), "setup", "--name", "S", "--language", "tr"]) == (
        EXIT_CONFIG
    )


class FixedIdentity:
    def __init__(self) -> None:
        self.next: DeviceId | None = None
        self.asked: list[str] = []

    async def device(self, address: str) -> DeviceId | None:
        self.asked.append(address)
        return self.next


async def until(condition: Callable[[], bool]) -> None:
    for _ in range(200):
        if condition():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition never held")


async def test_each_connection_gets_a_session_from_its_device(tmp_path: Path) -> None:
    config = load(config_dir(tmp_path), {"MAYEN_MODEL": "local"})
    config.storage_path.parent.mkdir(parents=True)
    with Database(config.storage_path) as db:
        core = Core(config, db)
        owner = core.people.create_owner("Sinan", "tr", None, (DeviceId("nPhone"),))
        identity = FixedIdentity()
        server = uvicorn.Server(
            uvicorn.Config(core_app(core, identity), host="127.0.0.1", port=0, log_config=None)
        )
        serving = asyncio.create_task(server.serve())
        await until(lambda: server.started)
        port = server.servers[0].sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}{TEXT_PATH}"
        try:
            # Tarayıcıdan gelen bağlantı reddedilir (Origin başlığı).
            with pytest.raises(InvalidStatus):
                async with connect(url, origin=Origin("http://example.com")):
                    pass
            async with connect(url):
                await until(lambda: len(core.sessions.names()) == 1)
                [unverified] = core.sessions.names()
                assert core.presence.personal(unverified) is None
            await until(lambda: core.sessions.names() == [])
            identity.next = DeviceId("nPhone")
            async with connect(url):
                await until(lambda: len(core.sessions.names()) == 1)
                [phone] = core.sessions.names()
                assert core.presence.personal(phone) == owner.id
                assert core.presence.target(owner.id, Sensitivity.PERSONAL) == phone
            await until(lambda: core.sessions.names() == [])
            assert core.presence.target(owner.id, Sensitivity.PERSONAL) is None
            assert identity.asked == ["127.0.0.1", "127.0.0.1"]
        finally:
            server.should_exit = True
            await serving


def _voice_config(tmp_path: Path, url: str | None) -> Path:
    path = config_dir(tmp_path)
    body = path.read_text(encoding="utf-8")
    if url is None:
        body = body[: body.index("stt:")] + body[body.index("system_role:") :]
    else:
        body = body.replace("http://127.0.0.1:8770", url).replace("http://127.0.0.1:8771", url)
    path.write_text(body, encoding="utf-8")
    return path


async def test_voice_connection_gets_a_session_from_its_device(tmp_path: Path) -> None:
    async with speech_service() as (service, url):
        service.voices = ["default"]  # örnek config'in sesi
        config = load(_voice_config(tmp_path, url), {"MAYEN_MODEL": "local"})
        config.storage_path.parent.mkdir(parents=True)
        with Database(config.storage_path) as db:
            core = Core(config, db)
            owner = core.people.create_owner("Sinan", "tr", None, (DeviceId("nLaptop"),))
            identity = FixedIdentity()
            identity.next = DeviceId("nLaptop")
            server = uvicorn.Server(
                uvicorn.Config(
                    core_app(core, identity), host="127.0.0.1", port=0, log_config=None
                )
            )
            serving = asyncio.create_task(server.serve())
            await until(lambda: server.started)
            port = server.servers[0].sockets[0].getsockname()[1]
            url = f"ws://127.0.0.1:{port}{VOICE_PATH}"
            try:
                with pytest.raises(InvalidStatus):
                    async with connect(url, origin=Origin("http://example.com")):
                        pass
                async with connect(url) as ws:
                    hello = VoiceHello.decode(await ws.recv())
                    assert hello.input_sample_rate == 16000
                    await until(lambda: len(core.sessions.names()) == 1)
                    [laptop] = core.sessions.names()
                    assert laptop.startswith("voice-")
                    assert core.presence.personal(laptop) == owner.id
                    # Ses akar; sessizlik bir tur açmaz, bağlantı ayakta kalır.
                    for _ in range(10):
                        await ws.send(b"\x00\x00" * 320)
                    await asyncio.sleep(0.2)
                    assert core.sessions.running(laptop) is None
                    # Cihaz komutu sesle aynı bağlantıdan gider ve sonucu oradan döner (§9.7).
                    link = core.devices.get(laptop)
                    await ws.send(Capabilities(frozenset({Capability.SPEAKER})).encode())
                    await until(
                        lambda: core.devices.capabilities(laptop) == {Capability.SPEAKER}
                    )
                    running = asyncio.create_task(
                        link.run(Capability.SPEAKER, "set_volume", {"level": 30})
                    )
                    message = await ws.recv()
                    while not isinstance(message, str):  # araya giren ses parçaları
                        message = await ws.recv()
                    command = Command.decode(message)
                    assert (command.action, command.args) == ("set_volume", {"level": 30})
                    await ws.send(CommandResult(command.id, Status.OK, {"level": 30}).encode())
                    assert (await running).data == {"level": 30}
                await until(lambda: core.sessions.names() == [])
                assert core.devices.capabilities(laptop) == frozenset()
            finally:
                server.should_exit = True
                await serving


async def test_without_speech_services_there_is_no_voice_channel(tmp_path: Path) -> None:
    config = load(_voice_config(tmp_path, None), {"MAYEN_MODEL": "local"})
    config.storage_path.parent.mkdir(parents=True)
    with Database(config.storage_path) as db:
        app = core_app(Core(config, db), FixedIdentity())
    assert VOICE_PATH not in {getattr(r, "path", None) for r in app.routes}
    assert TEXT_PATH in {getattr(r, "path", None) for r in app.routes}


class NoIdentity:
    def __init__(self) -> None:
        self.asked: list[str] = []

    async def device(self, address: str) -> DeviceId | None:
        self.asked.append(address)
        return None


async def test_this_machine_is_the_local_device_and_the_rest_is_verified() -> None:
    inner = NoIdentity()
    identity = LoopbackIsLocal(inner)
    assert await identity.device("127.0.0.1") == LOCAL_DEVICE
    assert await identity.device("::1") == LOCAL_DEVICE
    assert await identity.device("100.64.0.7") is None
    assert inner.asked == ["100.64.0.7"]


def test_app_entries_cannot_look_like_options(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    body = path.read_text(encoding="utf-8").replace("apps: {}", "apps: {Steam: --help}")
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ConfigError, match="desktop entry"):
        load(path, {"MAYEN_MODEL": "local"})
    path.write_text(body.replace("--help", "steam"), encoding="utf-8")
    config = load(path, {"MAYEN_MODEL": "local"})
    assert config.apps == {"Steam": "steam"}
    assert "apps" in {s.name for s in discover_skills(SkillConfig(apps=config.apps))}
