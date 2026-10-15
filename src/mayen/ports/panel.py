"""Panelin sözleşmesi (§14): çekirdekten panele giden mesajlar.

Panel ayrı bir süreçtir ve Python import etmez; bu tanımı kendi dilinde aynen kurar ve
`schema_version`'ı tutmayan mesajı göstermez. Panel salt okunurdur: çekirdeğe mesaj göndermez.

Bağlanınca önce istenen andan bu yana kayıtlar zaman sırasıyla gelir, sonra `live`, ondan
sonra kayda girdikçe canlı kayıtlar. Durum ayrıca çıkarılmaz; `state.changed` olayıdır (§5.4).
"""

import json
from enum import StrEnum
from typing import Any

from mayen.ports.events import Event, stamp
from mayen.ports.transcript import Utterance

SCHEMA_VERSION = 1


class PanelMessageKind(StrEnum):
    EVENT = "event"  # olay kaydının bir satırı (§5.5)
    UTTERANCE = "utterance"  # transkriptin bir sözü (§11)
    LIVE = "live"  # geçmiş bitti; bundan sonrası canlı


def _encode(kind: PanelMessageKind, fields: dict[str, Any]) -> str:
    message = {"schema_version": SCHEMA_VERSION, "type": kind.value, **fields}
    return json.dumps(message, ensure_ascii=False, allow_nan=False)


def encode_event(event: Event) -> str:
    h = event.header
    return _encode(
        PanelMessageKind.EVENT,
        {
            "id": str(h.id),
            "kind": h.kind.value,
            "source": h.source,
            "time": stamp(h.time),
            "session": h.session,
            "turn_id": None if h.turn_id is None else str(h.turn_id),
            "duration_s": h.duration_s,
            "status": None if h.status is None else h.status.value,
            "related": list(h.related),
            "body": dict(event.body),
        },
    )


def encode_utterance(utterance: Utterance) -> str:
    u = utterance
    return _encode(
        PanelMessageKind.UTTERANCE,
        {
            "id": str(u.id),
            "time": stamp(u.time),
            "session": u.session,
            "turn_id": None if u.turn_id is None else str(u.turn_id),
            "party": u.party.value,
            "role": None if u.role is None else u.role.value,
            "person_id": u.person_id,
            "text": u.text,
            "interrupted": u.interrupted,
        },
    )


def encode_live() -> str:
    return _encode(PanelMessageKind.LIVE, {})
