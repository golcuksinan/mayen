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
import logging
import time
from collections.abc import Callable, Sequence

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

from mayen.core.turns import Interrupt, Start, Turn, Turns
from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import Fate, Priority, Trigger, TriggerSource, TurnId

log = logging.getLogger(__name__)

# İlk segmentin konuşmacısı; hattı kuran bağlar. Konuşmacı tanıma gelince değişen yalnızca
# bu kaynaktır (onay kapısındaki `SpeakerSource` gibi).
type CallerSource = Callable[[TranscriptionFrame], Caller]

# Söz başladığında kimin konuştuğu henüz bilinmez; kesme kuralı onu sahip saymaz.
UNIDENTIFIED = Caller(Role.UNKNOWN, None, has_personal_device=False)

_TICK_S = 0.05


class Sessions:
    """Oturumların kapıları ve ortak `Turns`; kararları ilgili oturumun kapısına taşır."""

    def __init__(self, turns: Turns, voice: Priority) -> None:
        self._turns = turns
        self._voice = voice  # sesli tetikleyicinin önceliği (§5.1)
        self._gates: dict[str, TriggerGate] = {}

    @property
    def voice(self) -> Priority:
        return self._voice

    def attach(self, gate: "TriggerGate") -> None:
        if gate.session in self._gates:
            raise ValueError(f"session {gate.session!r} already has a gate")
        self._gates[gate.session] = gate

    def hears(self, session: str) -> bool:
        return self._turns.hears(session, self._voice)

    def identify(self, session: str, requester: Caller) -> None:
        self._turns.identify(session, requester)

    async def submit(self, trigger: Trigger) -> None:
        if trigger.session not in self._gates:
            # Hedef cihazın seçimi (§12) bu katmanın işi değil; hatsız oturum bir hatadır.
            raise ValueError(f"no gate for session {trigger.session!r}")
        await self._apply(self._turns.submit(trigger), trigger)

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
                await gate.start(action.turn, fresh=action.turn.trigger is fresh)


class TriggerGate(FrameProcessor):
    """Bir oturumun turunu hatta yürütür; STT ile kullanıcı toplayıcısının arasında durur.

    Tur, oturum `settle_s` boyunca sessiz kalınca biter: kimse konuşmuyor, model cevap
    yazmıyor, açık tool çağrısı yok, onay beklenmiyor ve beklenen bir cevap yok. Beklenen
    cevap `response_timeout_s` içinde başlamazsa tur sessizce kapanır (§5.4).
    """

    def __init__(
        self,
        session: str,
        sessions: Sessions,
        caller: CallerSource,
        *,
        settle_s: float,
        response_timeout_s: float,
        holds: Sequence[Callable[[], bool]] = (),
    ) -> None:
        super().__init__()
        self.session = session
        self._sessions = sessions
        self._caller = caller
        self._settle_s = settle_s
        self._response_timeout_s = response_timeout_s
        self._holds = holds  # turu açık tutan başka durumlar; onay beklemek gibi (§5.4)
        self._turn: Turn | None = None
        self._identified = True
        self._user_speaking = False
        self._bot_speaking = False
        self._responding = False
        self._open_calls: set[str] = set()
        self._awaiting_since: float | None = None
        self._quiet_since: float | None = None
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
        self._awaiting_since = None

    def response_stopped(self) -> None:
        self._responding = False

    # --- Sessions'ın kararları ---

    async def start(self, turn: Turn, *, fresh: bool) -> None:
        self._turn = turn
        self._quiet_since = None
        source = turn.trigger.source
        self._identified = source is not TriggerSource.VOICE or not fresh
        log.info("turn %s started: %s %s", turn.id, source, turn.trigger.priority)
        if source is TriggerSource.VOICE:
            if fresh:
                return  # söz zaten hatta; cevabı Pipecat tetikler
            # Baştan başlayan sesli tur: söz bağlamda duruyor, model yeniden çalışır.
            await self._push_run(LLMRunFrame())
        elif source is TriggerSource.TEXT:
            await self._push_run(
                LLMMessagesAppendFrame(
                    messages=[{"role": "user", "content": turn.trigger.content}], run_llm=True
                )
            )
        else:
            # Sistem cümle kurmaz: olay, modele etiketli bir mesaj olarak gider (§2.1).
            content = json.dumps(
                {
                    "trigger": source.value,
                    "priority": turn.trigger.priority.value,
                    "content": turn.trigger.content,
                },
                ensure_ascii=False,
            )
            await self._push_run(
                LLMMessagesAppendFrame(
                    messages=[{"role": "developer", "content": content}], run_llm=True
                )
            )

    async def interrupt(self, turn: Turn, fate: Fate, *, already_cut: bool) -> None:
        log.info("turn %s interrupted: %s", turn.id, fate)
        self._turn = None
        self._responding = False
        self._awaiting_since = None
        self._open_calls.clear()
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
            # Susturma sözün ortasında başlarsa sözün bittiği hiç duyulmaz.
            if self._user_speaking:
                self._awaiting_since = time.monotonic()
            self._user_speaking = False
        elif isinstance(frame, TranscriptionFrame) and not self._identified:
            self._identified = True
            self._sessions.identify(self.session, self._caller(frame))
        elif isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
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

    async def _push_run(self, frame: Frame) -> None:
        self._awaiting_since = time.monotonic()
        await self.push_frame(frame)

    def _quiet(self, now: float) -> bool:
        awaiting = self._awaiting_since
        if awaiting is not None and now - awaiting >= self._response_timeout_s:
            log.info("turn %s: no response, closing", self._turn and self._turn.id)
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
                self._turn = None
                self._quiet_since = None
                log.info("turn %s finished", turn.id)
                await self._sessions.finished(turn.id)


class HeardOnly(BaseUserMuteStrategy):
    """Duyulmaması gereken an kullanıcıyı susturur (§5.3; sesli tetikleyici sıraya girmez)."""

    def __init__(self, gate: TriggerGate) -> None:
        super().__init__()  # type: ignore[no-untyped-call]  # Pipecat'te tipsiz
        self._gate = gate

    async def process_frame(self, frame: Frame) -> bool:
        await super().process_frame(frame)
        return not self._gate.hears()
