"""Hava durumu (§9.5, §11.1): skill, sağlayıcı adaptörü, varsayılan konum, `.env` ve config."""

import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from fakes import FakeClock
from mayen.adapters.storage.sqlite import Database, SqlitePersonStore
from mayen.adapters.weather.openweathermap import OpenWeatherMap
from mayen.app.config import ConfigError, load, with_dotenv
from mayen.app.main import main
from mayen.app.wiring import ToolCtx, discover_skills
from mayen.core.devices import NO_DEVICE
from mayen.core.profile import speaker
from mayen.ports.tools import Caller, Role, SkillConfig, Status
from mayen.ports.weather import Weather, WeatherError, WeatherFailure
from mayen.skills import weather
from test_app import config_dir

OWNER = Caller(Role.OWNER, "1", has_personal_device=True)
KEY = "0123456789abcdef0123456789abcdef"


class Source:
    def __init__(self, fail: WeatherFailure | None = None) -> None:
        self.asked: list[str] = []
        self._fail = fail

    async def current(self, place: str) -> Weather:
        self.asked.append(place)
        if self._fail is not None:
            raise WeatherError(self._fail, "no")
        return Weather(place.title(), 11.3, 10.6, "overcast clouds", 82, 0.96)


def ctx(source: Source, location: str | None) -> ToolCtx:
    return ToolCtx(None, None, FakeClock(), NO_DEVICE, source, location, OWNER, {})  # type: ignore[arg-type]


async def test_a_said_place_wins_over_the_default_location() -> None:
    source = Source()
    result = await weather.run(
        weather.Args(where=weather.Where.NAMED, place="İzmir"), ctx(source, "Denizli")
    )
    assert source.asked == ["İzmir"]
    assert result.status is Status.OK
    assert result.data == {
        "place": "İzmir",
        "default_location": False,
        "temperature_c": 11,
        "feels_like_c": 11,
        "condition": "overcast clouds",
        "humidity_percent": 82,
        "wind_m_s": 1.0,
    }


async def test_the_default_location_is_the_callers_own_or_the_model_asks() -> None:
    source = Source()
    default = weather.Where.USER_DEFAULT
    # Varsayılan seçilince yanına yazılmış bir yer uydurmadır, kullanılmaz.
    result = await weather.run(
        weather.Args(where=default, place="London"), ctx(source, "Denizli")
    )
    assert source.asked == ["Denizli"] and result.data["default_location"] is True
    nowhere = await weather.run(weather.Args(where=default), ctx(source, None))
    assert nowhere.status is Status.ERROR and "ask" in (nowhere.error or "")
    unnamed = await weather.run(weather.Args(where=weather.Where.NAMED), ctx(source, "Denizli"))
    assert unnamed.status is Status.ERROR and "ask" in (unnamed.error or "")
    assert source.asked == ["Denizli"]


async def test_a_provider_failure_is_a_result_not_an_exception() -> None:
    result = await weather.run(
        weather.Args(where=weather.Where.NAMED, place="x"),
        ctx(Source(WeatherFailure.NOT_FOUND), None),
    )
    assert result.status is Status.ERROR and result.data == {"failure": "not_found"}


def test_weather_is_in_the_catalog_only_when_configured() -> None:
    assert weather.spec(SkillConfig()) is None
    spec = weather.spec(SkillConfig(weather=True))
    assert spec is not None and spec.sends_outside
    assert "weather" not in {s.name for s in discover_skills()}


def _reply(status: int, body: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
    def urlopen(url: str, timeout: float) -> Any:  # noqa: ANN401
        assert KEY in url and "units=metric" in url
        if status != 200:
            raise urllib.error.HTTPError(url, status, "x", {}, io.BytesIO(b"{}"))  # type: ignore[arg-type]
        return io.BytesIO(json.dumps(body).encode())

    return urlopen


OWM = {
    "name": "Denizli Province",
    "main": {"temp": 11.32, "feels_like": 10.65, "humidity": 82},
    "weather": [{"description": "overcast clouds"}],
    "wind": {"speed": 0.96},
}


async def test_the_adapter_reads_the_provider_and_never_puts_the_key_in_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = OpenWeatherMap("https://example/weather", SecretStr(KEY))
    monkeypatch.setattr("urllib.request.urlopen", _reply(200, OWM))
    now = await source.current("Denizli")
    assert now == Weather("Denizli Province", 11.32, 10.65, "overcast clouds", 82, 0.96)
    for status, failure in (
        (404, "not_found"),
        (401, "rejected"),
        (429, "rejected"),
        (500, "unavailable"),
    ):
        monkeypatch.setattr("urllib.request.urlopen", _reply(status))
        with pytest.raises(WeatherError) as caught:
            await source.current("Denizli")
        assert caught.value.failure.value == failure and KEY not in str(caught.value)
    monkeypatch.setattr("urllib.request.urlopen", _reply(200, {"name": "x"}))
    with pytest.raises(WeatherError):
        await source.current("Denizli")


def test_dotenv_sits_beside_the_config_and_the_environment_wins(tmp_path: Path) -> None:
    path = tmp_path / "mayen.yaml"
    assert with_dotenv(path, {"A": "1"}) == {"A": "1"}
    (tmp_path / ".env").write_text(
        "# yorum\n\nOPENWEATHERMAP_KEY='abc'\nexport B=2\nA=dosya\n", encoding="utf-8"
    )
    assert with_dotenv(path, {"A": "1"}) == {"OPENWEATHERMAP_KEY": "abc", "B": "2", "A": "1"}
    (tmp_path / ".env").write_text("SECRET-VALUE-WITHOUT-NAME\n", encoding="utf-8")
    with pytest.raises(ConfigError) as caught:
        with_dotenv(path, {})
    assert "SECRET" not in str(caught.value)  # satırın kendisi bir anahtar olabilir


def test_a_weather_section_without_its_key_is_a_config_error(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    section = "\nweather: {url: 'https://example/weather', api_key_env: OWM_KEY}\n"
    path.write_text(path.read_text(encoding="utf-8") + section, encoding="utf-8")
    with pytest.raises(ConfigError, match="OWM_KEY"):
        load(path, {"MAYEN_MODEL": "local"})
    config = load(path, {"MAYEN_MODEL": "local", "OWM_KEY": KEY})
    assert config.weather is not None and config.weather.key.get_secret_value() == KEY
    assert KEY not in repr(config.weather)


def test_the_default_location_is_set_on_the_machine_and_never_reaches_the_model(
    tmp_path: Path,
) -> None:
    path = config_dir(tmp_path)
    assert main(["--config", str(path), "profile", "--location", "Denizli"]) == 1  # sahip yok
    assert main(["--config", str(path), "setup", "--name", "Sinan", "--language", "tr"]) == 0
    assert main(["--config", str(path), "profile", "--location", "Denizli"]) == 0
    with Database(tmp_path / "data" / "mayen.db") as db:
        owner = SqlitePersonStore(db).owner()
    assert owner is not None and owner.location == "Denizli"
    assert "Denizli" not in json.dumps(speaker(owner))  # konum bağlama girmez (§9.1)
    assert main(["--config", str(path), "profile", "--clear-location"]) == 0
    with Database(tmp_path / "data" / "mayen.db") as db:
        people = SqlitePersonStore(db)
        assert (owner := people.owner()) is not None and owner.location is None
        with pytest.raises(KeyError):
            people.set_location("999", "x")
