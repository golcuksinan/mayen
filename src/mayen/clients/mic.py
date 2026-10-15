"""Mikrofon istemcisi: sesli kanala (§13) mikrofonu sürekli akıtır, gelen sesi çalar.

Ses ham PCM'dir (§16.9 açık; biçim `ports.channels`'ta). Kimliğini beyan etmez; çekirdek
bağlantının hangi cihazdan geldiğini taşımadan okur (§10.1). Yankı giderme yapmaz (§6): ya
kulaklıkla ya da sistemin yankı gidericisinden geçen bir mikrofonla kullanılır, yoksa Mayen
kendi sesini duyar. Bozuk bir mesaj istemciyi öldürmez (§13).

Çıkışta (Ctrl+C) taşınan bayt sayısını ve ortalama bant genişliğini yazar.
"""

import argparse
import asyncio
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import sounddevice as sd  # type: ignore[import-untyped]  # tip bilgisi yok
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException

from mayen.ports.channels import VoiceHello

DEFAULT_URL = "ws://127.0.0.1:8765/voice"

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


async def _receive(ws: ClientConnection, playback: Playback, traffic: Traffic) -> None:
    async for message in ws:
        if isinstance(message, str) or len(message) % 2:
            print(f"[dropped a message that is not PCM: {message!r:.40}]", file=sys.stderr)
            continue
        traffic.received += len(message)
        playback.add(message)


async def run(url: str, traffic: Traffic) -> None:
    loop = asyncio.get_running_loop()
    microphone: asyncio.Queue[bytes] = asyncio.Queue()

    def captured(data: Any, _frames: int, _time: Any, _status: Any) -> None:  # noqa: ANN401
        loop.call_soon_threadsafe(microphone.put_nowait, bytes(data))

    async with connect(url) as ws:
        hello = VoiceHello.decode(await ws.recv())
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
        receiving = asyncio.create_task(_receive(ws, playback, traffic))
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
    args = parser.parse_args(argv)
    traffic = Traffic()
    code = 0
    try:
        asyncio.run(run(args.url, traffic))
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, WebSocketException, sd.PortAudioError) as e:
        print(f"[{e}]", file=sys.stderr)
        code = 1
    print(traffic.report(), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
