"""Dışarıya dokunan üç tool: hava durumu, sistem metrikleri, Wake-on-LAN.

Hiçbiri gerçek ağa çıkmıyor: HTTP `MockTransport` arkasında, sihirli paket yamalı bir
göndericiyle. §4'ün "GPU'suz, saniyeler içinde" kuralı burada da geçerli.
"""

from collections.abc import Mapping
from pathlib import Path

import httpx
import pytest

from mayen.config import Config, ConfigError, Secret, load
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.courses import CourseRepository
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository
from mayen.data.repositories.tasks import TaskRepository
from mayen.tools import wake_on_lan
from mayen.tools.catalog import builtin_registry
from mayen.tools.spec import ToolContext, ToolResult

MAC = "AA:BB:CC:DD:EE:FF"


def make_context(tmp_path: Path, config: Config, handler: object) -> ToolContext:
    db = Database(tmp_path / "mayen.db")
    migrate(db)
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return ToolContext(
        config=config,
        http=httpx.AsyncClient(transport=transport),
        people=PeopleRepository(db),
        notes=NoteRepository(db),
        courses=CourseRepository(db),
        tasks=TaskRepository(db),
        course_term="2026-guz",
    )


async def run(context: ToolContext, name: str, **raw: str) -> ToolResult:
    tool = builtin_registry().get(name)
    return await tool.handler(context, tool.validate(raw))


# --- hava durumu (§19.7) ---------------------------------------------------------------


def weather_reply(status: int, payload: Mapping[str, object] | None = None) -> object:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "appid" in request.url.params
        return httpx.Response(status, json=payload or {})

    return handler


async def test_weather_without_a_key_fails_loudly(tmp_path: Path) -> None:
    """Eksik sır sessizce boş sonuca dönmez (§14)."""
    context = make_context(tmp_path, Config(), weather_reply(200))

    result = await run(context, "weather", city="Denizli")

    assert not result.ok
    assert result.error is not None


async def test_weather_reports_temperature_and_condition(tmp_path: Path) -> None:
    payload = {"main": {"temp": 31.4}, "weather": [{"description": "clear sky"}]}
    context = make_context(
        tmp_path, Config(openweathermap_key=Secret("k")), weather_reply(200, payload)
    )

    result = await run(context, "weather", city="Denizli")

    assert result.ok
    assert result.data == {"city": "Denizli", "temperature_c": 31.4, "condition": "clear sky"}


@pytest.mark.parametrize("status", [401, 429, 404, 500])
async def test_weather_surfaces_service_errors(tmp_path: Path, status: int) -> None:
    """Kota ve anahtar hataları yutulmaz (§14, Kural 13)."""
    context = make_context(
        tmp_path, Config(openweathermap_key=Secret("k")), weather_reply(status)
    )

    result = await run(context, "weather", city="Denizli")

    assert not result.ok
    assert result.error is not None


async def test_weather_key_never_reaches_the_result(tmp_path: Path) -> None:
    context = make_context(
        tmp_path, Config(openweathermap_key=Secret("gizli")), weather_reply(401)
    )

    result = await run(context, "weather", city="Denizli")

    assert result.error is not None
    assert "gizli" not in result.error


# --- sistem metrikleri -----------------------------------------------------------------


async def test_system_metrics_reports_the_machine(tmp_path: Path) -> None:
    context = make_context(tmp_path, Config(), weather_reply(200))

    result = await run(context, "system_metrics")

    assert result.ok
    assert result.data is not None
    assert set(result.data) == {
        "cpu_percent",
        "memory_percent",
        "memory_available_gb",
        "disk_percent",
        "disk_free_gb",
    }


# --- Wake-on-LAN (§19.9) ---------------------------------------------------------------


async def test_wake_on_lan_only_accepts_configured_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ham MAC kabul edilmiyor: modelin söyleyebildiği bir adres listeyi aşardı."""
    context = make_context(tmp_path, Config(wol_targets={"masaustu": MAC}), weather_reply(200))
    monkeypatch.setattr(wake_on_lan, "_send", lambda payload: None)

    assert not (await run(context, "wake_on_lan", target=MAC)).ok
    assert (await run(context, "wake_on_lan", target="masaustu")).ok


async def test_magic_packet_layout() -> None:
    packet = wake_on_lan._magic_packet(MAC)
    assert packet.startswith(b"\xff" * 6)
    assert packet[6:] == bytes.fromhex("AABBCCDDEEFF") * 16
    assert len(packet) == 102


# --- §19.9'un yapılandırma dosyası -----------------------------------------------------


def test_wol_targets_are_read_from_the_config_file(tmp_path: Path) -> None:
    path = tmp_path / "wol.toml"
    path.write_text(f'[targets]\nmasaustu = "{MAC}"\n', encoding="utf-8")

    config = load({"MAYEN_WOL_TARGETS_PATH": str(path)})

    assert config.wol_targets == {"masaustu": MAC}


def test_unreadable_wol_file_is_not_an_empty_target_list(tmp_path: Path) -> None:
    """Kural 13: yanlış yazılmış bir yol, "hiçbir cihaz tanımlı değil" demek değildir."""
    with pytest.raises(ConfigError):
        load({"MAYEN_WOL_TARGETS_PATH": str(tmp_path / "yok.toml")})


def test_malformed_mac_is_rejected_at_load_time(tmp_path: Path) -> None:
    path = tmp_path / "wol.toml"
    path.write_text('[targets]\nmasaustu = "zz:bb"\n', encoding="utf-8")

    with pytest.raises(ConfigError):
        load({"MAYEN_WOL_TARGETS_PATH": str(path)})
