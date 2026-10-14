"""Terminal istemcisi: yazılı kanala (§7) satır satır yazar, cevabı geldikçe basar.

Kimliğini beyan etmez; çekirdek bağlantının hangi cihazdan geldiğini taşımadan okur (§10.1).
Tailscale'den geçmeyen bir bağlantı ortak cihazdır. Bozuk bir mesaj istemciyi öldürmez (§13).
"""

import argparse
import asyncio
import sys

from websockets.asyncio.client import ClientConnection, connect

from mayen.ports.channels import MessageKind, WireMessage

DEFAULT_URL = "ws://127.0.0.1:8765/text"


async def _print_replies(ws: ClientConnection) -> None:
    async for raw in ws:
        try:
            message = WireMessage.decode(raw)
        except ValueError as e:
            print(f"[{e}]", file=sys.stderr)
            continue
        if message.kind is MessageKind.TEXT:
            sys.stdout.write(message.text)
        elif message.kind is MessageKind.RESPONSE_END:
            sys.stdout.write("\n")
        sys.stdout.flush()


async def run(url: str) -> None:
    loop = asyncio.get_running_loop()
    async with connect(url) as ws:
        replies = asyncio.create_task(_print_replies(ws))
        try:
            while line := await loop.run_in_executor(None, sys.stdin.readline):
                if text := line.strip():
                    await ws.send(WireMessage(MessageKind.TEXT, text).encode())
        finally:
            replies.cancel()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayen-terminal")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    args = parser.parse_args(argv)
    try:
        asyncio.run(run(args.url))
    except (OSError, KeyboardInterrupt) as e:
        if isinstance(e, OSError):
            print(f"[{e}]", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
