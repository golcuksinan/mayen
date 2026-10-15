"""Hattın dışından tek bir model isteği (replay, §14), llama.cpp'nin OpenAI uyumlu ucunda.

Hattaki servisin istek kuruluşuna uyar: rolün ayarları gövdeyle her istekte gider, şablon
ortadaki geliştirici mesajını kabul etmiyorsa o mesaj kullanıcı mesajı olur.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from mayen.adapters.llamacpp.confirmation import client
from mayen.ports.models import Endpoint, ModelCall, ModelReply


class LlamaCppChat:
    def __init__(self, endpoint: Endpoint) -> None:
        self._endpoint = endpoint
        self._client = client(endpoint)

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        tool_choice: str,
    ) -> ModelReply:
        sent = [dict(m) for m in messages]
        if not self._endpoint.developer_role:
            for m in sent[1:]:
                if m["role"] == "developer":
                    m["role"] = "user"
        # Mesajlar ve tool'lar OpenAI biçiminde sözlüklerdir; istemcinin TypedDict'leri değil.
        response = await self._client.chat.completions.create(  # type: ignore[call-overload]
            model=self._endpoint.model,
            messages=sent,
            tools=list(tools),
            tool_choice=tool_choice,
            extra_body=dict(self._endpoint.body),
        )
        message = response.choices[0].message
        calls = [
            ModelCall(c.id, c.function.name, c.function.arguments)
            for c in message.tool_calls or ()
            if c.type == "function"
        ]
        return ModelReply((message.content or "").strip(), calls)
