"""Bir rolün Pipecat model servisi, model deposundaki ayarlarla (§8.9, §8.10).

Adım tavanı (§8.8) da buradadır: döngüyü Pipecat yürütür ve her adım bir istektir. Tavana
ulaşılan istek tool'suz gider, model eldeki sonuçlarla cevap verir (§9.1).

Bağlam bloğu (§8.3) ayrı bir işlemci olarak durmaz, servisin istek kurduğu yerdedir: Pipecat
tool sonucundan sonraki çağrıyı hattın aşağısından tetikler ve modelin üstündeki bir işlemci o
çağrıyı görmez. İstekte bağlamın bir kopyası gider; tool çağrıları ve toplayıcılar asıl
bağlamı kullanmaya devam eder, blok geçmişe hiç yazılmaz.

Isıtma (§8.3) da buradadır: oturumun öneki ve geçmişi, ilk istekten önce sunucuya işletilir.
"""

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from pipecat.frames.frames import Frame, StartFrame, UserStartedSpeakingFrame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.openai.llm import OpenAILLMService

from mayen.ports.models import NO_KEY, Endpoint

log = logging.getLogger(__name__)

# Turu açan mesajın rolleri: kişinin sözü ya da yazısı, ya da tetikleyicinin etiketli mesajı.
_TURN_OPENERS = ("user", "developer")


def _turn_start(messages: list[Any]) -> int:
    """Güncel turu açan son mesajın yeri; yoksa listenin sonu."""
    return next(
        (
            i
            for i in range(len(messages) - 1, -1, -1)
            if isinstance(messages[i], dict) and messages[i].get("role") in _TURN_OPENERS
        ),
        len(messages),
    )


@dataclass(frozen=True)
class Steps:
    taken: int  # en az bir geçerli çağrı taşıyan cevaplar
    corrections: int  # bütün çağrıları bozuk cevaplar; adım harcamaz (§9.1)


def count_steps(messages: list[Any], malformed: Callable[[str], bool]) -> Steps:
    """Güncel turda modelin çağrı taşıyan cevapları, geçmişten sayılır."""
    taken = corrections = 0
    for message in messages[_turn_start(messages) :]:
        calls = message.get("tool_calls") if isinstance(message, dict) else None
        if not calls:
            continue
        if all(malformed(call["id"]) for call in calls):
            corrections += 1
        else:
            taken += 1
    return Steps(taken, corrections)


@dataclass(frozen=True)
class StepCap:
    max_steps: int
    max_corrections: int

    def reached(self, steps: Steps) -> bool:
        return steps.taken >= self.max_steps or steps.corrections > self.max_corrections


def with_block(messages: list[Any], block: str) -> list[Any]:
    """Blok güncel turun önüne, geçmişin arkasına (§8.3): son tur açan mesajın hemen önü.

    Tool çağrısı ve sonucu gibi tur içinde sonradan gelenler bloğun arkasında kalır; tur
    sürerken blok aynı yerde durur ve önek tur içinde değişmez.
    """
    at = _turn_start(messages)
    # Kişinin söylediği değil sistemin bildiği: kullanıcı mesajı olarak gitmez (§18 madde 7).
    return [*messages[:at], {"role": "developer", "content": block}, *messages[at:]]


class ContextualLLMService(OpenAILLMService):
    """Her isteğe o anın bağlam bloğunu ekleyen model servisi."""

    def __init__(
        self,
        *,
        block: Callable[[], str],
        cap: StepCap,
        malformed: Callable[[str], bool],
        session: LLMContext | None = None,
        warm_on_speech: bool = False,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(**kwargs)
        self._block = block
        self._cap = cap
        self._malformed = malformed
        self._session = session
        self._warm_on_speech = warm_on_speech
        self._warming = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if self._session is None or self._warming:
            return
        if isinstance(frame, StartFrame) or (
            self._warm_on_speech and isinstance(frame, UserStartedSpeakingFrame)
        ):
            self._warming = True
            self.create_task(self.warm(self._session))

    async def warm(self, context: LLMContext) -> None:
        """Sabit önek ve geçmiş, istekten önce sunucuya işletilir (§8.3); cevap atılır."""
        started = time.perf_counter()
        try:
            await self.run_inference(
                LLMContext(messages=list(context.messages), tools=context.tools), max_tokens=1
            )
            log.debug("warmed in %.2fs", time.perf_counter() - started)
        except Exception as e:  # ısıtılamayan önek asıl istekte işlenir
            log.warning("warm-up failed: %s", e)
        finally:
            self._warming = False

    async def get_chat_completions(
        self, context: LLMContext
    ) -> AsyncStream[ChatCompletionChunk]:
        history = list(context.messages)
        messages = with_block(history, self._block())
        tool_choice = context.tool_choice
        steps = count_steps(history, self._malformed)
        if self._cap.reached(steps):
            log.warning("step cap reached: %d steps, %d corrections", *vars(steps).values())
            # Sistem cümle kurmaz: tavan modele etiketli bir mesajla bildirilir (§2.1).
            note = {"step_cap": {"steps": steps.taken, "corrections": steps.corrections}}
            messages.append({"role": "developer", "content": json.dumps(note)})
            tool_choice = "none"
        copy = LLMContext(messages=messages, tools=context.tools, tool_choice=tool_choice)
        return await super().get_chat_completions(copy)


def llm_service(
    endpoint: Endpoint,
    system_instruction: str,
    block: Callable[[], str],
    cap: StepCap,
    malformed: Callable[[str], bool],
    session: LLMContext | None = None,
    warm_on_speech: bool = False,
) -> ContextualLLMService:
    """Ayarlar gövdeyle her istekte gider; sunucunun varsayılanı rol farkını bilmez.

    `session` verilirse oturum açılınca, `warm_on_speech` ile söz başlayınca da ısıtılır (§8.3).
    """
    service = ContextualLLMService(
        block=block,
        cap=cap,
        malformed=malformed,
        session=session,
        warm_on_speech=warm_on_speech,
        base_url=endpoint.base_url,
        api_key=endpoint.api_key.get_secret_value() if endpoint.api_key else NO_KEY,
        settings=OpenAILLMService.Settings(
            model=endpoint.model,
            system_instruction=system_instruction,
            extra={"extra_body": dict(endpoint.body)},
        ),
        # Yan etkili çağrılar sırayla (§9.3); READ'lerin paralelliği izin, zorunluluk değil.
        run_in_parallel=False,
    )
    # Şablon ortadaki geliştirici mesajını reddediyorsa Pipecat onu kullanıcı mesajına çevirir.
    service.supports_developer_role = endpoint.developer_role
    return service
