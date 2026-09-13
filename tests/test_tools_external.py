"""Dışarıya dokunan üç tool: hava durumu, sistem metrikleri, Wake-on-LAN.

Hiçbiri gerçek ağa çıkmıyor: HTTP `MockTransport` arkasında, sihirli paket yamalı bir
göndericiyle. §4'ün "GPU'suz, saniyeler içinde" kuralı burada da geçerli.
"""

from collections.abc import Mapping
from pathlib import Path

import httpx
import pytest

from mayen.adapters.fakes.desktop import FakeDesktop
from mayen.config import Config, ConfigError, Secret, load
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.courses import CourseRepository
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository
from mayen.data.repositories.tasks import TaskRepository
from mayen.policy.effects import Effect
from mayen.tools import wake_on_lan
from mayen.tools.catalog import builtin_registry
from mayen.tools.spec import ToolArgumentError, ToolContext, ToolResult

MAC = "AA:BB:CC:DD:EE:FF"


def make_context(
    tmp_path: Path,
    config: Config,
    handler: object,
    desktop: FakeDesktop | None = None,
) -> ToolContext:
    db = Database(tmp_path / "mayen.db")
    migrate(db)
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return ToolContext(
        config=config,
        http=httpx.AsyncClient(transport=transport),
        desktop=desktop if desktop is not None else FakeDesktop(),
        people=PeopleRepository(db),
        notes=NoteRepository(db),
        facts=FactRepository(db),
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


async def test_weather_fields_selects_what_comes_back(tmp_path: Path) -> None:
    """§8.3'ün liste kodlaması: `--fields temperature,condition`."""
    payload = {"main": {"temp": 31.4}, "weather": [{"description": "clear sky"}]}
    context = make_context(
        tmp_path, Config(openweathermap_key=Secret("k")), weather_reply(200, payload)
    )

    result = await run(context, "weather", city="Denizli", fields="condition")

    assert result.ok
    assert result.data == {"city": "Denizli", "condition": "clear sky"}
    assert result.speech is not None
    assert "degrees" not in result.speech


async def test_weather_without_fields_returns_everything(tmp_path: Path) -> None:
    """Alanın yokluğu boş filtre değil, filtre yok demek."""
    payload = {"main": {"temp": 31.4}, "weather": [{"description": "clear sky"}]}
    context = make_context(
        tmp_path, Config(openweathermap_key=Secret("k")), weather_reply(200, payload)
    )

    both = await run(context, "weather", city="Denizli", fields="temperature,condition")
    neither = await run(context, "weather", city="Denizli")

    assert both.data == neither.data


async def test_weather_rejects_an_unknown_field(tmp_path: Path) -> None:
    """Kural 13: tanınmayan alan sessizce atılmaz — model istediğini aldığını sanmasın."""
    payload = {"main": {"temp": 31.4}, "weather": [{"description": "clear sky"}]}
    context = make_context(
        tmp_path, Config(openweathermap_key=Secret("k")), weather_reply(200, payload)
    )

    result = await run(context, "weather", city="Denizli", fields="temperature,rüzgar")

    assert not result.ok
    assert result.error is not None
    assert "rüzgar" in result.error


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


# --- masaüstü denetimi -----------------------------------------------------------------


def _refuse(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"masaüstü tool'u ağa çıktı: {request.url}")


async def launch(context: ToolContext, name: str) -> ToolResult:
    """`run()`'ın kendi `name` parametresiyle çakışmasın diye ayrı bir yol.

    Defter yapılandırmadan kuruluyor: açılabilir adlar gramere seçenek olarak giriyor.
    """
    tool = builtin_registry(context.config).get("app_launch")
    return await tool.handler(context, tool.validate({"name": name}))


def desktop_context(
    tmp_path: Path, desktop: FakeDesktop, config: Config | None = None
) -> ToolContext:
    return make_context(tmp_path, config or Config(), _refuse, desktop)


async def test_volume_reads_when_no_level_is_given(tmp_path: Path) -> None:
    desktop = FakeDesktop(level=35)
    result = await run(desktop_context(tmp_path, desktop), "volume")
    assert result.ok
    assert result.data == {"seviye": 35}
    assert desktop.level == 35


async def test_volume_sets_the_level(tmp_path: Path) -> None:
    desktop = FakeDesktop(level=35)
    assert (await run(desktop_context(tmp_path, desktop), "volume", level="70")).ok
    assert desktop.level == 70


async def test_volume_out_of_range_is_refused(tmp_path: Path) -> None:
    """Gramer `cli-integer`'ı sınırsız üretir; %5000 duyulur bir kaza."""
    desktop = FakeDesktop(level=35)
    result = await run(desktop_context(tmp_path, desktop), "volume", level="5000")
    assert not result.ok
    assert desktop.level == 35


async def test_media_control_names_the_player_it_affected(tmp_path: Path) -> None:
    desktop = FakeDesktop(player="firefox")
    result = await run(desktop_context(tmp_path, desktop), "media_control", action="next")
    assert result.ok
    assert desktop.medias == ["next"]
    assert "firefox" in result.speech


async def test_media_control_without_a_player_is_an_error_not_a_lie(tmp_path: Path) -> None:
    """ "Duraklattım" demek, hiçbir şey duraklatmamışken yanlış olur."""
    desktop = FakeDesktop(player=None)
    result = await run(desktop_context(tmp_path, desktop), "media_control", action="pause")
    assert not result.ok


async def test_window_action_does_not_offer_closing(tmp_path: Path) -> None:
    """Kapatmanın bedeli farklı: ayrı tool, GERİ_ALINAMAZ, onaydan geçiyor.

    Reddediş **doğrulamada**: hatalı çağrı kullanıcıya sorulmaz, modele geri beslenir
    (§8.5). Gramerde de üretilemez, ama gramer bir güvenlik sınırı değil.
    """
    desktop = FakeDesktop()
    with pytest.raises(ToolArgumentError):
        await run(desktop_context(tmp_path, desktop), "window_action", action="close")
    assert desktop.windows == []


async def test_window_close_is_a_separate_irreversible_tool(tmp_path: Path) -> None:
    desktop = FakeDesktop()
    assert (await run(desktop_context(tmp_path, desktop), "window_close")).ok
    assert desktop.windows == ["close"]
    assert builtin_registry().get("window_close").effect is Effect.GERI_ALINAMAZ
    assert builtin_registry().get("window_action").effect is Effect.DIS


async def test_app_launch_refuses_an_application_outside_the_list(tmp_path: Path) -> None:
    """Değişmez 8: modelin yazdığı komut çalıştırılmaz, listedeki ad çalıştırılır."""
    desktop = FakeDesktop()
    config = Config(apps={"tarayici": ("firefox",)})
    with pytest.raises(ToolArgumentError):
        await launch(desktop_context(tmp_path, desktop, config), "rm")
    assert desktop.launched == []


async def test_app_launch_runs_the_configured_argv(tmp_path: Path) -> None:
    desktop = FakeDesktop()
    config = Config(apps={"tarayici": ("firefox", "--new-window")})
    result = await launch(desktop_context(tmp_path, desktop, config), "tarayici")
    assert result.ok
    assert desktop.launched == [("firefox", "--new-window")]


def test_apps_are_read_from_the_config_file(tmp_path: Path) -> None:
    path = tmp_path / "apps.toml"
    path.write_text('[apps]\ntarayici = ["firefox", "--new-window"]\n', encoding="utf-8")

    config = load({"MAYEN_APPS_PATH": str(path)})

    assert config.apps == {"tarayici": ("firefox", "--new-window")}


def test_an_application_command_must_be_a_non_empty_list(tmp_path: Path) -> None:
    """Tek metin kabul edilseydi onu bölmek bir kabuk ayrıştırması isterdi (Değişmez 8)."""
    path = tmp_path / "apps.toml"
    path.write_text('[apps]\ntarayici = "firefox --new-window"\n', encoding="utf-8")

    with pytest.raises(ConfigError):
        load({"MAYEN_APPS_PATH": str(path)})


def test_unreadable_apps_file_is_not_an_empty_list(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load({"MAYEN_APPS_PATH": str(tmp_path / "yok.toml")})


async def test_the_body_refuses_an_unknown_application_too(tmp_path: Path) -> None:
    """Gramer onu üretemez, ama gramer bir güvenlik sınırı değil (Değişmez 4): doğrulamayı
    atlayan bir yol kalırsa gövde yine de reddetmeli."""
    desktop = FakeDesktop()
    config = Config(apps={"tarayici": ("firefox",)})
    tool = builtin_registry(config).get("app_launch")
    result = await tool.handler(desktop_context(tmp_path, desktop, config), {"name": "rm"})
    assert not result.ok
    assert "tarayici" in (result.error or "")
    assert desktop.launched == []


def test_without_a_configured_application_the_tool_is_not_in_the_catalog() -> None:
    """Hiçbir şey açamayan bir tool katalogda yalnızca token tutardı."""
    assert "app_launch" not in builtin_registry(Config())
    assert "app_launch" in builtin_registry(Config(apps={"tarayici": ("firefox",)}))


def test_an_application_name_must_fit_the_grammar(tmp_path: Path) -> None:
    """Adlar gramere seçenek olarak giriyor; boşluklu bir ad orada değeri bölerdi."""
    path = tmp_path / "apps.toml"
    path.write_text('[apps]\n"metin duzenleyici" = ["kwrite"]\n', encoding="utf-8")

    with pytest.raises(ConfigError):
        load({"MAYEN_APPS_PATH": str(path)})
