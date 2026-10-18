"""Masaüstünde çalışan eylemler (§9.7): çekirdeğin komutunu bu makinede yürütür.

Bir yetenek ancak cihazda çalışıyorsa bildirilir: aracı bulunmayan yetenek beyan edilmez.
Komutlar argv dizisidir, tek dize değil (§9.4); model değeri yalnızca doğrulanmış argümanda,
argv'nin ayrı bir öğesi olarak durur.

Hoparlör, varsayılan çıkış cihazıdır; `pactl` ile (PipeWire'da da çalışır). Medya, MPRIS
arayüzünü sunan oynatıcılardır; `busctl` ile oturum veri yolundan. Okumalar JSON çıktısından
yapılır: düz metin çıktısı yerel ayara göre değişir.

Uygulamalar, çekirdeğin gönderdiği `.desktop` kimliğiyle, sistemin kendi tanımından
`gtk-launch` ile açılır; tablo çekirdeğin config'indedir (§9.4).

`ok`, etkinin görüldüğünü kanıtlar (§9.1): eylemden sonra durum yeniden okunur ve `ok` yalnızca
etki orada görülürse döner. Süresi içinde görülmezse sonuç `error`dur ve okunan durumu taşır.

Pencereler KWin'in betik arayüzüyle yönetilir: Wayland pencere listesini istemcilere vermez,
KDE'de onu veren tek yol pencere yöneticisinin kendisidir. Betikler koddaki bir tablodadır
(§9.4); betiğin çıktısı oturum günlüğünden, her çalıştırmaya özel bir işaretle okunur.
"""

import asyncio
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

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

# Etkinin görünmesi için beklenen en uzun süre; tool'un süresine (5 sn) sığar. Ölçülen: ses
# ~15 ms, MPRIS durumu ~20 ms, pencere kapanması ~30 ms, YouTube'da sonraki şarkı 1,5 sn.
# Etki gelince hemen dönülür; sınıra yalnızca etki hiç gelmezse varılır.
EFFECT_WAIT_S = 3.0
_POLL_S = 0.05


async def until[T](
    read: Callable[[], Awaitable[T]], seen: Callable[[T], bool], wait_s: float
) -> T:
    """Durumu, etki görülene ya da süre dolana kadar okur; son okunanı döner."""
    deadline = time.monotonic() + wait_s
    while True:
        value = await read()
        if seen(value) or time.monotonic() >= deadline:
            return value
        await asyncio.sleep(_POLL_S)


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
    def __init__(self, run: Run = run_argv, wait_s: float = EFFECT_WAIT_S) -> None:
        self._run = run
        self._wait_s = wait_s

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
            sink = await until(self._default, lambda s: _level(s) == level, self._wait_s)
            after = _level(sink)
            # Önceki seviye geri alma içindir (§9.6); yalnızca eylem anında bilinir.
            volume = {"level": after, "previous": before}
            if after != level:
                return CommandResult("", Status.ERROR, volume, f"the volume stayed at {after}%")
            return CommandResult("", Status.OK, volume)
        if action == "set_muted":
            muted = bool(args["muted"])
            before = bool((await self._default())["mute"])
            await self._run(["pactl", "set-sink-mute", DEFAULT_SINK, "1" if muted else "0"])
            sink = await until(self._default, lambda s: bool(s["mute"]) is muted, self._wait_s)
            mute = {"muted": bool(sink["mute"]), "previous": before}
            if mute["muted"] is not muted:
                return CommandResult("", Status.ERROR, mute, "the mute did not change")
            return CommandResult("", Status.OK, mute)
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
            now, _ = await until(self._sinks, lambda d: d[0] == output, self._wait_s)
            moved = {"output": now, "previous": default}
            if now != output:
                return CommandResult("", Status.ERROR, moved, "the output did not change")
            return CommandResult("", Status.OK, moved)
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


@dataclass(frozen=True)
class _PlayerState:
    status: str
    title: str | None
    position: int | None


MEDIA_UNSEEN = {
    "play": "the player is not playing",
    "pause": "the player is still playing",
    "toggle": "the player did not change",
    "next": "the track did not change",
    "previous": "the track did not change",
}


def _played(action: str, before: _PlayerState, now: _PlayerState) -> bool:
    """Eylemin etkisi oynatıcının durumunda görülüyor mu."""
    if action == "play":
        return now.status == "playing"
    if action == "pause":
        return now.status != "playing"
    if action == "toggle":
        return now.status != before.status
    rewound = (
        action == "previous"
        and now.position is not None
        and before.position is not None
        and now.position < before.position
    )
    return now.title != before.title or rewound


class Media:
    """Oynatıcı verilmezse çalan; çalan yoksa tek olan. Birden çoğu çalmıyorsa seçmez:
    rastgele bir seçim, kişinin istemediği oynatıcıyı çalıştırabilirdi."""

    def __init__(self, run: Run = run_argv, wait_s: float = EFFECT_WAIT_S) -> None:
        self._run = run
        self._wait_s = wait_s

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
        before = await self._state(bus, action)
        await self._run(["busctl", "--user", "call", bus, MPRIS_PATH, PLAYER, method])
        after = await until(
            lambda: self._state(bus, action),
            lambda now: _played(action, before, now),
            self._wait_s,
        )
        data = {"player": player["name"], "id": player["id"], **await self._track(bus)}
        if not _played(action, before, after):
            return CommandResult("", Status.ERROR, data, MEDIA_UNSEEN[action])
        return CommandResult("", Status.OK, data)

    async def _state(self, bus: str, action: str) -> _PlayerState:
        status = str(await self._property(bus, PLAYER, "PlaybackStatus")).lower()
        title = (await self._track(bus)).get("title")
        position = None
        if action == "previous":
            # Çoğu oynatıcı şarkının başındaysa öncekine, değilse başa döner.
            try:
                position = int(await self._property(bus, PLAYER, "Position"))
            except (CommandError, KeyError, ValueError, TypeError):
                position = None  # oynatıcı konumu bildirmiyor
        return _PlayerState(status, title, position)


class Apps:
    """Çekirdeğin gönderdiği `.desktop` kimliğini açar; tablo çekirdeğin config'indedir ve
    ad katalogda seçenektir (§9.1). Kimlik tireyle başlayamaz: başlatıcının seçeneği olurdu.

    Açmanın görülen etkisi sürecin başlamasıdır (§9.1): `gtk-launch` uygulamanın komutunu
    çalıştıramazsa hata verir. Pencere beklenmez: bir oyunun penceresi onlarca saniye sürebilir
    (ölçülen, Steam kapalıyken CS2: 14 sn), önce başka bir uygulamanın penceresi gelebilir
    (Steam'in girişi) ve pencerenin sınıfı uygulamanın başlatma ayarına göre değişir."""

    def __init__(
        self,
        spawn: Spawn = spawn_argv,
        categories: Callable[[str], list[str]] | None = None,
    ) -> None:
        self._spawn = spawn
        self._categories = categories or desktop_categories

    def available(self) -> bool:
        return shutil.which("gtk-launch") is not None

    async def handle(self, action: str, args: Mapping[str, Any]) -> CommandResult | None:
        if action != "open":
            return None
        entry = str(args["entry"])
        if not entry or entry.startswith("-"):
            return CommandResult("", Status.ERROR, error=f"{entry!r} is not a desktop entry id")
        await self._spawn(["gtk-launch", entry])
        # Kategoriler sistemin kendi tanımından (§7: oyun yerleşimi açılan uygulamanın türüne
        # göre); tablo yalnızca adı kimliğe bağlar.
        data = {"opened": str(args.get("app", entry)), "categories": self._categories(entry)}
        return CommandResult("", Status.OK, data)


def application_dirs() -> list[Path]:
    """`.desktop` dosyalarının arandığı yerler, öncelik sırasıyla (XDG Base Directory)."""
    home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    data = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    return [Path(d) / "applications" for d in [home, *data.split(":")] if d]


def desktop_categories(entry: str, dirs: list[Path] | None = None) -> list[str]:
    """Uygulamanın freedesktop kategorileri (`Categories=`), ilk bulunan tanımdan; bulunmazsa
    boş: türü bilinmeyen uygulama hiçbir yerleşimi tetiklemez."""
    for directory in application_dirs() if dirs is None else dirs:
        path = directory / f"{entry}.desktop"
        if not path.is_file():
            continue
        group = None
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("["):
                group = line
            elif group == "[Desktop Entry]" and line.startswith("Categories="):
                return [c for c in line.removeprefix("Categories=").split(";") if c]
        return []
    return []


KWIN = "org.kde.KWin"
SCRIPTING = "org.kde.kwin.Scripting"
KWIN_UUID = re.compile(r"\{[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\}")
JOURNAL_WAIT_S = 2.0

# Betik başına iki sabit eklenir: `MARK` (çıktının işareti) ve `ID` (pencerenin KWin kimliği).
# İkisi de JSON değeri olarak girer, kod olarak değil; kimlik ayrıca biçiminden doğrulanır.
_FIND = "const w = workspace.windowList().find(w => w.internalId.toString() === ID);\n"
_FOUND = "{found: !!w, title: w ? w.caption : null, app: w ? w.resourceClass : null}"
WINDOW_SCRIPTS = {
    "list": "print(MARK + JSON.stringify(workspace.windowList()"
    ".filter(w => w.normalWindow && !w.skipTaskbar).map(w => ({id: w.internalId.toString(), "
    "title: w.caption, app: w.resourceClass, active: w === workspace.activeWindow, "
    "minimized: w.minimized}))));",
    "focus": _FIND + f"const r = {_FOUND};\n"
    "if (w) { w.minimized = false; workspace.activeWindow = w; }\n"
    "print(MARK + JSON.stringify(r));",
    "minimize": _FIND + f"const r = {_FOUND};\nif (w) {{ w.minimized = true; }}\n"
    "print(MARK + JSON.stringify(r));",
    "close": _FIND + f"const r = {_FOUND};\nif (w) {{ w.closeWindow(); }}\n"
    "print(MARK + JSON.stringify(r));",
}


type Script = Callable[[str, str], Awaitable[Any]]


async def kwin_script(action: str, window: str, run: Run = run_argv) -> Any:  # noqa: ANN401
    """Tablodaki betiği KWin'e yükler, çalıştırır ve çıktısını günlükten okur."""
    mark = f"MAYEN-{uuid.uuid4().hex}:"
    source = f"const MARK = {json.dumps(mark)};\nconst ID = {json.dumps(window)};\n"
    source += WINDOW_SCRIPTS[action]
    since = int(time.time()) - 1
    name = mark.removesuffix(":").lower()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".js", dir=os.environ.get("XDG_RUNTIME_DIR")
    ) as f:
        f.write(source)
        f.flush()
        loaded = await run(
            [
                "busctl",
                "--user",
                "--json=short",
                "call",
                KWIN,
                "/Scripting",
                SCRIPTING,
                "loadScript",
                "ss",
                f.name,
                name,
            ]
        )
        number = json.loads(loaded)["data"][0]
        try:
            await run(
                [
                    "busctl",
                    "--user",
                    "call",
                    KWIN,
                    f"/Scripting/Script{number}",
                    "org.kde.kwin.Script",
                    "run",
                ]
            )
            return await _journal(mark, since, run)
        finally:
            await run(
                [
                    "busctl",
                    "--user",
                    "call",
                    KWIN,
                    "/Scripting",
                    SCRIPTING,
                    "unloadScript",
                    "s",
                    name,
                ]
            )


async def _journal(mark: str, since: int, run: Run) -> Any:  # noqa: ANN401
    deadline = time.monotonic() + JOURNAL_WAIT_S
    while True:
        try:
            out = await run(
                [
                    "journalctl",
                    "--user",
                    "-o",
                    "cat",
                    "-q",
                    "--no-pager",
                    f"--since=@{since}",
                    f"--grep={mark}",
                ]
            )
        except CommandError:
            out = ""  # eşleşme yokken çıkış kodu sıfır değildir
        for line in out.splitlines():
            if mark in line:
                return json.loads(line.split(mark, 1)[1])
        if time.monotonic() > deadline:
            raise CommandError("the window manager did not answer")
        await asyncio.sleep(0.1)


class Windows:
    """Pencereye numara verir; numara pencere açık kaldıkça aynıdır ve başka pencereye geçmez.
    Böylece eski bir listedeki numara, sonradan açılmış başka bir pencereye dokunamaz; kısa
    olduğu için de onay cümlesinde aynen okunabilir (§10.5)."""

    def __init__(self, script: Script = kwin_script, wait_s: float = EFFECT_WAIT_S) -> None:
        self._script = script
        self._wait_s = wait_s
        self._numbers: dict[str, int] = {}
        self._next = 1

    def available(self) -> bool:
        tools = ("busctl", "journalctl")
        kwin = shutil.which("kwin_wayland") or shutil.which("kwin_x11")
        return bool(kwin) and all(shutil.which(t) for t in tools)

    def _number(self, kwin_id: str) -> int:
        if kwin_id not in self._numbers:
            self._numbers[kwin_id] = self._next
            self._next += 1
        return self._numbers[kwin_id]

    async def _list(self) -> list[dict[str, Any]]:
        windows = await self._script("list", "")
        open_now = {w["id"] for w in windows}
        self._numbers = {k: n for k, n in self._numbers.items() if k in open_now}
        listed = [{"window": self._number(w.pop("id")), **w} for w in windows]
        return sorted(listed, key=_by_number)

    async def handle(self, action: str, args: Mapping[str, Any]) -> CommandResult | None:
        if action not in WINDOW_SCRIPTS:
            return None
        if action == "list":
            return CommandResult("", Status.OK, {"windows": await self._list()})
        number = args.get("window")
        kwin_id = next((k for k, n in self._numbers.items() if n == number), None)
        found = None
        if action == "close" and kwin_id is not None:
            # Kapatma geri alınamaz: numara, onaylanan uygulamanın penceresi değilse dokunulmaz.
            app = next((w["app"] for w in await self._list() if w["window"] == number), None)
            if app != args.get("app"):
                kwin_id = None
        if kwin_id is not None:
            if not KWIN_UUID.fullmatch(kwin_id):
                raise CommandError(f"unexpected window id {kwin_id!r}")
            found = await self._script(action, kwin_id)
        if found is None or not found["found"]:
            # Liste hatayla döner (medyadaki gibi): model numarayı bir sonraki adımda seçer,
            # kişiye "listeleyeyim mi" diye sormaz.
            error = "no window number given" if number is None else f"no open window {number}"
            windows = await self._list()
            return CommandResult("", Status.ERROR, {"windows": windows}, f"{error}; pick one")
        data = {"window": number, "title": found["title"], "app": found["app"]}
        assert kwin_id is not None  # bulunan pencerenin kimliği vardır
        windows = await until(
            lambda: self._script("list", ""),
            lambda now: _arranged(action, kwin_id, now),
            self._wait_s,
        )
        if not _arranged(action, kwin_id, windows):
            return CommandResult("", Status.ERROR, data, WINDOW_UNSEEN[action])
        return CommandResult("", Status.OK, data)


WINDOW_UNSEEN = {
    "focus": "the window did not come to the front",
    "minimize": "the window was not minimized",
    "close": "the window is still open; it may be asking something, such as to save",
}


def _arranged(action: str, kwin_id: str, windows: list[dict[str, Any]]) -> bool:
    """Eylemin etkisi pencere listesinde görülüyor mu."""
    window = next((w for w in windows if w["id"] == kwin_id), None)
    if action == "close":
        return window is None
    if window is None:
        return False
    if action == "minimize":
        return bool(window["minimized"])
    return bool(window["active"]) and not window["minimized"]


def _by_number(window: Mapping[str, Any]) -> int:
    return int(window["window"])


class Desktop:
    """Bu makinenin yürütücüleri; yetenek, yürütücüsü çalışabiliyorsa bildirilir."""

    def __init__(self, executors: Mapping[Capability, Executor] | None = None) -> None:
        default: dict[Capability, Executor] = {
            Capability.SPEAKER: Speaker(),
            Capability.MEDIA: Media(),
            Capability.APPS: Apps(),
            Capability.WINDOWS: Windows(),
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
