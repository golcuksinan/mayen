"""Tur koşucusu (§6): segment → konuşmacı tanıma ∥ STT → ajan → cümle bölücü → TTS kuyruğu.

`session.TurnRunner`'ın gerçek uygulaması. Aktör durumu yürütür, burası turu koşar ve
ilerlemesini `report` ile bildirir — P4'ün bıraktığı boşluk tam olarak bu.

**Konuşmacı tanıma ve STT paralel** (§6): ikisi de aynı segmenti okur ve birbirini
beklemez. Gömüyü kademeye çevirmek burada **yok**; §19.3'ün eşikleri açık, o iş Faz 4'ün.
Bu yüzden kimlik bir `Identifier` geri çağrımından geliyor — akış bugün fake'le, Faz 4'te
gerçeğiyle koşar; ikisi de aynı yere takılır.

**Onay akışı burada yürüyor** (§8.5), çünkü `ONAY_BEKLİYOR` bir oturum durumu ve ajan onu
göremez. Sıra pazarlığa kapalı: önce duruma geçilir, **sonra** cümle okunur (B3). Okuma
sırasında söz kesilirse (`speech_stopped`) yalnızca ses durur; durum ve plan yaşar, gelen
segment doğrudan çözümleyiciye gider.

**Oturumla konuşma `turn/report.py`'nin dar arayüzünden** — `session` bu katmanın üstünde
ve import edilemez; gerekçesi orada yazılı.

**Zaman aşımı turu bitirir.** §5'in tablosunda `ONAY_ZAMAN_AŞIMI` `IDLE`'a gidiyor: plan
düşer ve konuşulmaz, çünkü karşıda kimse yok. Bu yüzden `False` dönmek yetmez — döngü
`DÜŞÜNÜYOR`'a devam ederdi, oysa durum artık `IDLE`. Akış `_AbandonedError` ile kesilir.

**Boş yanıt turu bitirir, ama sessizce değil.** Hiç ses üretilmezse `İLK_SES_HAZIR` da
olmaz, yani `SES_BİTTİ` ile kapanacak bir `KONUŞUYOR` yok. P8'de bu bir hataydı çünkü §5
tabloda karşılığı yoktu; 2026-08-10'da tabloya `YANIT_BOŞ → IDLE` çıkışı eklendi (gerçek
modelde boş üretim mümkün ve tur bir istisnayla değil, tanımlı bir geçişle bitmeli). Sebep
§14'ün ayrı kanalından bildirilir — önce sebep, sonra durum (Kural 13).

**Konuşma geçmişi buradan yazılıyor** (§11.1): kullanıcının cümlesi, turun her tool
adımı (çağrı `assistant`, sonuç `tool`), asistanın yanıtı — bu sırayla.

**Tool sonucu artık saklanıyor** (2026-08-16, Faz B) ve bu bir geri alma. Eski kural
"sonuç ertesi tur bayat, yalnızca adı yaz"dı; `[araç] bu turda çağrıldı: …` satırı
2026-08-12'de o gerekçeyle kondu. Üç bağımsız ölçüm o izin **etkisiz** olduğunu söyledi
(`docs/faz6-olcum.md`, `docs/faz-a-bulgular.md` §2.1, `docs/faz-b-bicim.md`) ve
dördüncüsü sebebi gösterdi: sonuç atılınca veri geçmişte **yalnızca asistanın cevabında**
kalıyor, yani bir tool'dan geldiği hiçbir yerde yazmıyor ve model onu kendi bilgisi
sanıyor. Bayatlık yok olmuyordu, kaynağı gizleniyordu. Sonuç `tool` rolünde durduğunda
kaynak da tarih de rollerden okunuyor — §11.3'ün "bayatsa tool çağır"ı ancak o zaman
uygulanabilir bir kural. Gerekçenin uzunu `agent/loop.py:ToolDone`'da.

**Ajanın tur içinde gördüğü dizi ile ertesi tur göreceği dizi artık aynı biçimde.**
Eskiden ilki iki mesajdı (çağrı + sonuç), ikincisi tek satırlık bir izdi; model kendi
geçmişinde hiç üretmediği bir biçim görüyordu.

**Söz kesilen turun yanıtı da yazılmıyor:** iptal üretimin ortasında geliyor ve yarım bir
cümleyi "asistan bunu söyledi" diye kaydetmek, kullanıcının duymadığı bir konuşmayı
geçmişe yazmak olurdu.

**Bellek turun içinde iki yerde:** pencere kurulurken (özet + geçmiş + olgular) ve tur
biterken (yanıtın kaydı). İkisinin arasında hiçbir arka plan işi çalışmıyor; onu koşturan
`memory.BackgroundWork` turun kuyruğa girmesiyle iptal ediliyor (Kural 11).
"""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from dataclasses import replace
from typing import Protocol

from mayen.adapters.audio import Audio, AudioFormat
from mayen.adapters.llm import NativeCall
from mayen.adapters.speaker import Embedding, SpeakerClient
from mayen.adapters.stt import STTClient
from mayen.adapters.tts import TTSClient
from mayen.agent.loop import AgentLoop, TextChunk, ToolDone, ToolStarted
from mayen.agent.prompt import ContextBlock
from mayen.data import clock
from mayen.data.repositories.conversation import Role
from mayen.memory.window import Window
from mayen.obs.log import get_logger
from mayen.obs.trace import Outcome as TurnOutcome
from mayen.obs.trace import Stage, TraceSink, TurnTrace, tool_stage
from mayen.policy.approval import ApprovalFlow, ApprovalResolver, Outcome, PendingPlan
from mayen.policy.authority import Identity
from mayen.turn.report import SegmentLike, TurnHandle, TurnReport
from mayen.turn.sentences import split
from mayen.turn.speech import AudioSink, SpeechQueue

log = get_logger(__name__)

type Identifier = Callable[[Embedding | None], Awaitable[Identity]]
"""Gömü → kimlik. Eşikler §19.3'te açık, karşılaştırma Faz 4'ün işi (bkz. modül başlığı)."""


class TurnSink(AudioSink, Protocol):
    """Turun dışarıya duyurdukları (§13). `transport` uygular; `turn` çerçeveyi görmez."""

    async def transcript(self, turn_id: str, segment_id: str, text: str) -> None:
        """Segmenti tura bağlayan çerçeve: `turn_id`'yi sunucu üretir (§13)."""
        ...

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        """§6: tool sonucu dönene kadar ses yok; sessizliğin sebebi bildirilir."""
        ...

    async def turn_failed(self, turn_id: str, error: str) -> None:
        """§14'ün ayrı hata kanalı. `SessionSink`'te aynı imzayla var ve `transport`'ta
        ikisini de tek `FrameSink` uyguluyor — turun kendi bildirebildiği tek hata,
        durumu tabloya göre biten boş yanıt."""
        ...


class Conversation(Protocol):
    """Turun belleğe bakan yüzü (§11). `memory.ContextWindow` uyguluyor.

    `memory` bu katmanın altında ve doğrudan import edilebilirdi; arada bu `Protocol`'ün
    durmasının sebebi §4'ün şartı: bütün tur akışı GPU'suz **ve** veritabanısız test
    edilebilmeli. Gerçek pencere iki repository ile bir LLM istiyor; turun ondan istediği
    ise iki yöntem.
    """

    def record(
        self,
        turn_id: str,
        role: Role,
        content: str,
        *,
        person_id: int | None = None,
        tool_calls: tuple[NativeCall, ...] = (),
    ) -> object: ...

    async def build(self, *, fixed_text: str, person_id: int | None = None) -> Window: ...


class _AbandonedError(Exception):
    """Onay zaman aşımı: tur konuşulmadan biter (§5, Kural 5)."""


class Runner:
    def __init__(
        self,
        *,
        agent: AgentLoop,
        system: str,
        language_rule: str | None = None,
        stt: STTClient,
        speaker: SpeakerClient,
        tts: TTSClient,
        sink: TurnSink,
        traces: TraceSink,
        identify: Identifier,
        resolver: ApprovalResolver,
        memory: Conversation,
        min_chars: int,
        max_wait_seconds: float,
        approval_timeout_seconds: float,
    ) -> None:
        self._agent = agent
        self._system = system
        #: Yerel çağrı biçiminde dolu: dil kuralı bağlam bloğunun sonuna biniyor, çünkü
        #: sistem promptunun sonu artık öneğin sonu değil (`agent/prompt.py`'de gerekçe).
        #: Yeri seçen taraf `main` — montaj, katman değil (§8.3'ün biçim kuralı duruyor).
        self._language_rule = language_rule
        self._stt = stt
        self._speaker = speaker
        self._tts = tts
        self._sink = sink
        self._traces = traces
        self._identify = identify
        self._resolver = resolver
        self._memory = memory
        self._min_chars = min_chars
        self._max_wait = max_wait_seconds
        self._approval_timeout = approval_timeout_seconds

    async def run(self, turn: TurnHandle, report: TurnReport) -> None:
        """`session.TurnRunner` sözleşmesi."""
        with TurnTrace(self._traces, turn.segment.device_id, turn_id=turn.turn_id) as trace:
            try:
                await self._run(turn, report, trace)
            except _AbandonedError:
                log.info("onay zaman aşımı, tur bitti", turn_id=turn.turn_id)
                # **Sessiz red yine sessiz, ama turun bittiği duyuruluyor.** İstemciler
                # turu durumdan değil çerçeveden takip ediyor; bitiş çerçevesi çıkmayınca
                # `active_turn` ve GUI'nin `_speaking` bayrağı ölü turda asılı kalıyordu ve
                # bir sonraki turun cevabı bir öncekinin satırına biniyordu. Sahibin
                # ekranında görüldü (2026-08-16): `[tool] window_close Close the active
                # window?` iki turun tek satırda birleşmiş hâli.
                await self._sink.audio_end(turn.turn_id)

    async def _run(self, turn: TurnHandle, report: TurnReport, trace: TurnTrace) -> None:
        text, embedding = await self._understand(turn.segment, trace)
        await self._sink.transcript(turn.turn_id, turn.segment.segment_id, text)
        await report.understood()

        identity = await self._identify(embedding)
        context = ContextBlock(
            now=clock.local(),
            speaker=_speaker_line(identity),
            language_rule=self._language_rule,
        )
        # Sabit kısım: geçmiş dışında öneğe giren her şey. Bütçeyi bölen taraf `memory`;
        # burası yalnızca "şu kadarı zaten dolu" diyor (§11.1, tek yer kuralı).
        window = await self._memory.build(
            fixed_text=f"{self._system}\n{context.render()}\n{text}",
            person_id=identity.person_id,
        )
        context = replace(context, facts=window.facts)
        # Kayıt pencere kurulduktan **sonra**: önce yazıldığında bu cümle geçmişin son
        # satırı olarak da dönüyordu ve model kullanıcının sözünü iki kez görüyordu —
        # bir kez geçmişte, bir kez `[bağlam]`dan sonra. Gerçek modelde görüldü.
        self._memory.record(turn.turn_id, "user", text, person_id=identity.person_id)

        audio = _FirstAudio(self._sink, trace, report)
        speech = SpeechQueue(self._tts, audio)
        answer: list[str] = []
        called: list[ToolDone] = []
        events = self._agent.run(
            self._system,
            identity=identity,
            context=context,
            user=text,
            summary=window.summary,
            history=window.history,
            approve=self._approver(turn, report, trace, speech, audio),
        )
        async with aclosing(events) as stream:
            chunks = self._chunks(stream, turn.turn_id, trace, answer, called)
            pieces = split(chunks, min_chars=self._min_chars, max_wait_seconds=self._max_wait)
            async with aclosing(pieces) as sentences:
                await speech.speak(turn.turn_id, sentences)

        if not audio.announced:
            # Hiç ses çıkmadı: sebep önce (§14), durum sonra (§5'in `YANIT_BOŞ` çıkışı).
            # Ters sırada istemci turun sessizce bittiğini sanardı. Kullanıcının duymadığı
            # bir yanıt geçmişe de yazılmaz — tool izi de: yanıt satırı olmayınca tur
            # geçmişte hiç görünmez ve taklit edilecek yarım bir örnek bırakmaz.
            log.warning("boş yanıt", turn_id=turn.turn_id)
            # İz açıkça `HATA`: istisna kalmadığı için `__exit__` bunu `TAMAM` sayardı ve
            # duyulmamış bir tur başarılı görünürdü.
            trace.finish(TurnOutcome.HATA)
            await self._sink.turn_failed(turn.turn_id, "empty_answer: ajan hiç metin üretmedi")
            await report.answer_empty()
            return
        for step in called:
            # Tur içindeki dizinin aynısı, kalıcı hâlde: çağrı `assistant`, sonuç `tool`.
            # Ajanın o tur gördüğü geçmiş ile ertesi tur göreceği geçmiş böylece **aynı
            # biçimde** oluyor; eskiden ilki iki mesaj, ikincisi tek satırlık bir izdi.
            self._memory.record(
                turn.turn_id, "assistant", step.call_text, tool_calls=step.tool_calls
            )
            self._memory.record(turn.turn_id, "tool", step.feedback)
        self._memory.record(turn.turn_id, "assistant", "".join(answer))
        await speech.end(turn.turn_id)
        await report.spoke()

    async def _understand(
        self, segment: SegmentLike, trace: TurnTrace
    ) -> tuple[str, Embedding | None]:
        """§6'nın çatalı: iki servis aynı segmenti okur, biri diğerini beklemez.

        Metin segmentinde (P1'in ertelenmiş STT kararı) konuşmacı tanıma yok — ortada ses
        yok. Kimliği metinden okumak Kural 7'nin yasakladığı şey olurdu.
        """
        payload = segment.payload
        if isinstance(payload, str):
            return payload, None
        if not isinstance(payload, Audio):
            raise TypeError(f"beklenmeyen segment yükü: {type(payload).__name__}")
        transcript, embedding = await asyncio.gather(
            self._transcribe(payload, trace), self._embed(payload, trace)
        )
        return transcript, embedding

    async def _transcribe(self, audio: Audio, trace: TurnTrace) -> str:
        with trace.stage(Stage.STT):
            return (await self._stt.transcribe(audio)).text

    async def _embed(self, audio: Audio, trace: TurnTrace) -> Embedding:
        with trace.stage(Stage.KONUSMACI):
            return await self._speaker.embed(audio)

    async def _chunks(
        self,
        events: AsyncIterator[object],
        turn_id: str,
        trace: TurnTrace,
        answer: list[str],
        called: list[ToolDone],
    ) -> AsyncGenerator[str]:
        """Ajan olaylarını cümle bölücünün beklediği metin akışına indirger.

        `answer` yol üstünde birikiyor: yanıtı konuşma geçmişine yazmak için ikinci kez
        toplamak, aynı metnin iki kopyasını tutmak olurdu. `called` aynı sebeple burada
        toplanıyor: çağrılan tool'ların adı yalnızca bu olay akışında geçiyor.
        """
        first = True
        async for event in events:
            match event:
                case TextChunk(text=text):
                    if first:
                        trace.mark(Stage.LLM_ILK_TOKEN)
                        first = False
                    answer.append(text)
                    yield text
                case ToolStarted(name=name):
                    trace.mark(tool_stage(name))
                    await self._sink.tool_running(turn_id, name)
                case ToolDone():
                    called.append(event)

    def _approver(
        self,
        turn: TurnHandle,
        report: TurnReport,
        trace: TurnTrace,
        speech: SpeechQueue,
        audio: "_FirstAudio",
    ) -> Callable[[PendingPlan], Awaitable[bool]]:
        async def approve(plan: PendingPlan) -> bool:
            flow = ApprovalFlow(plan, self._resolver, timeout_seconds=self._approval_timeout)
            # Önce durum, sonra okuma (§8.5 adım 2, B3). Sıra pazarlığa kapalı.
            await report.approval_needed()
            while True:
                await self._read_out(turn, plan.spoken, speech, audio)
                segment = await self._await_answer(turn, report)
                answer, _ = await self._understand(segment, trace)
                match await flow.resolve_segment(answer):
                    case Outcome.ONAYLANDI:
                        await report.approved()
                        return True
                    case Outcome.REDDEDILDI:
                        await report.refused()
                        return False
                    case Outcome.TEKRAR_SOR:
                        continue  # §8.5 adım 5: bir kez daha sorulur

        return approve

    async def _read_out(
        self, turn: TurnHandle, spoken: str, speech: SpeechQueue, audio: "_FirstAudio"
    ) -> None:
        """Onay cümlesini okur; söze girilirse ses durur, plan yaşar (B3).

        Okuma ayrı bir görevde, çünkü beklenen iki şey var: okumanın bitmesi ve söz
        kesilmesi. `speech_stopped` her okumadan önce temizleniyor — önceki turdan kalan
        bir bayrak, ikinci soruyu hiç okunmadan bitirirdi.
        """
        turn.speech_stopped.clear()
        audio.announce = False  # durum ONAY_BEKLIYOR; §5 oradan İLK_SES_HAZIR tanımlamıyor
        reading = asyncio.create_task(speech.speak(turn.turn_id, _one(spoken)))
        stopped = asyncio.create_task(turn.speech_stopped.wait())
        try:
            await asyncio.wait({reading, stopped}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            stopped.cancel()
            if not reading.done():
                reading.cancel()
            audio.announce = True
        if reading.done() and not reading.cancelled():
            reading.result()  # sentez hatası yutulmaz (Kural 13)

    async def _await_answer(self, turn: TurnHandle, report: TurnReport) -> SegmentLike:
        """Kapalı durumdaki turun kendi kuyruğundan gelen segment (§5).

        Zaman aşımında red — ama sessiz bir red: `IDLE`'a dönülür ve hiçbir şey okunmaz.
        """
        try:
            async with asyncio.timeout(self._approval_timeout):
                segment: SegmentLike = await turn.segments.get()
                log.info("onay yaniti alindi!", payload=segment.payload)
                return segment
        except TimeoutError:
            await report.approval_timed_out()
            raise _AbandonedError from None


class _FirstAudio:
    """`AudioSink` sarmalayıcısı: ilk parçada durumu ve iki ölçüm anını işaretler.

    `announced` "durum KONUŞUYOR'a geçti mi" sorusunun cevabı; boş yanıtı yakalayan işaret bu.

        `announce` bilerek bir bayrak: onay cümlesi de bu kuyruktan geçiyor ve o sırada durum
        `ONAY_BEKLİYOR` — §5 oradan `İLK_SES_HAZIR` tanımlamıyor, bildirim tabloya olmayan bir
        geçiş isterdi.

        `TTS_ILK_PARCA` ile `ILK_SES` aynı an değil: ilki TTS'ten çıkan ilk bayt, ikincisi
        istemciye kabul edilen ilk bayt. Kuyruk doluysa (§13 backpressure) aradaki fark tam da
        ölçülmek istenen şey.
    """

    def __init__(self, sink: AudioSink, trace: TurnTrace, report: TurnReport) -> None:
        self._sink = sink
        self._trace = trace
        self._report = report
        self.announce = True
        self.announced = False
        self._seen = False

    async def reply(self, turn_id: str, text: str) -> None:
        await self._sink.reply(turn_id, text)

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        first = not self._seen
        self._seen = True
        if first:
            self._trace.mark(Stage.TTS_ILK_PARCA)
        if self.announce and not self.announced:
            self.announced = True
            await self._report.speaking()
        await self._sink.audio_chunk(turn_id, seq, audio_format, data)
        if first:
            self._trace.mark(Stage.ILK_SES)

    async def audio_end(self, turn_id: str) -> None:
        await self._sink.audio_end(turn_id)


def _speaker_line(identity: Identity) -> str:
    """Bağlam bloğuna yazılan konuşmacı satırı. Yetki değil, bilgi (Kural 4)."""
    return identity.authority.value


async def _one(text: str) -> AsyncGenerator[str]:
    yield text
