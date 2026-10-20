"""İstemcinin ekranı için mesajlar (§7): oturumun durumu, sözler ve tool sonuçları.

Sesli bağlantıda sesin yanında JSON metin olarak gider; ekran yalnızca bunlardan çizilir,
model ekrana yazmaz. Tool sonucu, yetki süzgecinden geçmiş hâlidir: modelin görmediği bir
kayıt ekranda da görünmez. Arayüz ayrı bir süreçtir ve Python import etmez; bu tanımı kendi
dilinde aynen kurar ve `schema_version`'ı tutmayan mesajı göstermez.
"""

import dataclasses
import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from mayen.ports.events import FaultPart, SessionState, stamp
from mayen.ports.speech import untagged
from mayen.ports.timers import Timer
from mayen.ports.tools import ToolResult
from mayen.ports.transcript import Utterance

SCHEMA_VERSION = 1


class ScreenKind(StrEnum):
    STATE = "state"  # oturumun durumu değişti (§5.4)
    UTTERANCE = "utterance"  # oturumda bir söz: kişinin ya da Mayen'in (§11)
    TOOL = "tool"  # bir tool çağrısının sonucu, modelin gördüğü hâliyle
    REMINDER = "reminder"  # çalan hatırlatma: turu açan zamanlayıcının kaydı (§12)
    FAULT = "fault"  # sistemin bir parçası bozuldu (§5.4 hata kanalı); tool sonucu değil


def _encode(kind: ScreenKind, fields: Mapping[str, Any]) -> str:
    message = {"schema_version": SCHEMA_VERSION, "type": kind.value, **fields}
    return json.dumps(message, ensure_ascii=False, allow_nan=False)


def encode_state(state: SessionState) -> str:
    return _encode(ScreenKind.STATE, {"state": state.value})


def encode_utterance(utterance: Utterance) -> str:
    u = utterance
    return _encode(
        ScreenKind.UTTERANCE,
        {
            "time": stamp(u.time),
            "party": u.party.value,
            "role": None if u.role is None else u.role.value,
            "text": untagged(u.text),
            "interrupted": u.interrupted,
        },
    )


def encode_reminder(timer: Timer) -> str:
    """Kişinin kendi sözleri ve vadesi; Mayen'in onu nasıl söylediği değil (model yazmaz)."""
    return _encode(
        ScreenKind.REMINDER,
        {"text": timer.text, "due": stamp(timer.due), "priority": timer.priority.value},
    )


def encode_fault(part: FaultPart, detail: str) -> str:
    """Bozulan parça ve hatanın kendi metni. Tool'un `error` durumundan ayrıdır: o, isteğin
    yerine getirilemediğidir; bu, sistemin bir parçasının çalışmadığı."""
    return _encode(ScreenKind.FAULT, {"part": part.value, "detail": detail})


def encode_tool(tool: str, arguments: Mapping[str, Any], result: ToolResult) -> str:
    return _encode(
        ScreenKind.TOOL,
        {"tool": tool, "arguments": dict(arguments), **dataclasses.asdict(result)},
    )


def screen_message(raw: str | bytes) -> dict[str, Any] | None:
    """Ekran mesajıysa içeriği; değilse (cihaz komutu gibi) `None`."""
    try:
        message = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(message, dict) or message.get("type") not in set(ScreenKind):
        return None
    return message
