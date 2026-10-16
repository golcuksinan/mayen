"""Tetikleyici kapısı (§5.1–§5.3) Pipecat hattında: turu başlatır, keser, bittiğini bildirir.

Her oturumun hattında bir kapı durur; bütün oturumlar aynı `Sessions` üzerinden tek bir
`Turns`'ü paylaşır. Kesme ve kuyruk kararı `core`'dadır; kapı kararı hatta uygular.

Kesme Pipecat'in kendi söz kesmesidir: süren model cevabı, ses ve tool işleri düşer. Bir
oturumda aynı anda tek tur sürer ve bekleyenler hattın dışında, `Turns`'te durur; bu yüzden
söz kesmenin düşürdüğü, yalnızca kesilen turun işleridir (§5.3: iptalin kapsamı tur).

Sesli tetikleyici sıraya alınamaz: duyulmaması gereken an kullanıcı susturulur ve söylenen
yeniden söylenir. Susturma Pipecat'in kullanıcı susturma stratejisiyle yapılır.
"""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable, Sequence

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    CancelFrame,
    EndFrame,
    Frame,
    FunctionCallCancelFrame,
    FunctionCallResultFrame,
    FunctionCallsStartedFrame,
    InterruptionFrame,
    LLMMessagesAppendFrame,
    LLMRunFrame,
    StartFrame,
    TranscriptionFrame,
    UserMuteStartedFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.turns.user_mute.base_user_mute_strategy import BaseUserMuteStrategy

from mayen.core.events import Recorder
from mayen.core.state import StateTracker
from mayen.core.turns import Interrupt, Start, Turn, Turns
from mayen.pipeline.events import UTTERANCE, SessionTranscript
from mayen.pipeline.speaker import score
from mayen.ports.events import EventKind, ref
from mayen.ports.tools import Caller, Role, Status
from mayen.ports.triggers import Fate, Priority, Trigger, TriggerSource, TurnId

# Segmentin konuşmacısı; hattı kuran bağlar: konuşmacı tanıma (`pipeline/speaker.py`) ya da
# cihazın kişisi. Onay kapısındaki `SpeakerSource` da bu kaynaktan okur.
type CallerSource = Callable[[TranscriptionFrame], Caller]

# Söz başladığında kimin konuştuğu henüz bilinmez; kesme kuralı onu sahip saymaz.
UNIDENTIFIED = Caller(Role.UNKNOWN, None, has_personal_device=False)

_TICK_S = 0.05


class Sessions:
    """Oturumların kapıları ve ortak `Turns`; kararları ilgili oturumun kapısına taşır."""

    def __init__(
        self,
        turns: Turns,
        voice: Priority,
        seen: Callable[[str, Caller], None] = lambda session, requester: None,
    ) -> None:
        self._turns = turns
        self._voice = voice  # sesli tetikleyicinin önceliği (§5.1)
        self._seen = seen  # tur kime aitse onun bu oturumda etkileşimde bulunduğu (§12)
        self._gates: dict[str, TriggerGate] = {}

    @property
    def voice(self) -> Priority:
        return self._voice

    def names(self) -> list[str]:
        """Hattı kurulmuş oturumlar, kuruluş sırasıyla."""
        return list(self._gates)

    def attach(self, gate: "TriggerGate") -> None:
        if gate.session in self._gates:
            raise ValueError(f"session {gate.session!r} already has a gate")
        self._gates[gate.session] = gate

    async def detach(self, session: str) -> None:
        """Oturumun hattı kapandı; turları düşer, yeri bekleyenlere geçer."""
        self._gates.pop(session, None)
        await self._apply(self._turns.drop(session), None)

    def running(self, session: str) -> Turn | None:
        """Oturumun süren turu; sahibi tanındıysa güncel hâliyle (`identify`)."""
        return self._turns.running(session)

    def hears(self, session: str) -> bool:
        return self._turns.hears(session, self._voice)

    def identify(self, session: str, requester: Caller) -> None:
        self._turns.identify(session, requester)
        self._seen(session, requester)

    async def submit(
        self, trigger: Trigger, received: Callable[[TurnId], object] = lambda turn_id: None
    ) -> None:
        """`received`, tetikleyicinin turu (başlamış ya da sırada) belli olunca ve tur hatta
        yürümeden önce çağrılır: turu açan söz transkripte cevabından önce girer (§11)."""
        if trigger.session not in self._gates:
            # Hedef cihazın seçimi (§12) bu katmanın işi değil; hatsız oturum bir hatadır.
            raise ValueError(f"no gate for session {trigger.session!r}")
        actions = self._turns.submit(trigger)
        turns = [a.turn for a in actions] + self._turns.waiting(trigger.session)
        received(next(t for t in turns if t.trigger is trigger).id)
        await self._apply(actions, trigger)

    async def finished(self, turn_id: TurnId) -> None:
        await self._apply(self._turns.finished(turn_id), None)

    async def _apply(self, actions: Sequence[Interrupt | Start], fresh: Trigger | None) -> None:
        # Söz başladığında Pipecat kesmeyi zaten yapmıştır; yalnızca akıbet uygulanır.
        by_voice = fresh is not None and fresh.source is TriggerSource.VOICE
        for action in actions:
            gate = self._gates[action.turn.trigger.session]
            if isinstance(action, Interrupt):
                await gate.interrupt(action.turn, action.fate, already_cut=by_voice)
            else:
                self._seen(gate.session, action.turn.trigger.requester)
                await gate.start(action.turn, fresh=action.turn.trigger is fresh)


class TriggerGate(FrameProcessor):
    """Bir oturumun turunu hatta yürütür; STT ile kullanıcı toplayıcısının arasında durur.

    Tur, oturum `settle_s` boyunca sessiz kalınca biter: kimse konuşmuyor, model cevap
    yazmıyor, açık tool çağrısı yok, onay beklenmiyor ve beklenen bir cevap yok. Beklenen
    cevap `response_timeout_s` içinde başlamazsa tur sessizce kapanır (§5.4).

    Duyulan her segment transkripte buradan girer (§6: transkript her zaman kaydedilir);
    duyulmaması gereken an söylenen de, ama olayında `muted` ile: o söz modele gitmedi.
    """

    def __init__(
        self,
        session: str,
        sessions: Sessions,
        caller: CallerSource,
        recorder: Recorder,
        transcript: SessionTranscript,
        *,
        settle_s: float,
        response_timeout_s: float,
        holds: Sequence[Callable[[], bool]] = (),
        drops: Sequence[Callable[[], Awaitable[None]]] = (),
        device_person: Callable[[], str | None] = lambda: None,
        state: StateTracker | None = None,
        label: Callable[[Caller], str] | None = None,
    ) -> None:
        super().__init__()
        self.session = session
        self._sessions = sessions
        self._caller = caller
        self._recorder = recorder
        self._transcript = transcript
        self._started_at = 0.0
        self._settle_s = settle_s
        self._response_timeout_s = response_timeout_s
        self._holds = holds  # turu açık tutan başka durumlar; onay beklemek gibi (§5.4)
        self._drops = drops  # kesilen turla düşen başka işler; bekleyen onay planı gibi (§5.3)
        # Oturumun cihazı kimin kişisel cihazı; kimse istemeden açılan turu o dinler (§8.6).
        self._device_person = device_person
        # Oturumun durumu (§5.4): kapı turu, sözü ve sesi bildirir.
        self._state = state or StateTracker(lambda _, __: None)
        # Yazılı sözün başına konuşanın adı (§8.1); sesli sözünkini `SpeakerLabel` yazar.
        self._label = label
        self._turn: Turn | None = None
        self._identified = True
        self._user_speaking = False
        self._bot_speaking = False
        self._responding = False
        self._open_calls: set[str] = set()
        self._awaiting_since: float | None = None
        self._answered = False  # son söz başladığından beri model cevap verdi mi
        self._quiet_since: float | None = None
        self._unanswered = False
        self._ticker: asyncio.Task[None] | None = None
        sessions.attach(self)

    @property
    def turn(self) -> Turn | None:
        return self._turn

    def hears(self) -> bool:
        return self._sessions.hears(self.session)

    # --- model cevabı: kullanıcı toplayıcısının olaylarından, hattı kuran bağlar ---

    def response_started(self) -> None:
        self._responding = True
        self._answered = True
        self._awaiting_since = None

    def response_stopped(self) -> None:
        self._responding = False

    # --- Sessions'ın kararları ---

    async def start(self, turn: Turn, *, fresh: bool) -> None:
        self._turn = turn
        self._quiet_since = None
        self._unanswered = False
        source = turn.trigger.source
        self._identified = source is not TriggerSource.VOICE or not fresh
        self._started_at = self._recorder.clock.monotonic()
        requester = turn.trigger.requester
        self._emit(
            EventKind.TURN_STARTED,
            turn,
            {
                "source": source.value,
                "priority": turn.trigger.priority.value,
                "fresh": fresh,
                # Sesli turun sahibi ilk segmentte tanınır; o segmentin konuşmacısıdır.
                "requester": {"role": requester.role.value, "person_id": requester.person_id},
                "device_person": self._device_person(),
            },
            related=turn.trigger.records,
        )
        self._state.turn(source)
        if source is TriggerSource.VOICE:
            if fresh:
                return  # söz zaten hatta; cevabı Pipecat tetikler
            # Baştan başlayan sesli tur: söz bağlamda duruyor, model yeniden çalışır.
            await self._push_run(LLMRunFrame())
        elif source is TriggerSource.TEXT:
            content = turn.trigger.content
            if self._label is not None:
                content = f"{self._label(requester)}: {content}"
            await self._push_run(
                LLMMessagesAppendFrame(
                    messages=[{"role": "user", "content": content}], run_llm=True
                )
            )
        else:
            # Sistem cümle kurmaz: olay, modele etiketli bir mesaj olarak gider (§2.1).
            message: dict[str, object] = {
                "trigger": source.value,
                "priority": turn.trigger.priority.value,
                "content": turn.trigger.content,
            }
            if turn.trigger.details:
                message["details"] = dict(turn.trigger.details)
            content = json.dumps(message, ensure_ascii=False)
            await self._push_run(
                LLMMessagesAppendFrame(
                    messages=[{"role": "developer", "content": content}], run_llm=True
                )
            )

    async def interrupt(self, turn: Turn, fate: Fate, *, already_cut: bool) -> None:
        self._emit(
            EventKind.TURN_INTERRUPTED,
            turn,
            {"fate": fate.value},
            duration_s=self._elapsed(turn),
            status=Status.CANCELLED,
        )
        self._turn = None
        self._state.turn(None)
        self._responding = False
        self._awaiting_since = None
        self._open_calls.clear()
        for drop in self._drops:
            await drop()
        if not already_cut:
            await self.broadcast_frame(InterruptionFrame)
        if fate is Fate.CANCEL:
            note = json.dumps({"interrupted": turn.trigger.source.value})
            await self.push_frame(
                LLMMessagesAppendFrame(
                    messages=[{"role": "developer", "content": note}], run_llm=False
                )
            )

    # --- hat ---

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, UserStartedSpeakingFrame):
            self._user_speaking = True
            self._state.listening(True)
            self._answered = False
            self._quiet_since = None
            voice_turn = (
                self._turn is not None and self._turn.trigger.source is TriggerSource.VOICE
            )
            # Susturma kareyle birlikte değerlendirilir; geç kalan bir söz tetikleyici olmaz.
            if not voice_turn and self.hears():
                trigger = Trigger(
                    self.session, self._sessions.voice, TriggerSource.VOICE, "", UNIDENTIFIED
                )
                await self._sessions.submit(trigger)
        elif isinstance(frame, UserStoppedSpeakingFrame | UserMuteStartedFrame):
            # Susturma sözün ortasında başlarsa sözün bittiği hiç duyulmaz. Cevap sözün
            # bittiği duyulmadan gelmiş olabilir: onay kapısının yuttuğu söz, toplayıcıya
            # metin ulaşmadığı için ancak onun zaman aşımıyla biter.
            if self._user_speaking and not self._answered:
                self._awaiting_since = time.monotonic()
            self._user_speaking = False
            self._state.listening(False)
        elif isinstance(frame, TranscriptionFrame):
            self._heard(frame)
            if not self._identified:
                self._identified = True
                self._sessions.identify(self.session, self._caller(frame))
        elif isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
            self._state.speaking(True)
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            self._state.speaking(False)
        elif isinstance(frame, FunctionCallsStartedFrame):
            self._open_calls |= {c.tool_call_id for c in frame.function_calls}
        elif isinstance(frame, FunctionCallResultFrame | FunctionCallCancelFrame):
            self._open_calls.discard(frame.tool_call_id)
        await self.push_frame(frame, direction)
        if isinstance(frame, StartFrame):
            self._ticker = self.create_task(self._watch())
        elif isinstance(frame, EndFrame | CancelFrame) and self._ticker is not None:
            await self.cancel_task(self._ticker)
            self._ticker = None

    def _heard(self, frame: TranscriptionFrame) -> None:
        utterance = self._transcript.heard(self._caller(frame), frame.text)
        record = ref("utterance", utterance.id)
        frame.metadata[UTTERANCE] = record
        self._recorder.emit(
            EventKind.STT_SEGMENT,
            __name__,
            {
                "language": None if frame.language is None else str(frame.language),
                "finalized": frame.finalized,
                "muted": not self.hears(),
                # Konuşmacı tanımanın en yüksek puanı (§6); eşik config'te, karar çekirdekte.
                "speaker_score": score(frame),
            },
            session=self.session,
            turn_id=None if self._turn is None else self._turn.id,
            status=Status.OK,
            related=[record],
        )

    def _elapsed(self, turn: Turn) -> float | None:
        # Kapı yalnızca kendi yürüttüğü turun başlangıcını bilir.
        if self._turn is None or self._turn.id != turn.id:
            return None
        return self._recorder.clock.monotonic() - self._started_at

    def _emit(
        self,
        kind: EventKind,
        turn: Turn,
        body: dict[str, object],
        *,
        duration_s: float | None = None,
        status: Status | None = None,
        related: Sequence[str] = (),
    ) -> None:
        self._recorder.emit(
            kind,
            __name__,
            body,
            session=self.session,
            turn_id=turn.id,
            duration_s=duration_s,
            status=status,
            related=related,
        )

    async def _push_run(self, frame: Frame) -> None:
        self._awaiting_since = time.monotonic()
        await self.push_frame(frame)

    def _quiet(self, now: float) -> bool:
        awaiting = self._awaiting_since
        if awaiting is not None and now - awaiting >= self._response_timeout_s:
            # Cevap gelmedi; tur sessizce kapanacak, sebebi bitiş olayının gövdesindedir.
            self._unanswered = True
            self._awaiting_since = awaiting = None
        return not (
            self._user_speaking
            or self._bot_speaking
            or self._responding
            or self._open_calls
            or awaiting is not None
            or any(hold() for hold in self._holds)
        )

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(_TICK_S)
            turn = self._turn
            now = time.monotonic()
            if turn is None or not self._quiet(now):
                self._quiet_since = None
                continue
            if self._quiet_since is None:
                self._quiet_since = now
            elif now - self._quiet_since >= self._settle_s:
                self._emit(
                    EventKind.TURN_FINISHED,
                    turn,
                    {"unanswered": self._unanswered},
                    duration_s=self._elapsed(turn),
                    status=Status.OK,
                )
                self._turn = None
                self._state.turn(None)
                self._quiet_since = None
                await self._sessions.finished(turn.id)


class HeardOnly(BaseUserMuteStrategy):
    """Duyulmaması gereken an kullanıcıyı susturur (§5.3; sesli tetikleyici sıraya girmez)."""

    def __init__(self, gate: TriggerGate) -> None:
        super().__init__()  # type: ignore[no-untyped-call]  # Pipecat'te tipsiz
        self._gate = gate

    async def process_frame(self, frame: Frame) -> bool:
        await super().process_frame(frame)
        return not self._gate.hears()
