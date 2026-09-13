"""Turun yeniden oynatılması (§15).

"Tur izleri kalıcı yazılır ve **yeniden oynatılabilir**: aynı girdi, sahte adaptörlerle
tekrar çalıştırılabilir. **Ses kaydetmeden** hata ayıklama bunu gerektirir."

Cümlenin son yarısı tasarımı belirliyor: kaydedilen şey ses değil, **transkript**. Bir turu
yeniden koşmak için gereken tam olarak şu üçü:

1. segmentin metni (STT'nin o gün ne duyduğu),
2. LLM'in ürettikleri, sırayla,
3. onay akışına gelen yanıtlar (varsa) — onlar da metin.

Bunlar `Recording`. Yeniden koşuda LLM'in yerine bu betiği okuyan `FakeLLM` geçiyor, ses
girişi hiç olmuyor (metin segmenti zaten birinci sınıf, P1). Çıkan `TurnOutcome` canlı
turunkiyle karşılaştırılabilir: aynı metin, aynı ilerleme, aynı aşama dizisi, aynı sonuç.

**Süreler karşılaştırılmıyor**, yalnızca aşamaların adı ve sırası. Süre makineye bağlı; onu
eşitlik ölçütü yapmak, testi donanım hızına bağlamak olurdu (Kural 14'ün tersi bir hata:
ölçülen bir sayıyı ölçüt sanmak).

**Kaydın nereye yazıldığı burada karara bağlanmıyor.** §15 yeniden oynatmayı istiyor ama
`Recording`'in hangi tabloda duracağını ne §15 ne §16 söylüyor; gövdelerin yeri `messages`
ve o tablonun tur akışına bağlanması konuşma geçmişiyle birlikte gelir (§11.1). Bu dosya
kaydı **üretiyor** ve **oynatıyor**; kalıcılığı ekleyecek olan, geçmişi yazan taraf.
"""

import asyncio
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass, field

from mayen.adapters.audio import AudioFormat
from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage
from mayen.obs.trace import Outcome
from mayen.turn.report import SegmentLike
from mayen.turn.runner import Runner


@dataclass(frozen=True, slots=True)
class Recording:
    """Bir turu yeniden koşmak için gereken her şey. Ses yok, yalnızca metin."""

    turn_id: str
    device_id: str
    segment_id: str
    transcript: str
    responses: tuple[str, ...]
    """LLM'in ürettikleri, üretildikleri sırayla. Ajan ve onay çözümleyicisi aynı akıştan
    okuyor — ikisi tek bir modeli paylaşıyor ve sıra o modelin gördüğü sıra."""
    answers: tuple[str, ...] = ()
    """Onay akışına gelen segmentler (§8.5). Onaysız turda boş."""


@dataclass(frozen=True, slots=True)
class TurnOutcome:
    """Turun gözlemlenebilir sonucu. Canlı koşuda da yeniden oynatmada da aynı şey."""

    text: str
    progress: tuple[str, ...]
    stages: tuple[str, ...]
    outcome: str


class RecordingLLM:
    """`LLMClient` sarmalayıcısı: ürettiği her yanıtı biriktirir.

    Sayaç ucu ve sağlık kontrolü olduğu gibi geçiyor — kaydedilen şey üretim, ölçüm değil.
    """

    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self.responses: list[str] = []

    @property
    def name(self) -> str:
        return self._inner.name

    async def health(self) -> bool:
        return await self._inner.health()

    async def count_tokens(self, text: str) -> int:
        return await self._inner.count_tokens(text)

    async def context_size(self) -> int:
        return await self._inner.context_size()

    async def stream(
        self,
        messages: Sequence[PromptMessage],
        *,
        grammar: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str]:
        chunks: list[str] = []
        async for chunk in self._inner.stream(messages, grammar=grammar, max_tokens=max_tokens):
            chunks.append(chunk)
            yield chunk
        self.responses.append("".join(chunks))

    async def stream_native(
        self,
        messages: Sequence[PromptMessage],
        *,
        tools: Sequence[dict[str, object]],
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str | NativeCall]:
        """Yerel biçim. Kayda **çağrılar da** giriyor: bir turu yeniden oynatmanın anlamı
        modelin ürettiğinin tamamını saklamak ve yerel biçimde çağrı metnin dışında."""
        parts: list[str] = []
        stream = self._inner.stream_native(messages, tools=tools, max_tokens=max_tokens)
        async for event in stream:
            parts.append(event if isinstance(event, str) else f"<çağrı> {event.name}")
            yield event
        self.responses.append("".join(parts))


type RunnerFactory = Callable[[LLMClient, "Collector"], Runner]
"""Yeniden oynatma için koşucuyu kuran taraf. Kurulum çağıranın elinde: `Runner`'ın
bağımlılıklarını burada ikinci kez yazmak, iki yerde bakımı yapılan bir kurulum demekti."""


class Collector:
    """`TurnSink` + `TraceSink` + `TurnReport`: turun dışarıya söylediği her şeyi toplar."""

    def __init__(self) -> None:
        self.audio: list[bytes] = []
        self.replies: list[str] = []
        self.progress: list[str] = []
        self.stages: list[str] = []
        self.outcome: str | None = None

    # TurnSink
    async def reply(self, turn_id: str, text: str) -> None:
        self.replies.append(text)

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        self.audio.append(data)

    async def audio_end(self, turn_id: str) -> None:
        self.progress.append("audio_end")

    async def transcript(self, turn_id: str, segment_id: str, text: str) -> None:
        self.progress.append("transcript")

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        self.progress.append(f"tool_running:{tool_name}")

    async def turn_failed(self, turn_id: str, error: str) -> None:
        self.progress.append("turn_failed")

    # TraceSink
    def start(self, turn_id: str, device_id: str, *, person_id: int | None = None) -> None:
        pass

    def add_stage(
        self,
        turn_id: str,
        name: str,
        *,
        duration_ms: int | None = None,
        detail: str | None = None,
    ) -> None:
        # Süre bilerek atılıyor: makineye bağlı, karşılaştırma ölçütü değil.
        self.stages.append(name)

    def finish(self, turn_id: str, outcome: str) -> None:
        self.outcome = outcome

    # TurnReport
    async def understood(self) -> None:
        self.progress.append("understood")

    async def speaking(self) -> None:
        self.progress.append("speaking")

    async def spoke(self) -> None:
        self.progress.append("spoke")

    async def answer_empty(self) -> None:
        self.progress.append("answer_empty")

    async def approval_needed(self) -> None:
        self.progress.append("approval_needed")

    async def approved(self) -> None:
        self.progress.append("approved")

    async def refused(self) -> None:
        self.progress.append("refused")

    async def approval_timed_out(self) -> None:
        self.progress.append("approval_timed_out")

    async def registration_needed(self) -> None:
        self.progress.append("registration_needed")

    async def registration_done(self) -> None:
        self.progress.append("registration_done")

    def result(self) -> TurnOutcome:
        return TurnOutcome(
            text=b"".join(self.audio).decode("utf-8", errors="replace"),
            progress=tuple(self.progress),
            stages=tuple(self.stages),
            outcome=self.outcome if self.outcome is not None else Outcome.HATA.value,
        )


@dataclass(frozen=True, slots=True)
class _Segment:
    segment_id: str
    device_id: str
    payload: object


@dataclass(slots=True)
class _Turn:
    """`TurnHandle`'ın kayıttan kurulmuş hâli. Söz kesme yok: kayıt onu taşımıyor."""

    turn_id: str
    segment: SegmentLike
    speech_stopped: asyncio.Event = field(default_factory=asyncio.Event)
    segments: asyncio.Queue[object] = field(default_factory=asyncio.Queue)


async def replay(recording: Recording, build: RunnerFactory) -> TurnOutcome:
    """Kaydı sahte adaptörlerle tekrar koşar ve gözlemlenebilir sonucu döner.

    Onay yanıtları kuyruğa **baştan** konuyor: yeniden oynatmada karşıda konuşan kimse yok,
    beklemek zaman aşımından başka bir şeye varmazdı.
    """
    collector = Collector()
    turn = _Turn(
        turn_id=recording.turn_id,
        segment=_Segment(
            segment_id=recording.segment_id,
            device_id=recording.device_id,
            payload=recording.transcript,
        ),
    )
    for answer in recording.answers:
        turn.segments.put_nowait(
            _Segment(segment_id="replay", device_id=recording.device_id, payload=answer)
        )
    runner = build(FakeLLM(recording.responses), collector)
    await runner.run(turn, collector)
    return collector.result()
