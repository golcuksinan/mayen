"""Bağlama (§4): somut adaptörleri, servisleri ve skill'leri tanıyan tek yer.

Süreçte bir `Core` vardır (depolar, kayıt defteri, tur kuyruğu); her oturum ondan kendi
hattını kurar (§5.2). Oturum cihaz başınadır: sesli oturum çekirdeğin kendi ses birimleriyle,
yazılı oturum her bağlantıyla kurulur. Ses birimleri (girdi, STT, TTS, çıktı) dışarıdan
verilir: hangi motorun kullanılacağı hattın kuralı değildir. STT ve TTS'in olağan kaynağı
config'teki model servisleridir (`Core.speech`); modeller çekirdekte yüklenmez (§18).
"""

import importlib
import pkgutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pipecat.audio.vad.vad_analyzer import VADAnalyzer
from pipecat.observers.base_observer import BaseObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    AssistantTurnStoppedMessage,
    LLMAssistantAggregator,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport

import mayen.skills
from mayen.adapters.llamacpp.chat import LlamaCppChat
from mayen.adapters.llamacpp.confirmation import LlamaCppAnswerResolver, LlamaCppQuestionWriter
from mayen.adapters.storage.sqlite import (
    Database,
    SqliteEventLog,
    SqliteNoteStore,
    SqlitePersonStore,
    SqliteTimerStore,
    SqliteTranscript,
)
from mayen.adapters.trigger.timer import TimerTrigger
from mayen.app.config import Config, ConfigError
from mayen.core.context import ContextBlock
from mayen.core.events import Recorder, SystemClock
from mayen.core.feed import Feed
from mayen.core.policy import ROLE_TABLE, PolicyTable, system_table
from mayen.core.presence import Presence
from mayen.core.profile import caller as caller_of
from mayen.core.registry import ToolRegistry
from mayen.core.state import StateTracker
from mayen.core.timers import TimerDispatcher
from mayen.core.transcript import Transcript
from mayen.pipeline.confirmation import ConfirmationGateProcessor, NoRecoveryWhileAwaiting
from mayen.pipeline.events import (
    EventObserver,
    SessionEvents,
    SessionTranscript,
    session_state,
)
from mayen.pipeline.llm import StepCap, llm_service
from mayen.pipeline.session import UNIDENTIFIED, CallerSource, HeardOnly, Sessions, TriggerGate
from mayen.pipeline.speech import ServiceSTT, ServiceTTS, ServiceVAD
from mayen.pipeline.text import TextInput, TextOutput
from mayen.pipeline.tools import AuthorizedTools
from mayen.ports.events import Clock
from mayen.ports.models import ModelRole
from mayen.ports.notes import NoteStore
from mayen.ports.people import DeviceId
from mayen.ports.timers import TimerStore
from mayen.ports.tools import Caller, Role, ToolSpec, TurnFlags
from mayen.ports.triggers import TriggerSource
from mayen.replay.run import Replayer

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


# TTS, cevabın dilini soran bir çağrılabilirle kurulur: ses dile göre seçilir (§16.3).
type TtsFactory = Callable[[Callable[[], str]], FrameProcessor]


# Turu açabilen, kimse konuşmadan gelen kaynaklar; her birinin `system` yetkisi config'te
# tanımlı olmalıdır (§10.2). Olay kaynağı adaptörüyle gelince buraya girer.
SYSTEM_SOURCES = (TriggerSource.TIMER,)


class Core:
    """Süreç başına bir tane: oturumların paylaştığı her şey."""

    def __init__(self, config: Config, db: Database) -> None:
        self.config = config
        # Panel kayda girenleri buradan canlı izler (§5.5); geçmişi depolardan okur.
        self.feed = Feed()
        self.events = SqliteEventLog(db)
        self.utterances = SqliteTranscript(db)
        self.recorder = Recorder(self.events, SystemClock(), self.feed)
        self.transcript = Transcript(self.utterances, self.recorder.clock, self.feed)
        self.presence = Presence()
        self.sessions = Sessions(
            config.turns(), config.triggers.voice_priority, self._interacted
        )
        self.people = SqlitePersonStore(db)
        self.context_block = ContextBlock(
            self.people,
            self.presence,
            self.recorder.clock,
            config.language_rule,
            config.default_language,
        )
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
            self.timers, self.recorder.clock, self.sessions.submit, self.presence.target
        )
        # Döngüyü hattı kuran başlatır; oturumsuz bir süreçte bakacak bir hedef yoktur.
        self.timer_trigger = TimerTrigger(dispatcher.dispatch)

    def _interacted(self, session: str, requester: Caller) -> None:
        if requester.person_id is not None:
            self.presence.interacted(requester.person_id, session)

    def connect(self, session: str, device: DeviceId | None) -> Caller:
        """Oturumun cihazını kaydeder; cihaz bir kişiye eşleşmişse o kişinin çağıranı döner."""
        person = None if device is None else self.people.by_device(device)
        self.presence.connected(session, device, None if person is None else person.id)
        return caller_of(person)

    async def disconnect(self, session: str) -> None:
        self.presence.disconnected(session)
        await self.sessions.detach(session)

    def table(self, session: str) -> PolicyTable:
        """Oturumun süren turuna göre yetki tablosu: `system`'in yetkisi kaynağa bağlıdır."""
        turn = self.sessions.running(session)
        if turn is None:
            return ROLE_TABLE
        return self.tables.get(turn.trigger.source, ROLE_TABLE)

    def caller(self, role: Role, person_id: str | None) -> Caller:
        """Kayıttaki rol ve kimlikten çağıran; kişisel cihazı profilden (replay, §14)."""
        person = None if person_id is None else self.people.get(person_id)
        return (
            Caller(role, person_id, has_personal_device=False)
            if person is None
            else caller_of(person)
        )

    def speech(self) -> tuple[FrameProcessor, TtsFactory, VADAnalyzer]:
        """Config'teki STT ve TTS servislerinin istemcileri (§3); VAD modeli STT servisinde."""
        stt, tts = self.config.stt, self.config.tts
        if stt is None or tts is None:
            raise ConfigError("a voice session needs both stt and tts in the config")

        def make_tts(language: Callable[[], str]) -> FrameProcessor:
            return ServiceTTS(tts.url, tts.voices, language)

        return ServiceSTT(stt.url, stt.language), make_tts, ServiceVAD(stt.url)

    def context(self, spec: ToolSpec[Any], caller: Caller) -> ToolCtx:
        return ToolCtx(
            self.notes, self.timers, self.recorder.clock, caller, self.defaults[spec.name]
        )


@dataclass(frozen=True)
class Voice:
    """Sesli bir oturumun dış birimleri; hattı kuran seçer."""

    input: FrameProcessor
    stt: FrameProcessor
    tts: TtsFactory
    output: FrameProcessor
    vad: VADAnalyzer
    # Konuşmacı tanıma gelene kadar sözün kime ait olduğunu hattı kuran söyler (§10.4);
    # `None` sözü cihazın kişisine verir, yazılı kanaldaki gibi (kişisel değilse tanımsız).
    caller: CallerSource | None
    # Ses birimlerinin cihazı; çekirdeğin kendi makinesindeyse `LOCAL_DEVICE` (§10.1).
    device: DeviceId | None


@dataclass
class Session:
    """Kurulmuş bir oturum: işçisi ve olaylarını okumak isteyenler için parçaları."""

    worker: PipelineWorker
    gate: TriggerGate
    confirmation: ConfirmationGateProcessor
    observers: Sequence[BaseObserver] = field(default_factory=list)


@dataclass
class _Conversation:
    """Oturumun girdiden bağımsız parçaları: kapı, onay, toplayıcılar, model."""

    gate: TriggerGate
    confirmation: ConfirmationGateProcessor
    aggregators: LLMContextAggregatorPair
    llm: FrameProcessor
    events: SessionEvents
    state: StateTracker
    language: Callable[[], str]  # süren turu isteyenin dili (§8.6)


def _conversation(
    core: Core, session: str, speaker: CallerSource, vad: VADAnalyzer | None
) -> _Conversation:
    config = core.config
    endpoint = config.models.endpoint(CONVERSATION_ROLE)

    def turn_id() -> Any:  # noqa: ANN401  # TurnId | None
        turn = core.sessions.running(session)
        return None if turn is None else turn.id

    def caller() -> Caller:
        turn = core.sessions.running(session)
        return UNIDENTIFIED if turn is None else turn.trigger.requester

    def language() -> str:
        return core.context_block.language(session, caller())

    events = SessionEvents(core.recorder, session, turn_id)
    transcript = SessionTranscript(core.transcript, session, turn_id)
    state = session_state(events)
    confirmation = ConfirmationGateProcessor(
        # Onay sorusu, turu isteyenin dilinde (§8.6).
        LlamaCppQuestionWriter(endpoint, language),
        LlamaCppAnswerResolver(endpoint),
        config.confirmation.timeout_s,
        lambda frame: speaker(frame).person_id,
        events,
        state.awaiting,
    )
    gate = TriggerGate(
        session,
        core.sessions,
        speaker,
        core.recorder,
        settle_s=config.triggers.settle_s,
        response_timeout_s=config.triggers.response_timeout_s,
        transcript=transcript,
        holds=[lambda: confirmation.awaiting],
        drops=[confirmation.drop],
        device_person=lambda: core.presence.personal(session),
        state=state,
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
    llm = llm_service(
        endpoint,
        config.system_prompt,
        lambda: core.context_block.render(session, caller()),
        StepCap(config.loop.max_steps, config.loop.max_corrections),
        tools.malformed,
    )
    tools.register(llm)
    aggregators = LLMContextAggregatorPair(
        LLMContext(tools=tools.schema()),
        user_params=LLMUserAggregatorParams(
            vad_analyzer=vad,
            user_mute_strategies=[HeardOnly(gate)] if vad is not None else [],
            empty_user_turn=NoRecoveryWhileAwaiting(confirmation),
        ),
    )
    _bind_response(aggregators.assistant(), gate, transcript)
    return _Conversation(gate, confirmation, aggregators, llm, events, state, language)


def _session(core: Core, conversation: _Conversation, pipeline: Pipeline) -> Session:
    observers: list[BaseObserver] = [EventObserver(conversation.events)]
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=observers,
        # İstemci RTVI konuşmaz; açık kalırsa yazılı kanalın her mesajını kendi biçimi sanır.
        enable_rtvi=False,
    )
    return Session(worker, conversation.gate, conversation.confirmation, observers)


def voice_session(core: Core, session: str, voice: Voice) -> Session:
    requester = core.connect(session, voice.device)
    speaker = voice.caller or (lambda _: requester)
    c = _conversation(core, session, speaker, voice.vad)
    pipeline = Pipeline(
        [
            voice.input,
            voice.stt,
            c.gate,
            c.confirmation,
            c.aggregators.user(),
            c.llm,
            voice.tts(c.language),
            voice.output,
            c.aggregators.assistant(),
        ]
    )
    return _session(core, c, pipeline)


def text_session(
    core: Core, session: str, transport: BaseTransport, device: DeviceId | None
) -> Session:
    """Bir yazılı bağlantının oturumu (§7). Yazının kime ait olduğunu cihaz söyler: kişisel
    cihazdan gelen yazı o kişinindir, doğrulanmamış ya da ortak cihazdan gelen tanımsızdır."""
    requester = core.connect(session, device)
    c = _conversation(core, session, lambda _: requester, None)
    text_input = TextInput(
        session,
        core.sessions,
        c.confirmation,
        requester,
        core.config.triggers.text_priority,
        core.transcript,
    )
    pipeline = Pipeline(
        [
            transport.input(),
            text_input,
            c.gate,
            c.confirmation,
            c.aggregators.user(),
            c.llm,
            TextOutput(c.state.speaking),
            transport.output(),
            c.aggregators.assistant(),
        ]
    )
    return _session(core, c, pipeline)


def _bind_response(
    assistant: LLMAssistantAggregator, gate: TriggerGate, transcript: SessionTranscript
) -> None:
    """Model cevabının başı ve sonu turun bitişine girer (§5.4); söylenen transkripte (§11).

    Toplayıcının metni söylenendir: kesilen cevapta söylenen kadarı. Yalnızca tool çağıran
    bir cevapta söz yoktur.
    """

    async def started(_: LLMAssistantAggregator) -> None:
        gate.response_started()

    async def stopped(_: LLMAssistantAggregator, message: AssistantTurnStoppedMessage) -> None:
        gate.response_stopped()
        if message.content.strip():
            transcript.said(message.content, interrupted=message.interrupted)

    assistant.add_event_handler("on_assistant_turn_started", started)
    assistant.add_event_handler("on_assistant_turn_stopped", stopped)


def replayer(core: Core, db: Database) -> Replayer:
    """Kayıtlı turları bugünkü config'le oynatan (§14); hattı kurmaz, modele doğrudan gider."""
    config = core.config
    return Replayer(
        SqliteEventLog(db),
        SqliteTranscript(db),
        core.timers,
        core.people,
        core.registry,
        core.caller,
        lambda source: core.tables.get(source, ROLE_TABLE),
        LlamaCppChat(config.models.endpoint(CONVERSATION_ROLE)),
        config.system_prompt,
        config.language_rule,
        config.default_language,
        StepCap(config.loop.max_steps, config.loop.max_corrections),
    )
