"""Yazılı kanalın sözleşmesi (§7, §13): istemciyle çekirdeğin mesajları ve cihaz kimliği.

İstemciler ayrı süreçlerdir ve yalnızca `ports`'u görür (§4); mesaj biçimi bu yüzden burada
durur, çekirdeğin serileştiricisi de istemci de aynı tanımı kullanır.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from mayen.ports.people import DeviceId


class MessageKind(StrEnum):
    TEXT = "text"  # istemciden: yazılı komut; çekirdekten: cevabın bir parçası
    RESPONSE_END = "response_end"  # çekirdekten: cevap bitti


@dataclass(frozen=True)
class WireMessage:
    kind: MessageKind
    text: str = ""

    def encode(self) -> str:
        return json.dumps({"type": self.kind.value, "text": self.text}, ensure_ascii=False)

    @classmethod
    def decode(cls, raw: str | bytes) -> "WireMessage":
        """Bozuk mesaj `ValueError`'dur; bağlantıyı kapatmaz, hata olarak bildirilir (§13)."""
        try:
            data = json.loads(raw)
            return cls(MessageKind(data["type"]), str(data.get("text", "")))
        except (TypeError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"malformed message: {e}") from e


class DeviceIdentity(Protocol):
    async def device(self, address: str) -> DeviceId | None:
        """Bu adresten gelen bağlantının taşımanın doğruladığı cihazı; doğrulanamazsa `None`
        (§10.1: doğrulanmamış bağlantı ortak cihazdır)."""
        ...
