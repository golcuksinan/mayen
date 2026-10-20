"""Kanalların sözleşmesi (§7, §13): istemciyle çekirdeğin mesajları ve cihaz kimliği.

Sesli kanal: çekirdek bağlantı açılınca bir JSON selam (`VoiceHello`) yollar; ardından iki
yönde de ikili mesajlar ham PCM'dir (16 bit, tek kanal, little-endian): istemciden
`input_sample_rate`, çekirdekten `output_sample_rate` hızında. Çekirdek sesi çalınma hızında
gönderir; istemci geldikçe çalar. Ses sürekli akar (§6, sürekli STT). Selamdan sonraki metin
mesajları cihaz komutlarıdır (`ports.devices`); istemci ayrıca sesi hangi mikrofondan
aldığını bildirebilir (`AudioInput`), bağlanınca ve değişince.

İstemciler ayrı süreçlerdir ve yalnızca `ports`'u görür (§4); mesaj biçimi bu yüzden burada
durur, çekirdeğin serileştiricisi de istemci de aynı tanımı kullanır.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

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


VOICE_SCHEMA_VERSION = 2  # 2: sesin yanında cihaz komutları (§9.7)


@dataclass(frozen=True)
class VoiceHello:
    input_sample_rate: int
    output_sample_rate: int

    def encode(self) -> str:
        return json.dumps(
            {
                "schema_version": VOICE_SCHEMA_VERSION,
                "input_sample_rate": self.input_sample_rate,
                "output_sample_rate": self.output_sample_rate,
            }
        )

    @classmethod
    def decode(cls, raw: str | bytes) -> "VoiceHello":
        """Başka bir sürüm ya da bozuk selam `ValueError`'dur: istemci çalışmaya başlamaz."""
        try:
            data: Any = json.loads(raw)
            if data["schema_version"] != VOICE_SCHEMA_VERSION:
                raise ValueError(
                    f"schema_version {data['schema_version']!r}, "
                    f"expected {VOICE_SCHEMA_VERSION}"
                )
            return cls(int(data["input_sample_rate"]), int(data["output_sample_rate"]))
        except (TypeError, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"malformed hello: {e}") from e


AUDIO_INPUT = "audio_input"


@dataclass(frozen=True)
class AudioInput:
    """Sesin alındığı mikrofon: türü (`builtin_mic`, `wired_headset`, `bluetooth_headset`...)
    ve aygıtın adı. Yalnızca sözün kaydına yazılır (`SttConfig.record_dir`); modele girmez."""

    source: str
    name: str = ""

    def encode(self) -> str:
        return json.dumps(
            {"type": AUDIO_INPUT, "source": self.source, "name": self.name}, ensure_ascii=False
        )

    @classmethod
    def decode(cls, raw: str | bytes) -> "AudioInput | None":
        """Başka türden bir mesaj `None`; bozuk bir bildirim `ValueError` (§13)."""
        try:
            data: Any = json.loads(raw)
            if not isinstance(data, dict) or data.get("type") != AUDIO_INPUT:
                return None
            return cls(str(data["source"]), str(data.get("name", "")))
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"malformed audio input: {e}") from e


class DeviceIdentity(Protocol):
    async def device(self, address: str) -> DeviceId | None:
        """Bu adresten gelen bağlantının taşımanın doğruladığı cihazı; doğrulanamazsa `None`
        (§10.1: doğrulanmamış bağlantı ortak cihazdır)."""
        ...
