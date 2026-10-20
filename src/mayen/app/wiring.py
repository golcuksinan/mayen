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

from pipecat.audio.turn.base_turn_analyzer import BaseTurnAnalyzer
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
from pipecat.turns.user_start import (
    TranscriptionUserTurnStartStrategy,
    VADUserTurnStartStrategy,
)
from pipecat.turns.user_turn_strategies import ExternalUserTurnStrategies, UserTurnStrategies

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
    SqliteVoiceprintStore,
)
from mayen.adapters.trigger.timer import TimerTrigger
from mayen.adapters.weather.openweathermap import OpenWeatherMap
from mayen.app.config import Config, ConfigError
from mayen.core.context import ContextBlock
from mayen.core.devices import DeviceLink, Devices
from mayen.core.events import Recorder, SystemClock
from mayen.core.feed import Feed
from mayen.core.policy import ROLE_TABLE, PolicyTable, system_table
from mayen.core.presence import Presence
from mayen.core.profile import caller as caller_of
from mayen.core.registry import ToolRegistry
from mayen.core.speakers import SpeakerMatcher, label
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
from mayen.pipeline.session import (
    UNIDENTIFIED,
    CallerSource,
    HeardOnly,
    RequesterSource,
    Sessions,
    TriggerGate,
)
from mayen.pipeline.sounds import ToolSound
from mayen.pipeline.speaker import SpeakerLabel, recognized, recognized_turn
from mayen.pipeline.speech import (
    ServiceSpeaker,
    ServiceSTT,
    ServiceTTS,
    ServiceTurn,
    ServiceVAD,
    TurnEndToStt,
)
from mayen.pipeline.text import TextInput, TextOutput
from mayen.pipeline.tools import AuthorizedTools, Shown
from mayen.pipeline.wake import ServiceWake, WakeStart
from mayen.ports.channels import AudioInput
from mayen.ports.devices import DeviceControl
from mayen.ports.events import Clock
from mayen.ports.models import ModelRole
from mayen.ports.notes import NoteStore
from mayen.ports.people import DeviceId
from mayen.ports.timers import TimerStore
from mayen.ports.tools import Caller, Role, SkillConfig, ToolSpec, TurnFlags
from mayen.ports.triggers import TriggerSource
from mayen.ports.weather import WeatherSource
from mayen.replay.run import Replayer

# Tek kip (§8.10): bir rol hem tool kararını hem cevabı yazar; onay soruları da bu rolde.
CONVERSATION_ROLE = ModelRole.TALKER


class SkillLoadError(Exception):
    pass


def discover_skills(tables: SkillConfig | None = None) -> list[ToolSpec[Any]]:
    """`skills/` klasöründeki her modülün `SPEC`'i, ya da config'in tablolarından kurulan
    `spec(tables)`'ı; katalog açılışta bir kez kurulur (§9.2). Tablosu boş skill `None` verir
    ve kataloğa girmez."""
    tables = tables or SkillConfig()
    specs: list[ToolSpec[Any]] = []
    for info in sorted(pkgutil.iter_modules(mayen.skills.__path__), key=lambda m: m.name):
        module = importlib.import_module(f"mayen.skills.{info.name}")
        spec = getattr(module, "SPEC", None)
        build = getattr(module, "spec", None)
        if spec is None and callable(build):
            spec = build(tables)
            if spec is None:
                continue
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
    """Skill'lerin gördüğü tek şey: depo portları, saat, oturumun cihazı, çağıran ve
    varsayılanlar (§9.1)."""

    notes: NoteStore
    timers: TimerStore
    clock: Clock
    device: DeviceControl
    weather: WeatherSource | None
    location: str | None  # çağıranın kendi varsayılan konumu (§11.1)
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
        self.devices = Devices()
        self.sessions = Sessions(
            config.turns(), config.triggers.voice_priority, self._interacted
        )
        self.people = SqlitePersonStore(db)
        speaker = config.speaker
        # Konuşmacı tanıma yoksa söz cihazın kişisinindir (`Voice.caller`).
        self.matcher = (
            None
            if speaker is None
            else SpeakerMatcher(SqliteVoiceprintStore(db), speaker.threshold)
        )
        self.context_block = ContextBlock(
            self.people,
            self.presence,
            self.recorder.clock,
            config.language_rule,
            config.default_language,
            self.devices.capabilities,
        )
        weather = config.weather
        self.weather: WeatherSource | None = (
            None if weather is None else OpenWeatherMap(weather.url, weather.key)
        )
        specs = discover_skills(SkillConfig(apps=config.apps, weather=weather is not None))
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

    def attach_device(self, session: str, link: DeviceLink) -> None:
        """Oturumun istemcisine giden komut yolu (§9.7); yazılı kanalın yoktur."""
        self.devices.attach(session, link)

    async def disconnect(self, session: str) -> None:
        self.presence.disconnected(session)
        self.devices.detach(session)
        await self.sessions.detach(session)

    def table(self, session: str) -> PolicyTable:
        """Oturumun süren turuna göre yetki tablosu: `system`'in yetkisi kaynağa bağlıdır."""
        turn = self.sessions.running(session)
        if turn is None:
            return ROLE_TABLE
        return self.tables.get(turn.trigger.source, ROLE_TABLE)

    def label(self, requester: Caller) -> str:
        """Geçmişteki sözün başına yazılan ad (§8.1)."""
        person_id = requester.person_id
        return label(None if person_id is None else self.people.get(person_id))

    def recognizer(self) -> CallerSource | None:
        """Sesten konuşanı bulan kaynak; config'te konuşmacı tanıma yoksa `None`."""
        return None if self.matcher is None else recognized(self.matcher, self.people)

    def turn_recognizer(self) -> RequesterSource | None:
        """Turu isteyeni turun bütün sözlerinin sesinden bulan kaynak (§6)."""
        return None if self.matcher is None else recognized_turn(self.matcher, self.people)

    def caller(self, role: Role, person_id: str | None) -> Caller:
        """Kayıttaki rol ve kimlikten çağıran; kişisel cihazı profilden (replay, §14)."""
        person = None if person_id is None else self.people.get(person_id)
        return (
            Caller(role, person_id, has_personal_device=False)
            if person is None
            else caller_of(person)
        )

    def speech(
        self, microphone: Callable[[], AudioInput | None] = lambda: None
    ) -> tuple[FrameProcessor, TtsFactory, VADAnalyzer, BaseTurnAnalyzer]:
        """Config'teki STT ve TTS servislerinin istemcileri (§3); VAD ve sözün bitişini
        bulan model de STT servisinde. `microphone`, istemcinin bildirdiği mikrofondur."""
        stt, tts = self.config.stt, self.config.tts
        if stt is None or tts is None:
            raise ConfigError("a voice session needs both stt and tts in the config")

        def make_tts(language: Callable[[], str]) -> FrameProcessor:
            return ServiceTTS(tts.url, tts.voices, language)

        speaker = self.config.speaker
        return (
            ServiceSTT(
                stt.url,
                stt.language,
                None if speaker is None else ServiceSpeaker(speaker.url),
                record_dir=stt.record_dir,
                microphone=microphone,
            ),
            make_tts,
            ServiceVAD(stt.url),
            ServiceTurn(stt.url),
        )

    def wake(self) -> "Wake | None":
        """STT servisindeki wake word modelinin istemcisi; config'te yoksa her söz tur açar."""
        stt = self.config.stt
        if stt is None or stt.wake is None:
            return None
        return Wake(ServiceWake(stt.url, stt.wake.threshold), stt.wake.follow_up_s)

    def context(self, session: str, spec: ToolSpec[Any], caller: Caller) -> ToolCtx:
        person = None if caller.person_id is None else self.people.get(caller.person_id)
        return ToolCtx(
            self.notes,
            self.timers,
            self.recorder.clock,
            self.devices.get(session),
            self.weather,
            None if person is None else person.location,
            caller,
            self.defaults[spec.name],
        )


@dataclass(frozen=True)
class Wake:
    """Wake word (§6): sesi modele akıtan ve asistan sustuktan sonraki takip penceresi."""

    detector: FrameProcessor
    follow_up_s: float


@dataclass(frozen=True)
class Voice:
    """Sesli bir oturumun dış birimleri; hattı kuran seçer."""

    input: FrameProcessor
    stt: FrameProcessor
    tts: TtsFactory
    output: FrameProcessor
    vad: VADAnalyzer
    turn: BaseTurnAnalyzer  # sözün bittiğine karar veren (§5.4)
    # Sözün kime ait olduğu: konuşmacı tanıma (`Core.recognizer`) ya da hattı kuranın
    # kaynağı; `None` sözü cihazın kişisine verir, yazılı kanaldaki gibi (kişisel değilse
    # tanımsız).
    caller: CallerSource | None
    # Ses birimlerinin cihazı; çekirdeğin kendi makinesindeyse `LOCAL_DEVICE` (§10.1).
    device: DeviceId | None
    # Yoksa her söz tur açar (§5.1).
    wake: Wake | None = None
    # Turu isteyen, turun sözlerinin hepsinden (`Core.turn_recognizer`); yoksa ilk sözün
    # konuşanı.
    requester: RequesterSource | None = None


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
    core: Core,
    session: str,
    speaker: CallerSource,
    vad: VADAnalyzer | None,
    turn: BaseTurnAnalyzer | None,
    sound: ToolSound | None = None,
    follow_up_s: float | None = None,
    requester: RequesterSource | None = None,
    shown: Shown | None = None,
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
        quiet=sound is not None,
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
        capabilities=lambda: core.devices.capabilities(session),
        state=state,
        label=core.label,
        requester=requester,
    )
    start = (
        None
        if follow_up_s is None
        else [
            # Pipecat'in varsayılan başlangıç stratejileri, önlerinde uyanıklık şartı.
            WakeStart(lambda: gate.turn is not None, follow_up_s, hears=gate.hears),
            VADUserTurnStartStrategy(),
            TranscriptionUserTurnStartStrategy(),
        ]
    )
    tools = AuthorizedTools(
        core.registry,
        lambda: core.table(session),
        lambda spec, caller: core.context(session, spec, caller),
        confirmation,
        caller,
        TurnFlags,
        events,
        None if sound is None else sound.play,
        shown,
    )
    context = LLMContext(tools=tools.schema())
    llm = llm_service(
        endpoint,
        config.system_prompt,
        lambda: core.context_block.render(session, caller()),
        StepCap(config.loop.max_steps, config.loop.max_corrections),
        tools.malformed,
        session=context,
        # Yazılı hatta mesaj geldiği an istek de gider; ısıtma onu yalnızca bekletirdi.
        warm_on_speech=vad is not None,
    )
    tools.register(llm)
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=vad,
            # Açık verilmezse Pipecat Smart Turn'ü çekirdekte yükler (§18). Yazılı hatta söz
            # yoktur, mesaj tetikleyici kapısından gelir; bitişine karar verilecek bir şey yok.
            user_turn_strategies=(
                ExternalUserTurnStrategies()
                if turn is None
                else UserTurnStrategies(start=start, stop=[TurnEndToStt(turn_analyzer=turn)])
            ),
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
        # Pipecat'in varsayılanı 5 dk sessizlikte oturumu kapatır: bağlantı kopar, bağlam
        # sıfırlanır. Bağlamın ne zaman sıfırlanacağı açık bir karardır (§16.12).
        idle_timeout_secs=None,
    )
    return Session(worker, conversation.gate, conversation.confirmation, observers)


def voice_session(
    core: Core, session: str, voice: Voice, shown: Shown | None = None
) -> Session:
    requester = core.connect(session, voice.device)
    speaker = voice.caller or (lambda _: requester)
    # Tool bitince sözsüz ses (§8.8); yazılı oturumda ses yok.
    sound = ToolSound()
    wake = voice.wake
    follow_up_s = None if wake is None else wake.follow_up_s
    c = _conversation(
        core,
        session,
        speaker,
        voice.vad,
        voice.turn,
        sound,
        follow_up_s,
        voice.requester,
        shown,
    )
    pipeline = Pipeline(
        [
            voice.input,
            *([] if wake is None else [wake.detector]),
            voice.stt,
            c.gate,
            c.confirmation,
            SpeakerLabel(lambda frame: core.label(speaker(frame))),
            c.aggregators.user(),
            c.llm,
            voice.tts(c.language),
            sound,
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
    c = _conversation(core, session, lambda _: requester, None, None)
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
