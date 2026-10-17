"""Masaüstünde çalışan eylemler (§9.7): çekirdeğin komutunu bu makinede yürütür.

Bir yetenek ancak cihazda çalışıyorsa bildirilir: aracı bulunmayan yetenek beyan edilmez.
Komutlar argv dizisidir, tek dize değil (§9.4); model değeri yalnızca doğrulanmış argümanda,
argv'nin ayrı bir öğesi olarak durur.

Hoparlör, varsayılan çıkış cihazıdır; `pactl` ile (PipeWire'da da çalışır). Medya, MPRIS
arayüzünü sunan oynatıcılardır; `busctl` ile oturum veri yolundan. Okumalar JSON çıktısından
yapılır: düz metin çıktısı yerel ayara göre değişir.

Uygulamalar, sahibin bu cihazdaki tablosundan açılır (§9.4): ad → `.desktop` kimliği. Model
yalnızca tablodaki bir adı seçer; uygulama sistemin kendi tanımıyla `gtk-launch` ile açılır.
"""

import asyncio
import json
import shutil
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

import yaml

from mayen.ports.devices import Capability, Command, CommandResult
from mayen.ports.tools import Status

DEFAULT_SINK = "@DEFAULT_SINK@"


class CommandError(Exception):
    """Aracın kendisi hata verdi; sonuç `error` olur."""


type Run = Callable[[list[str]], Awaitable[str]]


async def run_argv(argv: list[str]) -> str:
    process = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await process.communicate()
    if process.returncode != 0:
        raise CommandError(err.decode(errors="replace").strip() or f"{argv[0]} failed")
    return out.decode()


async def spawn_argv(argv: list[str]) -> None:
    """Başlatır ve başlatıcının bitmesini bekler; çıktılar kapalı. Açılan uygulama boruları
    miras alsaydı, okuyan taraf uygulama kapanana kadar beklerdi."""
    process = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    if await process.wait() != 0:
        raise CommandError(f"{argv[0]} exited with {process.returncode}")


type Spawn = Callable[[list[str]], Awaitable[None]]


def load_apps(path: Path) -> dict[str, str]:
    """Tablo dosyası; yoksa boş tablo (yetenek bildirilmez). Bozuk dosya `ValueError`'dur:
    sessizce boş sayılan bir tablo, sahibin yazdığı uygulamaların açılmaması olurdu."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in data.items()
    ):
        raise ValueError(f"{path}: expected 'name: desktop-entry-id' lines")
    return dict(data)


class Executor(Protocol):
    def available(self) -> bool: ...

    async def handle(self, action: str, args: Mapping[str, Any]) -> CommandResult | None:
        """Tanınmayan eylemde `None`; sonucun `id`'sini çağıran yazar."""
        ...


def _level(sink: Mapping[str, Any]) -> int:
    """Kanalların ortalaması; seviye kanallar arasında genellikle aynıdır."""
    channels = [int(c["value_percent"].rstrip("%")) for c in sink["volume"].values()]
    return round(sum(channels) / len(channels))


class Speaker:
    def __init__(self, run: Run = run_argv) -> None:
        self._run = run

    def available(self) -> bool:
        return shutil.which("pactl") is not None

    async def _sinks(self) -> tuple[str, list[dict[str, Any]]]:
        default = (await self._run(["pactl", "get-default-sink"])).strip()
        sinks = json.loads(await self._run(["pactl", "-f", "json", "list", "sinks"]))
        return default, sinks

    async def _default(self) -> dict[str, Any]:
        default, sinks = await self._sinks()
        for sink in sinks:
            if sink["name"] == default:
                return dict(sink)
        raise CommandError(f"default output {default!r} is not in the list")

    async def handle(self, action: str, args: Mapping[str, Any]) -> CommandResult | None:
        if action == "get":
            sink = await self._default()
            data = {"level": _level(sink), "muted": bool(sink["mute"])}
            return CommandResult("", Status.OK, data)
        if action == "set_volume":
            level = int(args["level"])
            before = _level(await self._default())
            await self._run(["pactl", "set-sink-volume", DEFAULT_SINK, f"{level}%"])
            # Önceki seviye geri alma içindir (§9.6); yalnızca eylem anında bilinir.
            return CommandResult("", Status.OK, {"level": level, "previous": before})
        if action == "set_muted":
            muted = bool(args["muted"])
            before = bool((await self._default())["mute"])
            await self._run(["pactl", "set-sink-mute", DEFAULT_SINK, "1" if muted else "0"])
            return CommandResult("", Status.OK, {"muted": muted, "previous": before})
        if action == "list_outputs":
            default, sinks = await self._sinks()
            outputs = [
                {"id": s["name"], "name": s["description"], "current": s["name"] == default}
                for s in sinks
            ]
            return CommandResult("", Status.OK, {"outputs": outputs})
        if action == "set_output":
            output = str(args["output"])
            default, sinks = await self._sinks()
            if output not in {s["name"] for s in sinks}:
                return CommandResult("", Status.ERROR, error=f"no output with id {output!r}")
            await self._run(["pactl", "set-default-sink", output])
            return CommandResult("", Status.OK, {"output": output, "previous": default})
        return None


MPRIS = "org.mpris.MediaPlayer2"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER = f"{MPRIS}.Player"
MEDIA_METHODS = {
    "play": "Play",
    "pause": "Pause",
    "toggle": "PlayPause",
    "next": "Next",
    "previous": "Previous",
}


class Media:
    """Oynatıcı verilmezse çalan; çalan yoksa tek olan. Birden çoğu çalmıyorsa seçmez:
    rastgele bir seçim, kişinin istemediği oynatıcıyı çalıştırabilirdi."""

    def __init__(self, run: Run = run_argv) -> None:
        self._run = run

    def available(self) -> bool:
        return shutil.which("busctl") is not None

    async def _json(self, *args: str) -> Any:  # noqa: ANN401
        return json.loads(await self._run(["busctl", "--user", "--json=short", *args]))

    async def _property(self, bus: str, interface: str, name: str) -> Any:  # noqa: ANN401
        return (await self._json("get-property", bus, MPRIS_PATH, interface, name))["data"]

    async def _players(self) -> list[dict[str, Any]]:
        names = await self._json(
            "call",
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus",
            "ListNames",
        )
        players = []
        for bus in sorted(n for n in names["data"][0] if n.startswith(f"{MPRIS}.")):
            identity = await self._property(bus, MPRIS, "Identity")
            status = await self._property(bus, PLAYER, "PlaybackStatus")
            players.append(
                {
                    "id": bus.removeprefix(f"{MPRIS}."),
                    "name": identity,
                    "status": status.lower(),
                }
            )
        return players

    async def _track(self, bus: str) -> dict[str, str]:
        """Şarkı ve sanatçı; adres verilmez: gereksiz, kişisel olabilir."""
        metadata = await self._property(bus, PLAYER, "Metadata")
        track = {}
        title = metadata.get("xesam:title", {}).get("data")
        if title:
            track["title"] = str(title)
        artists = metadata.get("xesam:artist", {}).get("data") or []
        if artists:
            track["artist"] = ", ".join(map(str, artists))
        return track

    async def handle(self, action: str, args: Mapping[str, Any]) -> CommandResult | None:
        if action != "status" and action not in MEDIA_METHODS:
            return None
        players = await self._players()
        if action == "status":
            for player in players:
                player.update(await self._track(f"{MPRIS}.{player['id']}"))
            return CommandResult("", Status.OK, {"players": players})
        wanted = args.get("player")
        if wanted is not None:
            chosen = [p for p in players if p["id"] == wanted]
            if not chosen:
                return CommandResult(
                    "", Status.ERROR, {"players": players}, f"no player with id {wanted!r}"
                )
        else:
            chosen = [p for p in players if p["status"] == "playing"] or players
        if not chosen:
            return CommandResult("", Status.ERROR, error="no media player is open")
        if len(chosen) > 1:
            return CommandResult(
                "", Status.ERROR, {"players": players}, "several players; say which one"
            )
        [player] = chosen
        bus = f"{MPRIS}.{player['id']}"
        method = MEDIA_METHODS[action]
        await self._run(["busctl", "--user", "call", bus, MPRIS_PATH, PLAYER, method])
        data = {"player": player["name"], "id": player["id"], **await self._track(bus)}
        return CommandResult("", Status.OK, data)


class Apps:
    def __init__(self, table: Mapping[str, str], spawn: Spawn = spawn_argv) -> None:
        self._table = {name.casefold(): (name, entry) for name, entry in table.items()}
        self._spawn = spawn

    def available(self) -> bool:
        return bool(self._table) and shutil.which("gtk-launch") is not None

    async def handle(self, action: str, args: Mapping[str, Any]) -> CommandResult | None:
        names = sorted(name for name, _ in self._table.values())
        if action == "list":
            return CommandResult("", Status.OK, {"apps": names})
        if action != "open":
            return None
        if not args.get("app"):
            return CommandResult("", Status.ERROR, {"apps": names}, "say which app to open")
        found = self._table.get(str(args["app"]).casefold())
        if found is None:
            return CommandResult(
                "", Status.ERROR, {"apps": names}, f"{args['app']!r} is not in the list"
            )
        name, entry = found
        await self._spawn(["gtk-launch", entry])
        return CommandResult("", Status.OK, {"opened": name})


class Desktop:
    """Bu makinenin yürütücüleri; yetenek, yürütücüsü çalışabiliyorsa bildirilir."""

    def __init__(
        self,
        executors: Mapping[Capability, Executor] | None = None,
        apps: Mapping[str, str] | None = None,
    ) -> None:
        default: dict[Capability, Executor] = {
            Capability.SPEAKER: Speaker(),
            Capability.MEDIA: Media(),
            Capability.APPS: Apps(apps or {}),
        }
        self._executors = default if executors is None else dict(executors)

    def capabilities(self) -> frozenset[Capability]:
        return frozenset(c for c, e in self._executors.items() if e.available())

    async def handle(self, command: Command) -> CommandResult:
        executor = self._executors.get(command.capability)
        if executor is None or not executor.available():
            return CommandResult(command.id, Status.UNSUPPORTED, error="no such capability")
        try:
            result = await executor.handle(command.action, command.args)
        except (CommandError, KeyError, ValueError, TypeError, OSError) as e:
            return CommandResult(command.id, Status.ERROR, error=str(e) or type(e).__name__)
        if result is None:
            return CommandResult(
                command.id, Status.UNSUPPORTED, error=f"unknown action {command.action!r}"
            )
        return CommandResult(command.id, result.status, result.data, result.error)
