"""Bağlama (§4): somut adaptörleri, servisleri ve skill'leri tanıyan tek yer.

Süreçte bir `Core` vardır (depolar, kayıt defteri, tur kuyruğu); her oturum ondan kendi
hattını kurar (§5.2). Ses birimleri (girdi, STT, TTS, çıktı) dışarıdan verilir: hangi motorun
kullanılacağı hattın kuralı değildir, ve ses bağımlılıkları ancak ses hattıyla gelir.
"""

import importlib
import pkgutil
from collections.abc import Mapping, Sequence
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
from mayen.adapters.storage.sqlite import (
    Database,
    SqliteEventLog,
    SqliteNoteStore,
    SqliteTimerStore,
)
from mayen.adapters.trigger.timer import TimerTrigger
from mayen.app.config import Config, ConfigError
from mayen.core.events import Recorder, SystemClock
from mayen.core.policy import ROLE_TABLE, PolicyTable, system_table
from mayen.core.registry import ToolRegistry
from mayen.core.timers import TimerDispatcher
from mayen.pipeline.confirmation import ConfirmationGateProcessor, NoRecoveryWhileAwaiting
from mayen.pipeline.events import EventObserver, SessionEvents
from mayen.pipeline.llm import llm_service
from mayen.pipeline.session import UNIDENTIFIED, CallerSource, HeardOnly, Sessions, TriggerGate
from mayen.pipeline.tools import AuthorizedTools
from mayen.ports.events import Clock
from mayen.ports.models import ModelRole
from mayen.ports.notes import NoteStore
from mayen.ports.timers import TimerStore
from mayen.ports.tools import Caller, ToolSpec, TurnFlags
from mayen.ports.triggers import TriggerSource

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


def skill_defaults(
    specs: Sequence[ToolSpec[Any]], overrides: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Her skill'in varsayılanları, sahibin config'te üzerine yazdıklarıyla (§9.1).

    Bilinmeyen bir skill ya da anahtar, ya da tipi tutmayan bir değer açılışta hatadır:
    sessizce yok sayılan bir ayar, sahibin değiştirdiğini sandığı bir davranıştır.
    """
    merged = {spec.name: dict(spec.defaults) for spec in specs}
    for name, values in overrides.items():
        if name not in merged:
            raise ConfigError(f"skills.{name}: no such skill")
        for key, value in values.items():
            if key not in merged[name]:
                raise ConfigError(f"skills.{name}.{key}: the skill has no such default")
            default = merged[name][key]
            # Tam sayı, ondalık bir varsayılanın yerine geçebilir; tersi ve gerisi geçemez.
            numeric = isinstance(default, float) and type(value) is int
            if type(value) is not type(default) and not numeric:
                raise ConfigError(
                    f"skills.{name}.{key}: expected {type(default).__name__}, "
                    f"got {type(value).__name__}"
                )
            merged[name][key] = value
    return merged


@dataclass(frozen=True)
class ToolCtx:
    """Skill'lerin gördüğü tek şey: depo portları, saat, çağıran ve varsayılanlar (§9.1)."""

    notes: NoteStore
    timers: TimerStore
    clock: Clock
    caller: Caller
    defaults: Mapping[str, Any]


# Turu açabilen, kimse konuşmadan gelen kaynaklar; her birinin `system` yetkisi config'te
# tanımlı olmalıdır (§10.2). Olay kaynağı adaptörüyle gelince buraya girer.
SYSTEM_SOURCES = (TriggerSource.TIMER,)


class Core:
    """Süreç başına bir tane: oturumların paylaştığı her şey."""

    def __init__(self, config: Config, db: Database) -> None:
        self.config = config
        self.recorder = Recorder(SqliteEventLog(db), SystemClock())
        self.sessions = Sessions(config.turns(), config.triggers.voice_priority)
        specs = discover_skills()
        self.registry = ToolRegistry(specs)
        self.defaults = skill_defaults(specs, config.skills)
        self.notes = SqliteNoteStore(db)
        self.timers = SqliteTimerStore(db)
        missing = [s.value for s in SYSTEM_SOURCES if s not in config.system_role]
        if missing:
            # Sessiz bir varsayılan, tetikleyiciyi ya tam yetkiyle ya hiç yetkisiz koşturur.
            raise ConfigError(f"system_role: no permissions for {missing}")
        self.tables: dict[TriggerSource, PolicyTable] = {
            source: {**ROLE_TABLE, **system_table(config.system_role[source])}
            for source in SYSTEM_SOURCES
        }
        dispatcher = TimerDispatcher(
            self.timers, self.recorder.clock, self.sessions.submit, self._timer_target
        )
        # Döngüyü hattı kuran başlatır; oturumsuz bir süreçte bakacak bir hedef yoktur.
        self.timer_trigger = TimerTrigger(dispatcher.dispatch)

    def _timer_target(self) -> str | None:
        # Hedef, kişinin en son etkileşimde bulunduğu cihazdır (§12); kanal ve profil
        # portları gelene kadar hattı kurulmuş ilk oturum.
        names = self.sessions.names()
        return names[0] if names else None

    def table(self, session: str) -> PolicyTable:
        """Oturumun süren turuna göre yetki tablosu: `system`'in yetkisi kaynağa bağlıdır."""
        turn = self.sessions.running(session)
        if turn is None:
            return ROLE_TABLE
        return self.tables.get(turn.trigger.source, ROLE_TABLE)

    def context(self, spec: ToolSpec[Any], caller: Caller) -> ToolCtx:
        return ToolCtx(
            self.notes, self.timers, self.recorder.clock, caller, self.defaults[spec.name]
        )


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
        core.registry,
        lambda: core.table(session),
        core.context,
        confirmation,
        caller,
        TurnFlags,
        events,
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
