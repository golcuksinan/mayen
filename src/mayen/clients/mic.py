"""Mikrofon istemcisi: sesli kanala (§13) mikrofonu sürekli akıtır, gelen sesi çalar.

Ses ham PCM'dir (§16.9 açık; biçim `ports.channels`'ta). Kimliğini beyan etmez; çekirdek
bağlantının hangi cihazdan geldiğini taşımadan okur (§10.1). Yankı giderme yapmaz (§6): ya
kulaklıkla ya da sistemin yankı gidericisinden geçen bir mikrofonla kullanılır, yoksa Mayen
kendi sesini duyar. Bozuk bir mesaj istemciyi öldürmez (§13).

Masaüstü istemcisidir de (§9.7): selamdan sonra bu makinenin yeteneklerini bildirir, çekirdeğin
gönderdiği komutu yürütür ve sonucu aynı bağlantıdan döner.

Çıkışta (Ctrl+C) taşınan bayt sayısını ve ortalama bant genişliğini yazar.
"""

import argparse
import asyncio
import json
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sounddevice as sd  # type: ignore[import-untyped]  # tip bilgisi yok
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException

from mayen.clients.desktop import Desktop, load_apps
from mayen.ports.channels import VoiceHello
from mayen.ports.devices import Capabilities, Command, CommandResult
from mayen.ports.tools import Status

DEFAULT_URL = "ws://127.0.0.1:8765/voice"
# Açılabilecek uygulamaların tablosu bu cihazda durur (§9.4, §9.7): her cihazda başka uygulama
# kuruludur.
DEFAULT_APPS = Path.home() / ".config" / "mayen" / "apps.yaml"

BLOCK_S = 0.02
"""Mikrofondan okunan parça: VAD'ın ve ağın gördüğü en küçük gecikme."""


@dataclass
class Traffic:
    started: float = field(default_factory=time.monotonic)
    sent: int = 0
    received: int = 0

    def report(self) -> str:
        seconds = max(time.monotonic() - self.started, 1e-9)

        def side(n: int) -> str:
            return f"{n / 1e6:.2f} MB ({n * 8 / seconds / 1000:.0f} kbit/s)"

        return f"{seconds:.0f} s: up {side(self.sent)}, down {side(self.received)}"


class Playback:
    """Gelen sesin çalınmayı bekleyen kısmı; ses kartının iş parçacığı buradan çeker."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._lock = threading.Lock()

    def add(self, pcm: bytes) -> None:
        with self._lock:
            self._buffer.extend(pcm)

    def fill(self, out: Any, _frames: int, _time: Any, _status: Any) -> None:  # noqa: ANN401
        need = len(out)
        with self._lock:
            chunk = bytes(self._buffer[:need])
            del self._buffer[:need]
        # Çalacak ses yoksa sessizlik: kart beklemez.
        out[:] = chunk + b"\x00" * (need - len(chunk))


def _dropped(message: str) -> None:
    print(f"[dropped a message that is not PCM: {message!r:.40}]", file=sys.stderr)


async def _receive(
    ws: ClientConnection,
    playback: Playback,
    traffic: Traffic,
    on_text: Callable[[str], None] = _dropped,
) -> None:
    async for message in ws:
        if isinstance(message, str):
            on_text(message)
            continue
        if len(message) % 2:
            _dropped(repr(message))
            continue
        traffic.received += len(message)
        playback.add(message)


async def respond(desktop: Desktop, raw: str) -> str | None:
    """Komutun sonucu; `id`'si okunamayan bozuk mesaja cevap yoktur (§13)."""
    try:
        command = Command.decode(raw)
    except ValueError as e:
        print(f"[dropped a command: {e}]", file=sys.stderr)
        try:
            data = json.loads(raw)
            # Tanınmayan bir yetenek: çekirdek beklemesin, yapılamadığını bilsin.
            return CommandResult(str(data["id"]), Status.UNSUPPORTED, error=str(e)).encode()
        except (ValueError, KeyError, TypeError):
            return None
    return (await desktop.handle(command)).encode()


class Commands:
    """Gelen komutları ayrı görevlerde yürütür: uzun bir komut sesi bekletmez."""

    def __init__(self, ws: ClientConnection, desktop: Desktop) -> None:
        self._ws = ws
        self._desktop = desktop
        self._tasks: set[asyncio.Task[None]] = set()

    def __call__(self, raw: str) -> None:
        task = asyncio.create_task(self._run(raw))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, raw: str) -> None:
        reply = await respond(self._desktop, raw)
        if reply is not None:
            try:
                await self._ws.send(reply)
            except WebSocketException as e:
                print(f"[could not send a command result: {e}]", file=sys.stderr)


async def run(url: str, traffic: Traffic, apps: Path = DEFAULT_APPS) -> None:
    loop = asyncio.get_running_loop()
    microphone: asyncio.Queue[bytes] = asyncio.Queue()

    def captured(data: Any, _frames: int, _time: Any, _status: Any) -> None:  # noqa: ANN401
        loop.call_soon_threadsafe(microphone.put_nowait, bytes(data))

    desktop = Desktop(apps=load_apps(apps))
    async with connect(url) as ws:
        hello = VoiceHello.decode(await ws.recv())
        capabilities = desktop.capabilities()
        await ws.send(Capabilities(capabilities).encode())
        print(f"capabilities: {sorted(capabilities)}", file=sys.stderr)
        playback = Playback()
        source = sd.RawInputStream(
            samplerate=hello.input_sample_rate,
            channels=1,
            dtype="int16",
            blocksize=int(hello.input_sample_rate * BLOCK_S),
            callback=captured,
        )
        sink = sd.RawOutputStream(
            samplerate=hello.output_sample_rate,
            channels=1,
            dtype="int16",
            callback=playback.fill,
        )
        receiving = asyncio.create_task(_receive(ws, playback, traffic, Commands(ws, desktop)))
        traffic.started = time.monotonic()
        print("listening (Ctrl+C to stop)", file=sys.stderr)
        with source, sink:
            try:
                while not receiving.done():
                    pcm = await microphone.get()
                    await ws.send(pcm)
                    traffic.sent += len(pcm)
            finally:
                receiving.cancel()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayen-mic")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    parser.add_argument("--apps", type=Path, default=DEFAULT_APPS, help="app table (YAML)")
    args = parser.parse_args(argv)
    traffic = Traffic()
    code = 0
    try:
        asyncio.run(run(args.url, traffic, args.apps))
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, WebSocketException, sd.PortAudioError) as e:
        print(f"[{e}]", file=sys.stderr)
        code = 1
    print(traffic.report(), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
