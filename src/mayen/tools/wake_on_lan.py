"""Wake-on-LAN (§9.2, GERİ_ALINAMAZ — fiziksel etki, onay ister).

Hedefler yapılandırmadaki ad → MAC listesinden gelir (§19.9); tool ham MAC adresi kabul
etmez. Sebep yetki, gramer değil: modelin söyleyebildiği bir MAC, listenin dışındaki bir
cihazı uyandırabilirdi.

Sihirli paket UDP yayınıdır; gönderim "uyandı" demek değil, "paket yollandı" demektir —
konuşulan cümle de o yüzden bunu söylüyor. Doğrulama için ikinci bir kanal yok.
"""

import asyncio
import socket
from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text

_PORT = 9
_BROADCAST = "255.255.255.255"


def _magic_packet(mac: str) -> bytes:
    address = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    return b"\xff" * 6 + address * 16


def _send(payload: bytes) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, (_BROADCAST, _PORT))


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    name = text(arguments, "target")
    mac = context.config.wol_targets.get(name)
    if mac is None:
        known = ", ".join(sorted(context.config.wol_targets)) or "yok"
        return ToolResult(ok=False, error=f"{name}: tanımlı hedef değil. Tanımlılar: {known}")
    try:
        await asyncio.to_thread(_send, _magic_packet(mac))
    except OSError as exc:
        return ToolResult(ok=False, error=f"{name}: sihirli paket gönderilemedi: {exc}")
    return ToolResult(ok=True, data={"target": name}, speech=f"Wake-up packet sent to {name}.")


TOOL = Tool(
    name="wake_on_lan",
    description="Yapılandırmada tanımlı bir cihaza uyandırma paketi gönderir.",
    effect=Effect.GERI_ALINAMAZ,
    confirm="Send a wake signal to {target}?",
    timeout_seconds=5.0,
    handler=_run,
    args=(Arg("target", ArgType.STRING, "Cihazın yapılandırmadaki adı"),),
)
