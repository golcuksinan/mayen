"""Sahte LLM."""

import asyncio
from collections import deque
from collections.abc import AsyncGenerator, Iterable, Sequence

from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.llm import NativeCall, PromptMessage


class FakeLLM:
    """Betiğe göre yanıt akıtan LLM.

    Kaydettiği çağrılar (`calls`) testin asıl malzemesi: sabit önek kuralının (§8.1)
    bozulup bozulmadığı ancak modele **ne gönderildiğine** bakarak anlaşılır.
    """

    def __init__(
        self,
        responses: Iterable[str] = (),
        *,
        name: str = "fake-llm",
        chunk_size: int = 4,
        available: bool = True,
        context_tokens: int = 4096,
    ) -> None:
        self._name = name
        self._responses: deque[str] = deque(responses)
        self._chunk_size = chunk_size
        self._context_tokens = context_tokens
        self.available = available
        self.calls: list[tuple[PromptMessage, ...]] = []
        self.grammars: list[str | None] = []
        self.native_calls: list[tuple[NativeCall, ...]] = []
        """Sıraya konmuş yerel çağrılar; her `stream_native` biri tüketir. Boş bırakılırsa
        yerel akış da yalnızca metin verir — yani "çağırmadı" hâli."""
        self.tool_schemas: list[Sequence[dict[str, object]]] = []

    @property
    def name(self) -> str:
        return self._name

    async def health(self) -> bool:
        return self.available

    def queue(self, *responses: str) -> None:
        self._responses.extend(responses)

    async def count_tokens(self, text: str) -> int:
        """Sahte de olsa bu bir **sayaç**, tahminci değil (Kural 10): boşluğa bölüp sayar
        ve aynı metin için hep aynı sayıyı verir. Üst katman sayıyı buradan alma
        alışkanlığını gerçek servise de taşır."""
        if not self.available:
            raise ServiceUnavailableError(self._name, "servis kapalı")
        return len(text.split())

    async def context_size(self) -> int:
        """Testin bütçeyi küçültebilmesi için kurulumda verilir; sunucuya sorulan sayının
        yerine geçer (§11.1)."""
        if not self.available:
            raise ServiceUnavailableError(self._name, "servis kapalı")
        return self._context_tokens

    def queue_native(self, *calls: NativeCall) -> None:
        """Bir sonraki `stream_native` üretiminin döndüreceği çağrılar."""
        self.native_calls.append(calls)

    async def stream_native(
        self,
        messages: Sequence[PromptMessage],
        *,
        tools: Sequence[dict[str, object]],
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str | NativeCall]:
        """Yerel biçim (`CallFormat.YEREL`). Metin `stream` ile aynı sıradan geliyor;
        çağrılar ayrı bir sıradan, çünkü ikisi **aynı üretimde** birlikte olabilir ve
        testin kurması gereken durum tam olarak budur."""
        calls = self.native_calls.pop(0) if self.native_calls else ()
        self.tool_schemas.append(tools)
        async for chunk in self.stream(messages, max_tokens=max_tokens):
            yield chunk
        for call in calls:
            yield call

    async def stream(
        self,
        messages: Sequence[PromptMessage],
        *,
        grammar: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str]:
        if not self.available:
            raise ServiceUnavailableError(self._name, "servis kapalı")
        self.calls.append(tuple(messages))
        self.grammars.append(grammar)
        if not self._responses:
            raise AssertionError(f"{self._name}: sıraya yanıt konmadı")
        text = self._responses.popleft()
        for start in range(0, len(text), self._chunk_size):
            # Parçalar arasında denetimi bırakmak iptali (Kural 12) test edilebilir yapar;
            # tek nefeste dönen bir üreteç hiçbir zaman iptal edilemez.
            await asyncio.sleep(0)
            yield text[start : start + self._chunk_size]
