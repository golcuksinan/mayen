"""Sahte STT."""

from collections import deque
from collections.abc import Iterable

from mayen.adapters.audio import Audio
from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.stt import Transcript


class FakeSTT:
    """Betikteki transkripti verir; betik boşsa ses yükünü **metin sayar**.

    İkinci davranış P1'in ertelenmiş STT kararı: sahte STT, istemciden gelen metin
    segmentini transkript kabul eder. Böylece gerçek STT gelmeden uçtan uca yazışılabilir
    ve üst katmanların hiçbiri değişmez — yalnızca uç değişir.
    """

    def __init__(
        self,
        transcripts: Iterable[str] = (),
        *,
        name: str = "fake-stt",
        language: str = "tr",
        available: bool = True,
    ) -> None:
        self._name = name
        self._language = language
        self._transcripts: deque[str] = deque(transcripts)
        self.available = available
        self.calls: list[Audio] = []

    @property
    def name(self) -> str:
        return self._name

    async def health(self) -> bool:
        return self.available

    def queue(self, *transcripts: str) -> None:
        self._transcripts.extend(transcripts)

    async def transcribe(self, audio: Audio) -> Transcript:
        if not self.available:
            raise ServiceUnavailableError(self._name, "servis kapalı")
        self.calls.append(audio)
        text = self._transcripts.popleft() if self._transcripts else audio.data.decode("utf-8")
        return Transcript(text=text, language=self._language, confidence=1.0)
