"""Sahte LLM."""

import asyncio
from collections import deque
from collections.abc import AsyncGenerator, Iterable, Sequence

from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.llm import PromptMessage


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
    ) -> None:
        self._name = name
        self._responses: deque[str] = deque(responses)
        self._chunk_size = chunk_size
        self.available = available
        self.calls: list[tuple[PromptMessage, ...]] = []
        self.grammars: list[str | None] = []

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
