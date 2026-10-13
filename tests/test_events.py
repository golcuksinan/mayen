"""Olay zarfı ve ortak saat (§5.5): başlığı çekirdek doldurur, log gövdeyi görmez (§14)."""

import logging
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from mayen.adapters.storage.sqlite import Database, SqliteEventLog
from mayen.core.events import Recorder
from mayen.ports.events import EventKind, parse_stamp, stamp
from mayen.ports.tools import Status
from mayen.ports.triggers import TurnId

T0 = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, start: datetime = T0) -> None:
        self.wall = start
        self.mono = 0.0

    def now(self) -> datetime:
        return self.wall

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds


def test_stamp_is_utc_iso_with_fixed_width() -> None:
    istanbul = timezone(timedelta(hours=3))
    assert (
        stamp(datetime(2026, 10, 13, 15, 0, tzinfo=istanbul)) == "2026-10-13T12:00:00.000000Z"
    )
    assert parse_stamp(stamp(T0)) == T0


def test_stamps_sort_as_text_in_time_order() -> None:
    # Değişken genişlikte "12:00:00Z" ile "12:00:00.5Z" metin olarak ters sıralanırdı.
    moments = [T0, T0 + timedelta(microseconds=500_000), T0 + timedelta(seconds=1)]
    assert sorted(stamp(m) for m in reversed(moments)) == [stamp(m) for m in moments]


def test_naive_datetime_is_refused() -> None:
    with pytest.raises(ValueError, match="naive"):
        stamp(datetime(2026, 10, 13, 12, 0))


def test_recorder_fills_header_and_stores_event(tmp_path: Path) -> None:
    clock = FakeClock()
    turn = TurnId(uuid.uuid4())
    with Database(tmp_path / "m.db") as db:
        log = SqliteEventLog(db)
        recorder = Recorder(log, clock)
        first = recorder.emit(
            EventKind.TOOL_FINISHED,
            "pipeline.tools",
            {"status": "ok"},
            session="s1",
            turn_id=turn,
            duration_s=0.25,
            status=Status.OK,
            related=["note:1"],
        )
        clock.advance(1)
        second = recorder.emit(EventKind.TURN_FINISHED, "pipeline.session", session="s1")

        assert first.header.time == T0
        assert second.header.time == T0 + timedelta(seconds=1)
        assert first.header.id != second.header.id
        assert log.read() == [first, second]


def test_log_gets_header_but_never_body(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    with Database(tmp_path / "m.db") as db:
        event = Recorder(SqliteEventLog(db), FakeClock()).emit(
            EventKind.STT_SEGMENT,
            "pipeline.events",
            {"text": "annemin doğum günü yarın"},
            session="s1",
            status=Status.OK,
        )
    assert str(event.header.id) in caplog.text
    assert "stt.segment" in caplog.text
    assert "doğum günü" not in caplog.text


def test_unwritable_event_is_not_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    with Database(tmp_path / "m.db") as db:
        recorder = Recorder(SqliteEventLog(db), FakeClock())
        with pytest.raises(TypeError):
            recorder.emit(EventKind.LLM_USAGE, "pipeline.events", {"x": object()})
    assert "llm.usage" not in caplog.text
