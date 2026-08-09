"""Tur izi (§15) ve tersine dönen bağımlılık.

`_sink` ataması testin en önemli satırı: `TraceRepository`'nin `obs`'un `TraceSink`
`Protocol`'üne uyduğunu mypy doğrular. Uymazsa `obs`'un `data`'ya inmesi gerekirdi ve
sınır testi onu reddederdi.
"""

from pathlib import Path

import pytest

from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.traces import TraceRepository
from mayen.obs.trace import Outcome, Stage, TraceSink, TurnTrace, new_turn_id, tool_stage


def test_turn_ids_are_unique() -> None:
    """§13: kimlik tel formatının parçası; çakışma söz kesmeyi bozar."""
    assert len({new_turn_id() for _ in range(1000)}) == 1000


def test_trace_round_trip(tmp_path: Path) -> None:
    database = Database(tmp_path / "mayen.db")
    migrate(database)
    repository = TraceRepository(database)
    # Tersine dönen bağımlılığın mypy tarafından doğrulandığı yer.
    sink: TraceSink = repository

    with TurnTrace(sink, "salon", turn_id="t1") as trace:
        with trace.stage(Stage.STT, detail="14 kelime"):
            pass
        trace.mark(Stage.LLM_ILK_TOKEN)
        with trace.stage(tool_stage("weather")):
            pass

    written = repository.get("t1")
    assert written is not None
    assert written.device_id == "salon"
    assert written.outcome == Outcome.TAMAM
    assert written.ended_at is not None
    assert [stage.name for stage in written.stages] == ["stt", "llm_ilk_token", "tool:weather"]
    assert [stage.seq for stage in written.stages] == [1, 2, 3]


def test_stage_duration_is_measured_not_left_empty() -> None:
    recorded = _Recorder()
    with TurnTrace(recorded, "salon") as trace, trace.stage(Stage.BAGLAM):
        pass
    assert recorded.stages[0][1] is not None
    assert recorded.stages[0][1] >= 0


def test_mark_has_no_duration() -> None:
    recorded = _Recorder()
    with TurnTrace(recorded, "salon") as trace:
        trace.mark(Stage.ILK_SES)
    assert recorded.stages == [(Stage.ILK_SES, None)]


def test_failed_stage_is_still_written() -> None:
    """Ölçümün en çok işe yaradığı an, bir şeyin yavaşlayıp patladığı andır."""
    recorded = _Recorder()
    trace = TurnTrace(recorded, "salon")
    with pytest.raises(RuntimeError), trace, trace.stage(Stage.STT):
        raise RuntimeError("stt çöktü")

    assert [name for name, _ in recorded.stages] == [Stage.STT]
    assert recorded.outcome == Outcome.HATA


def test_cancelled_turn_is_not_recorded_as_an_error() -> None:
    """Kural 12: iptal beklenen bir son. `BaseException` olduğu için `Exception`'dan
    ayrılıyor — iptali hata saymak hata sayacını okunamaz hale getirirdi."""
    recorded = _Recorder()
    with pytest.raises(KeyboardInterrupt), TurnTrace(recorded, "salon"):
        raise KeyboardInterrupt

    assert recorded.outcome == Outcome.IPTAL


def test_explicit_outcome_is_not_overwritten_on_exit() -> None:
    recorded = _Recorder()
    with TurnTrace(recorded, "salon") as trace:
        trace.finish(Outcome.IPTAL)
    assert recorded.outcome == Outcome.IPTAL


class _Recorder:
    """Belleğe yazan `TraceSink`. Sözleşmenin veritabanı olmadan da uygulanabildiğini
    göstermesi tesadüf değil — yeniden oynatma (§15) tam olarak bunu gerektirecek."""

    def __init__(self) -> None:
        self.started: tuple[str, str] | None = None
        self.stages: list[tuple[str, int | None]] = []
        self.outcome: str | None = None

    def start(self, turn_id: str, device_id: str, *, person_id: int | None = None) -> None:
        self.started = (turn_id, device_id)

    def add_stage(
        self,
        turn_id: str,
        name: str,
        *,
        duration_ms: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.stages.append((name, duration_ms))

    def finish(self, turn_id: str, outcome: str) -> None:
        self.outcome = outcome


_sink: TraceSink = _Recorder()
