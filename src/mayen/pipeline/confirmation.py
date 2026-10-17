"""Onay kapısı (§10.5) Pipecat hattında: planı tutar, soruyu okutur, cevabı yönlendirir.

Kapı STT ile kullanıcı toplayıcısının arasında durur. Plan beklerken gelen metin ana modele
gitmez, yalnızca çözümleyiciye gider (§5.4: kapalı durum). Kuralların kendisi `core`'dadır.

Bir cevaptaki onaylı çağrılar tek planda toplanır (§9.3). Pipecat önce cevaptaki bütün
çağrıları duyurur, sonra her biri için bir sonuç ya da iptal yayımlar; soru, duyurulan son
çağrı da kapanınca yazılır. Böylece planın tamamlandığı, çağrıların sırası ya da paralel
çalışıp çalışmadığından bağımsız olarak bilinir.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from pipecat.frames.frames import (
    Frame,
    FunctionCallCancelFrame,
    FunctionCallResultFrame,
    FunctionCallsStartedFrame,
    InterimTranscriptionFrame,
    LLMMessagesAppendFrame,
    TranscriptionFrame,
    TTSSpeakFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.turns.empty_user_turn import EmptyUserTurnConfig
from pydantic import BaseModel

from mayen.core.confirmation import (
    Entry,
    Plan,
    Step,
    missing_values,
    next_step,
    resolve_answer,
)
from mayen.pipeline.events import UTTERANCE, SessionEvents
from mayen.pipeline.tools import to_model
from mayen.ports.confirmation import (
    Answer,
    AnswerResolver,
    Outcome,
    PlannedCall,
    QuestionWriter,
)
from mayen.ports.events import EventKind
from mayen.ports.tools import Caller, Confirmation, Status, ToolResult, ToolSpec

log = logging.getLogger(__name__)

# Segmenti kimin söylediği; hattı kuran bağlar. Konuşmacı tanıma geldiğinde değişen
# yalnızca bu kaynaktır, kapı ve kural değişmez (§10.5 adım 4).
type SpeakerSource = Callable[[TranscriptionFrame], str | None]

# Planın kapanışı olay başlığında hangi durumla görünür (§5.5).
OUTCOME_STATUS = {
    Outcome.CONFIRMED: Status.OK,
    Outcome.REJECTED: Status.DENIED,
    Outcome.TIMED_OUT: Status.TIMEOUT,
    Outcome.CANCELLED: Status.CANCELLED,
    Outcome.ERROR: Status.ERROR,
}


class ConfirmationGateProcessor(FrameProcessor):
    def __init__(
        self,
        writer: QuestionWriter,
        resolver: AnswerResolver,
        timeout_s: float,
        speaker: SpeakerSource,
        events: SessionEvents,
        awaiting: Callable[[bool], None] = lambda _: None,
    ) -> None:
        super().__init__()
        self._writer = writer
        self._resolver = resolver
        self._timeout_s = timeout_s
        self._speaker = speaker
        self._events = events
        self._awaiting = awaiting  # oturumun durumuna bildirilir (§5.4)
        self._opened_at: float | None = None
        self._plan: Plan | None = None
        self._open_calls: set[str] = set()
        self._asking: asyncio.Task[None] | None = None
        self._timer: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    @property
    def awaiting(self) -> bool:
        return self._plan is not None

    async def request(
        self,
        spec: ToolSpec[Any],
        args: BaseModel,
        kind: Confirmation,
        execute: Callable[[], Awaitable[ToolResult]],
        requester: Caller,
    ) -> None:
        call = PlannedCall(spec.name, spec.description, args.model_dump(mode="json"))
        if self._plan is not None and (self._asking is not None or self._plan.question):
            # Soru yazılmaya başladıysa plan kapanmıştır; sonradan gelen çağrı ona eklenmez,
            # yoksa kullanıcı sorulmamış bir şeyi onaylamış olurdu.
            await self._report(
                [call], Outcome.CANCELLED, speak=False, reason="another plan is awaiting"
            )
            return
        if self._plan is None:
            # Önce durum, sonra cümle (§5.4).
            self._plan = Plan(requester)
            self._opened_at = self._events.monotonic()
            self._awaiting(True)
        self._plan.entries.append(Entry(call, kind, execute))

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, FunctionCallsStartedFrame):
            self._open_calls |= {c.tool_call_id for c in frame.function_calls}
        elif isinstance(frame, FunctionCallResultFrame | FunctionCallCancelFrame):
            self._open_calls.discard(frame.tool_call_id)
            plan = self._plan
            if not self._open_calls and plan and not plan.question and self._asking is None:
                self._asking = self.create_task(self._ask(plan))
        elif self._plan is not None and isinstance(frame, InterimTranscriptionFrame):
            return
        elif self._plan is not None and isinstance(frame, TranscriptionFrame):
            self.answer(Answer(frame.text, self._speaker(frame), frame.metadata.get(UTTERANCE)))
            return
        await self.push_frame(frame, direction)

    def answer(self, answer: Answer) -> None:
        """Onay beklenirken gelen tek segment; yalnızca çözümleyiciye gider (§5.4).

        Sesli segment hattan gelir; yazılı kanalın mesajı tetikleyiciye dönüşmeden buraya.
        """
        if self._plan is None:
            log.warning("answer without an awaiting plan dropped")
            return
        if answer.record is not None:
            self._plan.answers.append(answer.record)
        self.create_task(self._answer(self._plan, answer))

    async def drop(self) -> None:
        """Planın turu kesildi: plan iptal olur ve konuşulmaz (§5.3: iptalin kapsamı tur).

        Söz kesme bu değildir: soru okunurken söze girilirse plan yaşar (§5.4).
        """
        async with self._lock:
            asking = self._asking
            if self._plan is not None:
                await self._finish(
                    self._plan, Outcome.CANCELLED, speak=False, reason="turn interrupted"
                )
            if asking is not None:
                await self.cancel_task(asking)  # yazılmakta olan soru düşen plana aittir

    async def _ask(self, plan: Plan) -> None:
        if plan.kind is Confirmation.IDENTITY:
            # Kişisel cihaza giden kanal yok; kimlik onayı alınamıyorsa sonuç reddir (§10.3).
            await self._finish(
                plan, Outcome.REJECTED, reason="identity confirmation unavailable"
            )
            return
        try:
            for _ in range(2):
                question = await self._writer.write(plan.calls)
                missing = missing_values(plan.calls, question)
                # Loga içerik girmez (§14): eksik değerlerin kendisi değil sayısı.
                log.info("confirmation question written, %d values missing", len(missing))
                if not missing:
                    plan.question = question
                    await self._read(plan)
                    return
        except Exception as e:
            await self._finish(plan, Outcome.ERROR, error=str(e))
            return
        # İki denemede de cümle planı taşımadı: sesli onay yapılmaz, kimlik onayına geçilir
        # (§10.5 adım 3); o da alınamıyor.
        await self._finish(
            plan, Outcome.REJECTED, reason="the question could not carry the plan"
        )

    async def _read(self, plan: Plan) -> None:
        await self.push_frame(TTSSpeakFrame(plan.question, append_to_context=True))
        if self._timer:
            self._timer.cancel()
        self._timer = self.create_task(self._time_out(plan))

    async def _time_out(self, plan: Plan) -> None:
        await asyncio.sleep(self._timeout_s)
        async with self._lock:
            if self._plan is plan:
                # Zaman aşımı reddir ve konuşulmaz: karşıda kimse yok (§5.4, §10.5).
                await self._finish(plan, Outcome.TIMED_OUT, speak=False)

    async def _answer(self, plan: Plan, answer: Answer) -> None:
        async with self._lock:
            if self._plan is not plan:
                log.warning("segment after the plan closed dropped")
                return
            if not plan.question:
                # Soru okunmadan gelen söz cevap sayılamaz: sorulmamış bir şeye verilmiştir.
                log.warning("segment before the question dropped")
                return
            try:
                resolution = await resolve_answer(plan, answer, self._resolver)
            except Exception as e:  # kısıt dışı cevap belirsiz değil, hatadır (§10.5 adım 4)
                await self._finish(plan, Outcome.ERROR, error=str(e))
                return
            log.info("confirmation answer resolved: %s", resolution)
            step = next_step(plan, resolution)
            if plan.asked_again and step is not Step.ASK_AGAIN:
                # Tekrar sorusu henüz okunuyor ya da sırada olabilir: cevap ondan önce gelmiş
                # bir sözün devamıdır. Kesilmezse soru, iş bittikten sonra okunurdu.
                await self.broadcast_interruption()
            match step:
                case Step.EXECUTE:
                    # Yan etkili çağrılar sırayla çalışır (§9.3).
                    results = [to_model(await e.execute()) for e in plan.entries]
                    await self._finish(plan, Outcome.CONFIRMED, results=results)
                case Step.REJECT:
                    await self._finish(plan, Outcome.REJECTED)
                case Step.ASK_AGAIN:
                    plan.asked_again = True
                    await self._read(plan)
                case Step.CANCEL:
                    await self._finish(plan, Outcome.CANCELLED, reason="unclear twice")

    async def _finish(
        self,
        plan: Plan,
        outcome: Outcome,
        *,
        results: list[dict[str, Any]] | None = None,
        speak: bool = True,
        **detail: str,
    ) -> None:
        if self._timer and self._timer is not asyncio.current_task():
            self._timer.cancel()
        self._timer = None
        self._asking = None
        self._plan = None
        self._awaiting(False)
        opened, self._opened_at = self._opened_at, None
        duration_s = None if opened is None else self._events.monotonic() - opened
        await self._report(
            plan.calls,
            outcome,
            results=results,
            speak=speak,
            duration_s=duration_s,
            answers=plan.answers,
            **detail,
        )

    async def _report(
        self,
        calls: list[PlannedCall],
        outcome: Outcome,
        *,
        results: list[dict[str, Any]] | None = None,
        speak: bool = True,
        duration_s: float | None = None,
        answers: Sequence[str] = (),
        **detail: str,
    ) -> None:
        """Planın sonucu modele bir geliştirici mesajı olarak eklenir; çağrının sonucu
        zaten "onay bekleniyor" diye dönmüştü. Olay cevap olan sözlere bağlanır: onlar
        modele gitmedi."""
        listed = [{"tool": c.name, "arguments": dict(c.arguments)} for c in calls]
        if results is not None:
            for item, result in zip(listed, results, strict=True):
                item["result"] = result
        report = {"confirmation": outcome.value, "calls": listed, **detail}
        self._events.emit(
            EventKind.CONFIRMATION_CLOSED,
            __name__,
            report,
            duration_s=duration_s,
            status=OUTCOME_STATUS[outcome],
            related=answers,
        )
        content = json.dumps(report, ensure_ascii=False)
        await self.push_frame(
            LLMMessagesAppendFrame(
                messages=[{"role": "developer", "content": content}], run_llm=speak
            )
        )


class NoRecoveryWhileAwaiting(EmptyUserTurnConfig):
    """Pipecat'in boş tur kurtarması onay beklenirken çalışmaz (§5.4: kapalı durum).

    Kapı onay beklerken gelen metni yutar; Pipecat turu boş görür ve kendi kurtarmasıyla ana
    modeli çalıştırırdı, model de onay sırasında konuşurdu. Kurtarma istemi her turda bu
    ayardan okunur: onay beklenirken istem yok görünür, dışında Pipecat'in varsayılanıdır.
    """

    def __init__(self, gate: ConfirmationGateProcessor) -> None:
        self._gate = gate
        super().__init__()

    @property
    def interrupted_prompt(self) -> str | None:
        return None if self._gate.awaiting else self._interrupted

    @interrupted_prompt.setter
    def interrupted_prompt(self, value: str | None) -> None:
        self._interrupted = value

    @property
    def idle_prompt(self) -> str | None:
        return None if self._gate.awaiting else self._idle

    @idle_prompt.setter
    def idle_prompt(self, value: str | None) -> None:
        self._idle = value
