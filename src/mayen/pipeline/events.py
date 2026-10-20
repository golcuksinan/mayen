"""Hattan olay ve transkript üretimi (§5.5, §11): gözlemcinin gördüğü kareler, oturum bağlamı.

Ayrı bir olay altyapısı yoktur; gözlemci her kareyi ilk itilişinde bir kez görür ve
olaya dönüştürdüklerini çekirdeğin `Recorder`'ına verir. Mayen'in kendi katmanındaki
olaylar (tur, tool, onay) onları üreten işlemcilerde yayımlanır. Duyulan sözü tetikleyici
kapısı yazar: gözlemci kareyi geç görebilir, sözün kaydını ise arkadaki onay kapısı bilmelidir.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pipecat.frames.frames import ErrorFrame, MetricsFrame
from pipecat.metrics.metrics import LLMUsageMetricsData
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.services.llm_service import LLMService
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService

from mayen.core.events import Recorder
from mayen.core.state import StateTracker
from mayen.core.transcript import Transcript
from mayen.pipeline.wake import ServiceWake
from mayen.ports.events import Event, EventKind, FaultPart, SessionState
from mayen.ports.tools import Caller, Status
from mayen.ports.transcript import Utterance
from mayen.ports.triggers import TurnId

# Sözün transkriptteki kaydı (`ref`), STT karesinin üstünde hattın aşağısına taşınır.
UTTERANCE = "mayen.utterance"


class SessionEvents:
    """Bir oturumun olayları: oturum ve o anki tur kimliği başlığa kendiliğinden girer."""

    def __init__(
        self, recorder: Recorder, session: str, turn: Callable[[], TurnId | None]
    ) -> None:
        self._recorder = recorder
        self.session = session
        self._turn = turn

    def monotonic(self) -> float:
        return self._recorder.clock.monotonic()

    def emit(
        self,
        kind: EventKind,
        source: str,
        body: Mapping[str, Any] | None = None,
        *,
        duration_s: float | None = None,
        status: Status | None = None,
        related: Sequence[str] = (),
    ) -> Event:
        return self._recorder.emit(
            kind,
            source,
            body,
            session=self.session,
            turn_id=self._turn(),
            duration_s=duration_s,
            status=status,
            related=related,
        )

    def fault(self, part: FaultPart, detail: str) -> Event:
        """Bozulan parça (§5.4 hata kanalı, §14: hata hem kayda hem kişiye)."""
        return self.emit(EventKind.FAULT, __name__, {"part": part.value, "detail": detail})


def fault_part(processor: FrameProcessor | None) -> FaultPart:
    """Hata karesini üreten işlemcinin parçası."""
    for kind, part in (
        (LLMService, FaultPart.MODEL),
        (STTService, FaultPart.STT),
        (TTSService, FaultPart.TTS),
        (ServiceWake, FaultPart.WAKE),
    ):
        if isinstance(processor, kind):
            return part
    return FaultPart.OTHER


def session_state(events: SessionEvents) -> StateTracker:
    """Oturumun durumu; her değişim bir `state.changed` olayıdır (§5.4, §5.5)."""

    def changed(previous: SessionState, current: SessionState) -> None:
        events.emit(
            EventKind.STATE_CHANGED,
            __name__,
            {"state": current.value, "previous": previous.value},
            status=Status.OK,
        )

    return StateTracker(changed)


class SessionTranscript:
    """Bir oturumun transkripti: oturum ve o anki tur kimliği söze kendiliğinden girer."""

    def __init__(
        self, transcript: Transcript, session: str, turn: Callable[[], TurnId | None]
    ) -> None:
        self._transcript = transcript
        self.session = session
        self._turn = turn

    def heard(self, speaker: Caller, text: str) -> Utterance:
        return self._transcript.heard(self.session, self._turn(), speaker, text)

    def said(self, text: str, *, interrupted: bool) -> Utterance:
        return self._transcript.said(self.session, self._turn(), text, interrupted=interrupted)


class EventObserver(BaseObserver):
    """LLM token sayıları (yalnızca hatta kullanım ölçümü açıkken gelir) ve hattın hata
    kareleri: Pipecat'in servisleri hatayı yukarı akan bir kareyle bildirir."""

    def __init__(self, events: SessionEvents) -> None:
        # Her kare hattın her adımında yeniden itilir; olay ilk itilişte bir kez üretilir.
        super().__init__(observe_every_push=False)
        self._events = events

    async def on_push_frame(self, data: FramePushed) -> None:
        frame = data.frame
        if isinstance(frame, ErrorFrame):
            detail = frame.error
            part = fault_part(frame.processor)
            if part is FaultPart.OTHER and frame.processor is not None:
                detail = f"{frame.processor.name}: {detail}"
            self._events.fault(part, detail)
        elif isinstance(frame, MetricsFrame):
            for metric in frame.data:
                if isinstance(metric, LLMUsageMetricsData):
                    self._events.emit(
                        EventKind.LLM_USAGE,
                        __name__,
                        {"model": metric.model, **metric.value.model_dump(exclude_none=True)},
                        status=Status.OK,
                    )
