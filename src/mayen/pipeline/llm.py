"""Bir rolün Pipecat model servisi, model deposundaki ayarlarla (§8.9, §8.10).

Bağlam bloğu (§8.3) ayrı bir işlemci olarak durmaz, servisin istek kurduğu yerdedir: Pipecat
tool sonucundan sonraki çağrıyı hattın aşağısından tetikler ve modelin üstündeki bir işlemci o
çağrıyı görmez. İstekte bağlamın bir kopyası gider; tool çağrıları ve toplayıcılar asıl
bağlamı kullanmaya devam eder, blok geçmişe hiç yazılmaz.
"""

from collections.abc import Callable
from typing import Any

from openai import AsyncStream
from openai.types.chat import ChatCompletionChunk
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.openai.llm import OpenAILLMService

from mayen.ports.models import NO_KEY, Endpoint

# Turu açan mesajın rolleri: kişinin sözü ya da yazısı, ya da tetikleyicinin etiketli mesajı.
_TURN_OPENERS = ("user", "developer")


def with_block(messages: list[Any], block: str) -> list[Any]:
    """Blok güncel turun önüne, geçmişin arkasına (§8.3): son tur açan mesajın hemen önü.

    Tool çağrısı ve sonucu gibi tur içinde sonradan gelenler bloğun arkasında kalır; tur
    sürerken blok aynı yerde durur ve önek tur içinde değişmez.
    """
    at = next(
        (
            i
            for i in range(len(messages) - 1, -1, -1)
            if isinstance(messages[i], dict) and messages[i].get("role") in _TURN_OPENERS
        ),
        len(messages),
    )
    # Kişinin söylediği değil sistemin bildiği: kullanıcı mesajı olarak gitmez (§18 madde 7).
    return [*messages[:at], {"role": "developer", "content": block}, *messages[at:]]


class ContextualLLMService(OpenAILLMService):
    """Her isteğe o anın bağlam bloğunu ekleyen model servisi."""

    def __init__(self, *, block: Callable[[], str], **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self._block = block

    async def get_chat_completions(
        self, context: LLMContext
    ) -> AsyncStream[ChatCompletionChunk]:
        messages = with_block(list(context.messages), self._block())
        copy = LLMContext(
            messages=messages, tools=context.tools, tool_choice=context.tool_choice
        )
        return await super().get_chat_completions(copy)


def llm_service(
    endpoint: Endpoint, system_instruction: str, block: Callable[[], str]
) -> OpenAILLMService:
    """Ayarlar gövdeyle her istekte gider; sunucunun varsayılanı rol farkını bilmez."""
    service = ContextualLLMService(
        block=block,
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
