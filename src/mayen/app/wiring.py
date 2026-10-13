"""Bağlama (§4): somut adaptörleri, servisleri ve skill'leri tanıyan tek yer.

Süreçte bir `Core` vardır (depolar, kayıt defteri, tur kuyruğu); her oturum ondan kendi
hattını kurar (§5.2). Ses birimleri (girdi, STT, TTS, çıktı) dışarıdan verilir: hangi motorun
kullanılacağı hattın kuralı değildir, ve ses bağımlılıkları ancak ses hattıyla gelir.
"""

import importlib
import pkgutil
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.observers.base_observer import BaseObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMAssistantAggregator,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameProcessor

import mayen.skills
from mayen.adapters.llamacpp.confirmation import LlamaCppAnswerResolver, LlamaCppQuestionWriter
from mayen.adapters.storage.memory import MemoryNoteStore
from mayen.adapters.storage.sqlite import Database, SqliteEventLog
from mayen.app.config import Config
from mayen.core.events import Recorder, SystemClock
from mayen.core.policy import ROLE_TABLE
from mayen.core.registry import ToolRegistry
from mayen.pipeline.confirmation import ConfirmationGateProcessor, NoRecoveryWhileAwaiting
from mayen.pipeline.events import EventObserver, SessionEvents
from mayen.pipeline.llm import llm_service
from mayen.pipeline.session import UNIDENTIFIED, CallerSource, HeardOnly, Sessions, TriggerGate
from mayen.pipeline.tools import AuthorizedTools
from mayen.ports.events import Clock
from mayen.ports.models import ModelRole
from mayen.ports.notes import NoteStore
from mayen.ports.tools import Caller, ToolSpec, TurnFlags

# Tek kip (§8.10): bir rol hem tool kararını hem cevabı yazar; onay soruları da bu rolde.
CONVERSATION_ROLE = ModelRole.TALKER


class SkillLoadError(Exception):
    pass


def discover_skills() -> list[ToolSpec[Any]]:
    """`skills/` klasöründeki her modülün `SPEC`'i; katalog açılışta bir kez kurulur (§9.2)."""
    specs: list[ToolSpec[Any]] = []
    for info in sorted(pkgutil.iter_modules(mayen.skills.__path__), key=lambda m: m.name):
        module = importlib.import_module(f"mayen.skills.{info.name}")
        spec = getattr(module, "SPEC", None)
        if not isinstance(spec, ToolSpec):
            # Sessizce atlanan bir skill, modelin hiç görmediği bir skill demektir.
            raise SkillLoadError(f"mayen.skills.{info.name} has no SPEC")
        specs.append(spec)
    return specs


@dataclass(frozen=True)
class ToolCtx:
    """Skill'lerin gördüğü tek şey: depo portları ve saat (§9.1)."""

    notes: NoteStore
    clock: Clock


class Core:
    """Süreç başına bir tane: oturumların paylaştığı her şey."""

    def __init__(self, config: Config, db: Database) -> None:
        self.config = config
        self.recorder = Recorder(SqliteEventLog(db), SystemClock())
        self.sessions = Sessions(config.turns(), config.triggers.voice_priority)
        self.registry = ToolRegistry(discover_skills())
        self.ctx = ToolCtx(MemoryNoteStore(), self.recorder.clock)


@dataclass(frozen=True)
class Voice:
    """Sesli bir oturumun dış birimleri; hattı kuran seçer."""

    input: FrameProcessor
    stt: FrameProcessor
    tts: FrameProcessor
    output: FrameProcessor
    vad: VADAnalyzer
    # Konuşmacı tanıma gelene kadar sözün kime ait olduğunu hattı kuran söyler (§10.4).
    caller: CallerSource


@dataclass
class Session:
    """Kurulmuş bir oturum: işçisi ve olaylarını okumak isteyenler için parçaları."""

    worker: PipelineWorker
    gate: TriggerGate
    confirmation: ConfirmationGateProcessor
    observers: Sequence[BaseObserver] = field(default_factory=list)


def voice_session(core: Core, session: str, voice: Voice) -> Session:
    config = core.config
    endpoint = config.models.endpoint(CONVERSATION_ROLE)
    gate: TriggerGate | None = None

    def turn_id() -> Any:  # noqa: ANN401  # TurnId | None; kapı aşağıda kurulur
        turn = core.sessions.running(session)
        return None if turn is None else turn.id

    def caller() -> Caller:
        turn = core.sessions.running(session)
        return UNIDENTIFIED if turn is None else turn.trigger.requester

    events = SessionEvents(core.recorder, session, turn_id)
    confirmation = ConfirmationGateProcessor(
        LlamaCppQuestionWriter(endpoint, config.output_language),
        LlamaCppAnswerResolver(endpoint),
        config.confirmation.timeout_s,
        lambda frame: voice.caller(frame).person_id,
        events,
    )
    gate = TriggerGate(
        session,
        core.sessions,
        voice.caller,
        core.recorder,
        settle_s=config.triggers.settle_s,
        response_timeout_s=config.triggers.response_timeout_s,
        holds=[lambda: confirmation.awaiting],
    )
    tools = AuthorizedTools(
        core.registry, ROLE_TABLE, core.ctx, confirmation, caller, TurnFlags, events
    )
    llm = llm_service(endpoint, config.system_prompt)
    tools.register(llm)
    aggregators = LLMContextAggregatorPair(
        LLMContext(tools=tools.schema()),
        user_params=LLMUserAggregatorParams(
            vad_analyzer=voice.vad,
            user_mute_strategies=[HeardOnly(gate)],
            empty_user_turn=NoRecoveryWhileAwaiting(confirmation),
        ),
    )
    _bind_response(aggregators.assistant(), gate)
    pipeline = Pipeline(
        [
            voice.input,
            voice.stt,
            gate,
            confirmation,
            aggregators.user(),
            llm,
            voice.tts,
            voice.output,
            aggregators.assistant(),
        ]
    )
    observers: list[BaseObserver] = [EventObserver(events)]
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=observers,
    )
    return Session(worker, gate, confirmation, observers)


def _bind_response(assistant: LLMAssistantAggregator, gate: TriggerGate) -> None:
    """Model cevabının başı ve sonu turun bitişine girer (§5.4)."""

    async def started(_: LLMAssistantAggregator) -> None:
        gate.response_started()

    async def stopped(_: LLMAssistantAggregator, __: object) -> None:
        gate.response_stopped()

    assistant.add_event_handler("on_assistant_turn_started", started)
    assistant.add_event_handler("on_assistant_turn_stopped", stopped)
