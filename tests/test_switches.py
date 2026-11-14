"""Evdeki anahtarlar (§9.5): skill'ler, Shelly adaptörü (SHA-256 Digest) ve config."""

import hashlib
import io
import json
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from fakes import FakeClock, FakeErasing
from mayen.adapters.shelly.plugs import ShellyPlugs
from mayen.app.config import ConfigError, load
from mayen.app.wiring import ToolCtx, discover_skills
from mayen.core.devices import NO_DEVICE
from mayen.core.registry import ToolRegistry
from mayen.pipeline.tools import openai_tools
from mayen.ports.switches import SwitchError, SwitchFailure
from mayen.ports.tools import Caller, Effect, Role, SkillConfig, Status
from mayen.skills import switch, switch_state
from test_app import config_dir

OWNER = Caller(Role.OWNER, "1", has_personal_device=True)
PASSWORD = "parola-123"
NAMES = SkillConfig(switches=("gece lambası", "tv"))


class Plugs:
    def __init__(self, stuck: bool = False, fail: SwitchFailure | None = None) -> None:
        self.state = {"gece lambası": True, "tv": False}
        self.sets: list[tuple[str, bool]] = []
        self._stuck = stuck
        self._fail = fail

    async def set(self, name: str, on: bool) -> None:
        if self._fail is not None:
            raise SwitchError(self._fail, "no")
        self.sets.append((name, on))
        if not self._stuck:
            self.state[name] = on

    async def is_on(self, name: str) -> bool:
        if self._fail is not None:
            raise SwitchError(self._fail, "no")
        return self.state[name]


def ctx(plugs: Plugs) -> ToolCtx:
    no_store = None
    return ToolCtx(
        no_store,  # type: ignore[arg-type]
        no_store,  # type: ignore[arg-type]
        FakeClock(),
        NO_DEVICE,
        None,
        None,
        OWNER,
        {},
        FakeErasing(),
        FakeErasing(),
        plugs,
    )


def test_the_switch_skills_are_in_the_catalog_only_when_configured() -> None:
    assert switch.spec(SkillConfig()) is None and switch_state.spec(SkillConfig()) is None
    assert not {"switch", "switch_state"} & {s.name for s in discover_skills()}
    turn, read = switch.spec(NAMES), switch_state.spec(NAMES)
    assert turn is not None and read is not None
    assert (turn.effect, read.effect) == (Effect.EXTERNAL, Effect.READ)
    assert not turn.sends_outside and not read.sends_outside
    # Adlar katalogda sabit bir liste (§9.1); listede olmayan ad doğrulamadan geçmez.
    schema = turn.args.model_json_schema()
    assert schema["properties"]["switch"]["enum"] == ["gece lambası", "tv"]
    with pytest.raises(ValueError):
        turn.args(switch="mutfak", on=False)


def test_a_single_name_still_reaches_the_catalog_as_a_list() -> None:
    # Pydantic tek seçeneği `const` yazar; şablon onu atarsa model adı hiç görmez (§9.1).
    spec = switch.spec(SkillConfig(switches=("gece lambası",)))
    assert spec is not None
    (tool,) = openai_tools(ToolRegistry([spec]))
    name = tool["function"]["parameters"]["properties"]["switch"]
    assert name["enum"] == ["gece lambası"] and "const" not in name


async def test_switch_is_ok_only_when_the_switch_is_seen_in_the_wanted_state() -> None:
    spec = switch.spec(NAMES)
    assert spec is not None
    plugs = Plugs()
    result = await spec.run(spec.args(switch="gece lambası", on=False), ctx(plugs))
    assert result.status is Status.OK and result.data == {"switch": "gece lambası", "on": False}
    assert plugs.sets == [("gece lambası", False)] and not result.relay
    # Cihaz komutu aldı ama durum değişmedi: yapılmamış bir iş "yapıldı" diye anlatılmaz.
    stuck = await spec.run(spec.args(switch="tv", on=True), ctx(Plugs(stuck=True)))
    assert stuck.status is Status.ERROR and stuck.data == {"switch": "tv", "on": False}


async def test_switch_state_reads_the_device_and_failures_go_back_to_the_model() -> None:
    read, turn = switch_state.spec(NAMES), switch.spec(NAMES)
    assert read is not None and turn is not None
    result = await read.run(read.args(switch="tv"), ctx(Plugs()))
    assert result.status is Status.OK and result.data == {"switch": "tv", "on": False}
    for spec, args in ((read, {"switch": "tv"}), (turn, {"switch": "tv", "on": True})):
        failed = await spec.run(spec.args(**args), ctx(Plugs(fail=SwitchFailure.REJECTED)))
        assert failed.status is Status.ERROR and failed.data == {"failure": "rejected"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Device:
    """Parolalı bir Shelly: Digest'i kendisi doğrular."""

    REALM, NONCE = "shellyplugmg3-x", "AAAAAGr4ZH0L+C5M"

    def __init__(self, reachable: bool = True) -> None:
        self.on = True
        self.calls: list[str] = []
        self._reachable = reachable

    def urlopen(self, request: urllib.request.Request, timeout: float) -> Any:  # noqa: ANN401
        if not self._reachable:
            raise urllib.error.URLError("no route to host")
        assert request.full_url == "http://192.168.1.107/rpc"
        auth = request.get_header("Authorization")
        if auth is None or not self._valid(auth):
            headers = Message()
            headers["WWW-Authenticate"] = (
                f'Digest qop="auth", realm="{self.REALM}", nonce="{self.NONCE}", '
                "algorithm=SHA-256"
            )
            raise urllib.error.HTTPError(request.full_url, 401, "x", headers, io.BytesIO())
        assert isinstance(request.data, bytes)
        call = json.loads(request.data)
        self.calls.append(call["method"])
        if call["method"] == "Switch.Set":
            self.on = call["params"]["on"]
            result: dict[str, Any] = {"was_on": not self.on}
        else:
            result = {"id": 0, "output": self.on, "apower": 0.0}
        return io.BytesIO(json.dumps({"id": 1, "result": result}).encode())

    def _valid(self, auth: str) -> bool:
        fields = dict(
            part.strip().split("=", 1) for part in auth.removeprefix("Digest ").split(",")
        )
        fields = {k: v.strip('"') for k, v in fields.items()}
        ha1 = _sha(f"admin:{self.REALM}:{PASSWORD}")
        ha2 = _sha("POST:/rpc")
        expected = _sha(f"{ha1}:{self.NONCE}:{fields['nc']}:{fields['cnonce']}:auth:{ha2}")
        return fields["algorithm"] == "SHA-256" and fields["response"] == expected


async def test_the_shelly_adapter_answers_the_digest_and_keeps_the_password_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = Device()
    monkeypatch.setattr("urllib.request.urlopen", device.urlopen)
    plugs = ShellyPlugs({"gece lambası": "192.168.1.107"}, SecretStr(PASSWORD))
    await plugs.set("gece lambası", False)
    assert await plugs.is_on("gece lambası") is False
    assert device.calls == ["Switch.Set", "Switch.GetStatus"]
    wrong = ShellyPlugs({"gece lambası": "192.168.1.107"}, SecretStr("yanlış"))
    with pytest.raises(SwitchError) as caught:
        await wrong.is_on("gece lambası")
    assert caught.value.failure is SwitchFailure.REJECTED and "yanlış" not in str(caught.value)
    monkeypatch.setattr("urllib.request.urlopen", Device(reachable=False).urlopen)
    with pytest.raises(SwitchError) as caught:
        await plugs.is_on("gece lambası")
    assert caught.value.failure is SwitchFailure.UNAVAILABLE


def test_a_shelly_section_needs_its_password_and_plain_hosts(tmp_path: Path) -> None:
    path = config_dir(tmp_path)
    base = path.read_text(encoding="utf-8")

    def with_section(section: str) -> None:
        path.write_text(base + section, encoding="utf-8")

    with_section("\nshelly: {password_env: SHELLY_PW, switches: {gece lambası: 10.0.0.7}}\n")
    with pytest.raises(ConfigError, match="SHELLY_PW"):
        load(path, {"MAYEN_MODEL": "local"})
    config = load(path, {"MAYEN_MODEL": "local", "SHELLY_PW": PASSWORD})
    assert config.shelly is not None and config.shelly.hosts == {"gece lambası": "10.0.0.7"}
    assert PASSWORD not in repr(config.shelly)
    for hosts in ("{x: '10.0.0.7/rpc'}", "{x: 'a@10.0.0.7'}", "{}"):
        with_section(f"\nshelly: {{password_env: SHELLY_PW, switches: {hosts}}}\n")
        with pytest.raises(ConfigError):
            load(path, {"MAYEN_MODEL": "local", "SHELLY_PW": PASSWORD})
