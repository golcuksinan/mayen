"""Cihazda çalışan eylemlerin sözleşmesi (§9.7): yetenek beyanı, komut ve sonucu.

Mesajlar sesli kanalın bağlantısında, sesin yanında JSON metin olarak gider (§13). İstemci
selamı aldıktan sonra bir kez yeteneklerini bildirir; çekirdek komutu gönderir, istemci
sonucu aynı `id` ile döner. İstemciler yalnızca `ports`'u görür (§4); biçim bu yüzden burada
durur.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from mayen.ports.tools import Status, ToolResult


class Capability(StrEnum):
    """Bir istemcinin yapabildiği iş alanı; tool adı değil, birden çok tool'u kapsar."""

    SPEAKER = "speaker"


class MessageType(StrEnum):
    CAPABILITIES = "capabilities"  # istemciden, bağlanınca bir kez
    COMMAND = "command"  # çekirdekten
    COMMAND_RESULT = "command_result"  # istemciden


def _load(raw: str | bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed message: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("malformed message: not an object")
    return data


@dataclass(frozen=True)
class Capabilities:
    names: frozenset[Capability]

    def encode(self) -> str:
        return json.dumps(
            {"type": MessageType.CAPABILITIES.value, "capabilities": sorted(self.names)}
        )


@dataclass(frozen=True)
class Command:
    id: str
    capability: Capability
    action: str
    args: Mapping[str, Any] = field(default_factory=dict)

    def encode(self) -> str:
        return json.dumps(
            {
                "type": MessageType.COMMAND.value,
                "id": self.id,
                "capability": self.capability.value,
                "action": self.action,
                "args": dict(self.args),
            },
            ensure_ascii=False,
        )

    @classmethod
    def decode(cls, raw: str | bytes) -> "Command":
        """Bozuk komut `ValueError`'dur; istemciyi öldürmez (§13)."""
        data = _load(raw)
        try:
            if data["type"] != MessageType.COMMAND:
                raise ValueError(f"not a command: {data['type']!r}")
            args = data.get("args", {})
            if not isinstance(args, dict):
                raise ValueError("args is not an object")
            return cls(
                str(data["id"]), Capability(data["capability"]), str(data["action"]), args
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"malformed command: {e}") from e


@dataclass(frozen=True)
class CommandResult:
    id: str
    status: Status
    data: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None

    def encode(self) -> str:
        body: dict[str, Any] = {
            "type": MessageType.COMMAND_RESULT.value,
            "id": self.id,
            "status": self.status.value,
            "data": dict(self.data),
        }
        if self.error is not None:
            body["error"] = self.error
        return json.dumps(body, ensure_ascii=False)

    def result(self) -> ToolResult:
        return ToolResult(self.status, self.data, error=self.error)


def decode_client(raw: str | bytes) -> Capabilities | CommandResult:
    """İstemciden gelen metin mesajı. Bozuksa `ValueError`; bağlantı kapanmaz (§13).

    Bilinmeyen bir yetenek adı atılır: ad bağlam bloğuna girer (§9.7) ve istemcinin yazdığı
    serbest bir metin orada modele talimat gibi okunabilirdi.
    """
    data = _load(raw)
    try:
        kind = MessageType(data["type"])
        if kind is MessageType.CAPABILITIES:
            names = data["capabilities"]
            if not isinstance(names, list):
                raise ValueError("capabilities is not a list")
            known = {c.value for c in Capability}
            return Capabilities(frozenset(Capability(n) for n in names if n in known))
        if kind is MessageType.COMMAND_RESULT:
            body = data.get("data", {})
            if not isinstance(body, dict):
                raise ValueError("data is not an object")
            error = data.get("error")
            return CommandResult(
                str(data["id"]),
                Status(data["status"]),
                body,
                None if error is None else str(error),
            )
        raise ValueError(f"not a client message: {kind.value!r}")
    except (KeyError, TypeError) as e:
        raise ValueError(f"malformed message: {e}") from e


class DeviceControl(Protocol):
    """Oturumun cihazındaki istemciye giden yol; skill *ne* istendiğini bilir (§9.5)."""

    @property
    def capabilities(self) -> frozenset[Capability]: ...

    async def run(
        self, capability: Capability, action: str, args: Mapping[str, Any]
    ) -> ToolResult:
        """Yetenek cihazda yoksa komut gitmeden `unsupported` döner (§9.7)."""
        ...
