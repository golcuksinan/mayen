"""Turların zaman çizelgesi (`mayen-turns`): panel mesajlarının okunması ve satırlar."""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from mayen.clients.turns import OUTSIDE, Timeline, since_of
from mayen.ports.events import Event, EventId, EventKind, Header
from mayen.ports.panel import decode, encode_event, encode_live, encode_utterance
from mayen.ports.tools import Role, Status
from mayen.ports.transcript import Party, Utterance, UtteranceId
from mayen.ports.triggers import TurnId

T0 = datetime(2026, 10, 17, 12, 8, 31, tzinfo=UTC)
TURN = TurnId(uuid4())


def event(
    kind: EventKind,
    seconds: float,
    body: dict[str, object],
    status: Status | None = None,
    related: tuple[str, ...] = (),
) -> Event:
    at = T0 + timedelta(seconds=seconds)
    return Event(
        Header(EventId(uuid4()), kind, "test", at, "s", TURN, None, status, related), body
    )


def said(
    seconds: float, text: str, *, turn: bool = True, party: Party = Party.PERSON
) -> Utterance:
    person = party is Party.PERSON
    return Utterance(
        UtteranceId(uuid4()),
        T0 + timedelta(seconds=seconds),
        "s",
        TURN if turn else None,
        party,
        Role.OWNER if person else None,
        "1" if person else None,
        text,
    )


def test_panel_messages_round_trip() -> None:
    utterance = said(1, "Hey Mayen")
    assert decode(encode_utterance(utterance)) == utterance
    stt = event(EventKind.STT_SEGMENT, 1, {"speaker_score": 0.75}, status=Status.OK)
    assert decode(encode_event(stt)) == stt
    assert decode(encode_live()) is None
    with pytest.raises(ValueError):
        decode('{"schema_version": 99, "type": "live"}')


def test_a_turn_reads_as_who_said_what_and_what_the_tool_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    request = said(2, "Sesi yüzde otuza indir")
    lines = list(
        Timeline().lines(
            [
                event(
                    EventKind.TURN_STARTED, 0, {"source": "voice", "capabilities": ["speaker"]}
                ),
                request,
                # Puan sözün STT olayında, söz ile aynı anda ya da sonra gelir.
                event(
                    EventKind.STT_SEGMENT,
                    2.1,
                    {"speaker_score": 0.45, "muted": False},
                    related=(f"utterance:{request.id}",),
                ),
                event(EventKind.TOOL_REQUESTED, 3, {"call_id": "c", "verdict": "deny"}),
                event(
                    EventKind.TOOL_FINISHED,
                    3,
                    {
                        "tool": "volume",
                        "call_id": "c",
                        "arguments": {"level": 30},
                        "result": {
                            "status": "denied",
                            "data": {},
                            "error": "role not permitted",
                        },
                    },
                ),
                said(5, "I cannot.", party=Party.ASSISTANT),
                event(
                    EventKind.TURN_FINISHED,
                    6,
                    {"requester": {"role": "unknown", "person_id": None}},
                ),
                said(9, "Hey mayın.", turn=False),
            ]
        )
    )
    monkeypatch.undo()
    time.tzset()
    assert lines == [
        "12:08:31 turn · voice · s · device: speaker",
        "  12:08:33 owner#1 0.45  Sesi yüzde otuza indir",
        '  12:08:34 volume {"level": 30} [deny] → denied — role not permitted',
        "  12:08:36 Mayen  I cannot.",
        "12:08:37 turn finished · requester: unknown",
        f"{OUTSIDE}12:08:40 owner#1  Hey mayın.",
    ]


def test_since_is_today_local_time_or_an_iso_moment() -> None:
    now = datetime(2026, 10, 17, 12, 30, tzinfo=UTC)
    assert since_of(None, now) == now - timedelta(hours=1)
    assert since_of("2026-10-17T10:00:00+00:00", now) == datetime(2026, 10, 17, 10, tzinfo=UTC)
    local = since_of("09:15", now).astimezone()
    assert (local.hour, local.minute) == (9, 15)


def test_forgotten_records_read_as_marked_and_the_decision_has_a_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Unutulan kayıt panelde olduğu gibi işaretli görünür (§11.4); içeriği silinmez.
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    aside = said(0, "birine söylenen", turn=False)
    asked = said(2, "İzmir'de hava nasıl?")
    decision = event(
        EventKind.RECORD_FORGOTTEN,
        5,
        {"turns": 1, "utterances": 1},
        related=(f"turn:{TURN}", f"utterance:{aside.id}"),
    )
    lines = list(
        Timeline().lines(
            [aside, event(EventKind.TURN_STARTED, 1, {"source": "voice"}), asked, decision]
        )
    )
    assert lines[0] == f"{OUTSIDE}12:08:31 owner#1 (forgotten)  birine söylenen"
    assert lines[1].endswith("(forgotten)")
    assert lines[2] == "  12:08:33 owner#1 (forgotten)  İzmir'de hava nasıl?"
    assert lines[3] == "  12:08:36 forgotten: 2 record(s)"


def test_a_deletion_reads_as_one_line() -> None:
    decision = event(EventKind.RECORD_DELETED, 5, {"turns": 1}, related=(f"turn:{TURN}",))
    [line] = Timeline().lines([decision])
    assert line.endswith("deleted: 1 record(s)")
