"""Masaüstünde çalışan eylemler (§9.7): çekirdeğin komutunu bu makinede yürütür.

Bir yetenek ancak cihazda çalışıyorsa bildirilir: aracı bulunmayan yetenek beyan edilmez.
Komutlar argv dizisidir, tek dize değil (§9.4); model değeri yalnızca doğrulanmış argümanda,
argv'nin ayrı bir öğesi olarak durur.

Hoparlör, varsayılan çıkış cihazıdır; `pactl` ile (PipeWire'da da çalışır). Okumalar JSON
çıktısından yapılır: düz metin çıktısı yerel ayara göre değişir.
"""

import asyncio
import json
import shutil
from collections.abc import Awaitable, Callable, Mapping
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


class Desktop:
    """Bu makinenin yürütücüleri; yetenek, yürütücüsü çalışabiliyorsa bildirilir."""

    def __init__(self, executors: Mapping[Capability, Executor] | None = None) -> None:
        self._executors = (
            dict(executors) if executors is not None else {Capability.SPEAKER: Speaker()}
        )

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
