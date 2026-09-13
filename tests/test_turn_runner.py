"""§6'nın tur akışı, uçtan uca — GPU'suz, saniyeler içinde (§18 Faz 1 bitti kriteri)."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from mayen.adapters.audio import Audio, AudioFormat
from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.fakes.speaker import FakeSpeaker
from mayen.adapters.fakes.stt import FakeSTT
from mayen.adapters.fakes.tts import FAKE_FORMAT, FakeTTS
from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage
from mayen.adapters.speaker import Embedding
from mayen.agent.calls import CallFormat
from mayen.agent.loop import AgentLoop
from mayen.memory.window import Window
from mayen.obs.trace import TraceSink
from mayen.policy.approval import ApprovalResolver
from mayen.policy.authority import Authority, Identity
from mayen.policy.effects import Effect
from mayen.session.actor import Segment, Session
from mayen.session.state import State
from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult
from mayen.turn.replay import Collector, Recording, RecordingLLM, replay
from mayen.turn.runner import Runner, TurnSink


@dataclass
class FakeMemory:
    """`Conversation`'ın sahtesi: turun belleğe ne yazdığı testin görebildiği tek şey.

    Gerçek `ContextWindow` iki repository ile bir LLM istiyor; §4 bütün tur akışının
    GPU'suz **ve** veritabanısız koşmasını şart koştuğu için koşucu dar bir `Protocol`
    görüyor ve burada karşılığı bu.
    """

    lines: list[tuple[str, str]] = field(default_factory=list)
    window: Window = field(
        default_factory=lambda: Window(summary=None, history=(), facts=None, trimmed=0)
    )
    fixed: list[str] = field(default_factory=list)
    calls: list[tuple[NativeCall, ...]] = field(default_factory=list)

    def record(
        self,
        turn_id: str,
        role: str,
        content: str,
        *,
        person_id: int | None = None,
        tool_calls: tuple[NativeCall, ...] = (),
    ) -> object:
        self.lines.append((role, content))
        self.calls.append(tool_calls)
        return None

    async def build(self, *, fixed_text: str, person_id: int | None = None) -> Window:
        self.fixed.append(fixed_text)
        return self.window


class Sink(TurnSink, TraceSink, Protocol):
    """Koşucunun yazdığı iki uç. `Recorder` ve yeniden oynatmanın `Collector`'ı ikisini de
    karşılıyor; testler aynı `build()`'i paylaşabilsin diye tek tipte birleştirildi."""


DEVICE = "salon"
OWNER = Identity(authority=Authority.SAHIP, person_id=1)


@dataclass
class Recorder:
    """`TurnSink` + `SessionSink` + `TraceSink` — testin gördüğü tek pencere."""

    chunks: list[tuple[str, int, bytes]] = field(default_factory=list)
    replies: list[tuple[str, str]] = field(default_factory=list)
    ended: list[str] = field(default_factory=list)
    transcripts: list[tuple[str, str, str]] = field(default_factory=list)
    tools: list[tuple[str, str]] = field(default_factory=list)
    states: list[State] = field(default_factory=list)
    cancelled: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)

    # TurnSink
    async def reply(self, turn_id: str, text: str) -> None:
        self.replies.append((turn_id, text))

    async def audio_chunk(
        self, turn_id: str, seq: int, audio_format: AudioFormat, data: bytes
    ) -> None:
        self.chunks.append((turn_id, seq, data))

    async def audio_end(self, turn_id: str) -> None:
        self.ended.append(turn_id)

    async def transcript(self, turn_id: str, segment_id: str, text: str) -> None:
        self.transcripts.append((turn_id, segment_id, text))

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        self.tools.append((turn_id, tool_name))

    # SessionSink
    async def state_changed(self, state: State, turn_id: str | None) -> None:
        self.states.append(state)

    async def turn_cancelled(self, turn_id: str) -> None:
        self.cancelled.append(turn_id)

    async def turn_failed(self, turn_id: str, error: str) -> None:
        self.failed.append((turn_id, error))

    # TraceSink
    def start(self, turn_id: str, device_id: str, *, person_id: int | None = None) -> None:
        self.stages.append("start")

    def add_stage(
        self,
        turn_id: str,
        name: str,
        *,
        duration_ms: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.stages.append(name)

    def finish(self, turn_id: str, outcome: str) -> None:
        self.outcomes.append(outcome)

    @property
    def spoken(self) -> str:
        # Sahte TTS her cümlenin sonuna bir boşluk koyuyor (ayıraç, gerekçesi
        # `adapters/fakes/tts.py`'de); son cümleninki kuyrukta kalıyor.
        return b"".join(data for _, _, data in self.chunks).decode("utf-8").strip()


def registry() -> Registry:
    async def weather(ctx: ToolContext, args: Mapping[str, object]) -> ToolResult:
        return ToolResult(ok=True, data={"derece": 18}, speech="on sekiz derece")

    async def wipe(ctx: ToolContext, args: Mapping[str, object]) -> ToolResult:
        return ToolResult(ok=True, data={"silindi": args["id"]})

    reg = Registry()
    reg.register(
        Tool(
            name="hava",
            description="hava durumunu söyler",
            effect=Effect.OKUMA,
            timeout_seconds=5,
            handler=weather,
            args=(Arg(name="sehir", type=ArgType.STRING, description="şehir"),),
        )
    )
    reg.register(
        Tool(
            name="sil",
            description="notu siler",
            effect=Effect.GERI_ALINAMAZ,
            timeout_seconds=5,
            handler=wipe,
            args=(Arg(name="id", type=ArgType.INTEGER, description="not numarası"),),
            confirm="Should I delete note {id}?",
        )
    )
    return reg


def build(
    llm: LLMClient,
    sink: Sink,
    *,
    resolver_llm: LLMClient | None = None,
    tts: FakeTTS | None = None,
    stt: FakeSTT | None = None,
    speaker: FakeSpeaker | None = None,
    approval_timeout_seconds: float = 5,
    memory: FakeMemory | None = None,
) -> Runner:
    reg = registry()
    return Runner(
        agent=AgentLoop(
            llm=llm,
            registry=reg,
            tools=object.__new__(ToolContext),
            call_format=CallFormat.CLI,
            max_steps=3,
            max_corrections=2,
        ),
        system="SİSTEM",
        stt=stt if stt is not None else FakeSTT(),
        speaker=speaker if speaker is not None else FakeSpeaker(),
        tts=tts if tts is not None else FakeTTS(chunk_size=64),
        sink=sink,
        traces=sink,
        identify=_owner,
        resolver=ApprovalResolver(resolver_llm if resolver_llm is not None else FakeLLM()),
        memory=memory if memory is not None else FakeMemory(),
        min_chars=3,
        max_wait_seconds=1,
        approval_timeout_seconds=approval_timeout_seconds,
    )


async def _owner(embedding: Embedding | None) -> Identity:
    return OWNER


def audio(text: str) -> Audio:
    return Audio(format=FAKE_FORMAT, data=text.encode("utf-8"))


def active(session: Session) -> str:
    """Koşan turun kimliği. Sabit yazılamaz: `turn_id` uuid (§13, çakışma doğruluk şartı)."""
    turn = session.active_turn
    assert turn is not None
    return turn.turn_id


async def speak(session: Session, payload: object, segment_id: str = "s1") -> None:
    await session.deliver(Segment(segment_id=segment_id, device_id=DEVICE, payload=payload))


async def test_text_segment_runs_end_to_end() -> None:
    """P1'in ertelenmiş STT kararı: metin segmenti STT'siz aynı yoldan geçer."""
    sink = Recorder()
    llm = FakeLLM(["Merhaba, ben iyiyim."])
    session = Session(build(llm, sink), sink)
    await speak(session, "selam")
    assert sink.spoken == "Merhaba, ben iyiyim."
    assert [(segment_id, text) for _, segment_id, text in sink.transcripts] == [("s1", "selam")]
    assert sink.ended == [sink.transcripts[0][0]]
    assert sink.states == [State.COZUMLUYOR, State.DUSUNUYOR, State.KONUSUYOR, State.IDLE]
    assert sink.outcomes == ["tamam"]


async def test_audio_segment_runs_stt_and_speaker_in_parallel() -> None:
    """§6: iki servis aynı segmenti okur, biri diğerini beklemez."""
    sink = Recorder()
    stt, speaker = FakeSTT(["hava nasıl"]), FakeSpeaker()
    runner = build(FakeLLM(["On sekiz derece."]), sink, stt=stt, speaker=speaker)
    session = Session(runner, sink)
    await speak(session, audio("ses"))
    assert stt.calls and speaker.calls
    assert "stt" in sink.stages and "konusmaci" in sink.stages
    assert sink.transcripts[0][2] == "hava nasıl"


async def test_tool_turn_announces_the_running_tool() -> None:
    """§6: tool sonucu dönene kadar ses yok; kullanıcı sessizliğin sebebini görüyor."""
    sink = Recorder()
    llm = FakeLLM(["<tool> hava --sehir Ankara", "Ankara'da on sekiz derece."])
    session = Session(build(llm, sink), sink)
    await speak(session, "hava nasıl")
    assert [name for _, name in sink.tools] == ["hava"]
    assert sink.spoken == "Ankara'da on sekiz derece."
    assert "tool:hava" in sink.stages


async def test_first_audio_is_measured() -> None:
    """§15: ilk token, TTS'in ilk parçası ve istemciye giden ilk ses ayrı ayrı ölçülür."""
    sink = Recorder()
    session = Session(build(FakeLLM(["Kısa yanıt."]), sink), sink)
    await speak(session, "selam")
    assert {"llm_ilk_token", "tts_ilk_parca", "ilk_ses"} <= set(sink.stages)


async def test_approval_state_comes_before_the_sentence_is_read() -> None:
    """§8.5 adım 2 ve B3: sıra pazarlığa kapalı."""
    sink = Recorder()
    llm = FakeLLM(["<tool> sil --id 3", "Sildim."])
    runner = build(llm, sink, resolver_llm=FakeLLM(["ONAY"]))
    session = Session(runner, sink)

    async def answer() -> None:
        while State.ONAY_BEKLIYOR not in sink.states:
            await asyncio.sleep(0)
        await speak(session, "evet", segment_id="s2")

    task = asyncio.create_task(answer())
    await speak(session, "üçüncü notu sil")
    await task
    assert sink.states[:4] == [
        State.COZUMLUYOR,
        State.DUSUNUYOR,
        State.ONAY_BEKLIYOR,
        State.DUSUNUYOR,
    ]
    # Onay cümlesi asıl yanıttan önce okundu, ikisi de aynı turun sesi.
    assert sink.spoken.startswith("Should I delete note 3?")
    assert sink.spoken.endswith("Sildim.")
    assert [seq for _, seq, _ in sink.chunks] == list(range(len(sink.chunks)))
    assert len(sink.ended) == 1


async def test_approval_timeout_ends_the_turn_silently() -> None:
    """Kural 5 + §5: zaman aşımı reddir, plan düşer, hiçbir şey konuşulmaz."""
    sink = Recorder()
    llm = FakeLLM(["<tool> sil --id 3"])
    session = Session(build(llm, sink, approval_timeout_seconds=0.01), sink)
    await speak(session, "üçüncü notu sil")
    assert sink.states[-1] == State.IDLE
    assert sink.spoken.startswith("Should I delete note 3?")  # yalnızca onay cümlesi
    assert "Sildim" not in sink.spoken
    # Konuşulmuyor ama tur **kapanıyor**: bitiş çerçevesi çıkmazsa istemci ölü turu canlı
    # sanar ve sonraki turun cevabını onun satırına yazar (gerçek ekranda görüldü).
    assert sink.ended == [sink.transcripts[0][0]]
    assert sink.outcomes == ["tamam"]


async def test_refused_approval_feeds_the_model_and_answers() -> None:
    sink = Recorder()
    llm = FakeLLM(["<tool> sil --id 3", "Peki, silmedim."])
    runner = build(llm, sink, resolver_llm=FakeLLM(["RED"]))
    session = Session(runner, sink)

    async def answer() -> None:
        while State.ONAY_BEKLIYOR not in sink.states:
            await asyncio.sleep(0)
        await speak(session, "hayır", segment_id="s2")

    task = asyncio.create_task(answer())
    await speak(session, "üçüncü notu sil")
    await task
    assert sink.spoken.endswith("Peki, silmedim.")
    assert "onaylamadı" in llm.calls[1][-1].content


async def test_barge_in_during_read_out_keeps_the_plan() -> None:
    """B3: okuma sırasında söz kesme sesi durdurur, durum ve plan yaşar."""
    sink = Recorder()
    llm = FakeLLM(["<tool> sil --id 3", "Sildim."])
    runner = build(llm, sink, resolver_llm=FakeLLM(["ONAY"]), tts=FakeTTS(chunk_size=1))
    session = Session(runner, sink)

    async def interrupt_then_answer() -> None:
        while State.ONAY_BEKLIYOR not in sink.states:
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        await session.interrupt(active(session))
        await speak(session, "evet", segment_id="s2")

    task = asyncio.create_task(interrupt_then_answer())
    await speak(session, "üçüncü notu sil")
    await task
    assert session.state is State.IDLE
    assert sink.cancelled == []  # tur öldürülmedi
    assert sink.spoken.endswith("Sildim.")


async def test_cancellation_leaves_no_audio_end() -> None:
    """Kural 12: söz kesme turu iptal eder; turu bitiren çerçeve `Cancelled`."""
    sink = Recorder()
    llm = FakeLLM(["Uzun uzun anlatıyorum. " * 20], chunk_size=1)
    session = Session(build(llm, sink, tts=FakeTTS(chunk_size=1)), sink)

    async def interrupt() -> None:
        while State.KONUSUYOR not in sink.states:
            await asyncio.sleep(0)
        await session.interrupt(active(session))

    task = asyncio.create_task(interrupt())
    await speak(session, "anlat")
    await task
    assert len(sink.cancelled) == 1
    assert sink.ended == []
    assert sink.outcomes == ["iptal"]


async def test_empty_answer_ends_turn_through_the_table() -> None:
    """§5'in `YANIT_BOŞ` çıkışı: tur `IDLE`'da biter, istisna yükselmez."""
    sink = Recorder()
    session = Session(build(FakeLLM([""]), sink), sink)
    await speak(session, "selam")
    assert session.state is State.IDLE
    assert State.KONUSUYOR not in sink.states
    assert sink.ended == []


async def test_empty_answer_is_not_silent() -> None:
    """Kural 13 + §14: sebep önce hata kanalından gider, durum sonra; iz `HATA`."""
    sink = Recorder()
    session = Session(build(FakeLLM([""]), sink), sink)
    await speak(session, "selam")
    assert len(sink.failed) == 1
    assert "empty_answer" in sink.failed[0][1]
    assert sink.outcomes == ["hata"]


# --- §15: yeniden oynatma ---------------------------------------------------------

PROSE = ["Ankara'da hava on sekiz derece."]
TOOL = ["<tool> hava --sehir Ankara", "Ankara'da on sekiz derece."]
APPROVAL = ["<tool> sil --id 3", "Üçüncü notu sildim."]


async def live(
    responses: list[str], *, answer: str | None = None
) -> tuple[Recorder, Recording]:
    """Bir turu gerçekten koşar ve yeniden oynatmak için gerekeni toplar."""
    sink = Recorder()
    llm = RecordingLLM(FakeLLM(responses))
    resolver_llm = FakeLLM(["ONAY"]) if answer is not None else FakeLLM()
    runner = build(llm, sink, resolver_llm=RecordingLLM(resolver_llm))
    session = Session(runner, sink)

    if answer is not None:

        async def reply() -> None:
            while State.ONAY_BEKLIYOR not in sink.states:
                await asyncio.sleep(0)
            await session.deliver(Segment(segment_id="s2", device_id=DEVICE, payload=answer))

        task = asyncio.create_task(reply())
        await session.deliver(Segment(segment_id="s1", device_id=DEVICE, payload="soru"))
        await task
    else:
        await session.deliver(Segment(segment_id="s1", device_id=DEVICE, payload="soru"))

    return sink, Recording(
        turn_id="t1",
        device_id=DEVICE,
        segment_id="s1",
        transcript="soru",
        responses=tuple(llm.responses),
        answers=() if answer is None else (answer,),
    )


async def test_prose_turn_replays_identically() -> None:
    sink, recording = await live(PROSE)

    result = await replay(recording, build)
    assert result.text.strip() == sink.spoken
    assert result.stages == tuple(sink.stages[1:])
    assert result.outcome == sink.outcomes[0]


async def test_tool_turn_replays_identically() -> None:
    """Aşama dizisi tool adını da taşıyor: aynı tool, aynı sırada çalışmış olmalı."""
    sink, recording = await live(TOOL)

    result = await replay(recording, build)
    assert result.text.strip() == sink.spoken == "Ankara'da on sekiz derece."
    assert "tool:hava" in result.stages
    assert result.stages == tuple(sink.stages[1:])
    assert "tool_running:hava" in result.progress


async def test_approval_turn_replays_without_a_user() -> None:
    """Onay yanıtı da kaydın parçası; yeniden koşuda karşıda kimse yok."""
    sink, recording = await live(APPROVAL, answer="evet")

    def with_resolver(llm: LLMClient, collector: Collector) -> Runner:
        return build(llm, collector, resolver_llm=FakeLLM(["ONAY"]))

    result = await replay(recording, with_resolver)
    assert result.text.strip() == sink.spoken
    assert result.progress.index("approval_needed") < result.progress.index("approved")
    assert result.outcome == "tamam"


async def test_replay_records_no_audio_input() -> None:
    """§15: ses kaydetmeden hata ayıklama. Kayıtta bayt değil transkript var."""
    _, recording = await live(PROSE)
    assert recording.transcript == "soru"
    assert all(isinstance(response, str) for response in recording.responses)


# --- bellek (§11) ---------------------------------------------------------------------


async def test_the_turn_writes_both_sides_of_the_conversation() -> None:
    """§11.1: kullanıcının cümlesi ve asistanın yanıtı geçmişe girer."""
    sink = Recorder()
    memory = FakeMemory()
    session = Session(build(FakeLLM(["Merhaba."]), sink, memory=memory), sink)
    await speak(session, "selam")
    assert memory.lines == [("user", "selam"), ("assistant", "Merhaba.")]


async def test_the_turn_writes_the_call_and_its_result() -> None:
    """Tool adımı geçmişe iki satır olarak girer: çağrı `assistant`, sonuç `tool`.

    2026-08-16'da değişti (Faz B). Öncesinde yalnızca adlar yazılıyordu (`[araç]` izi) ve
    sonuç atılıyordu; ölçüm o izin etkisiz, atmanın ise zararlı olduğunu gösterdi — veri
    geçmişte yalnızca asistanın cevabında kalınca bir tool'dan geldiği hiçbir yerde
    yazmıyor ve model onu kendi bilgisi sanıyordu (`docs/faz-b-bicim.md`).

    **Sonucun geçmişte olması testin konusu**, yan etkisi değil: `18` artık `tool`
    satırında bulunmalı.
    """
    sink = Recorder()
    memory = FakeMemory()
    session = Session(build(FakeLLM(TOOL), sink, memory=memory), sink)
    await speak(session, "hava nasıl")
    assert memory.lines == [
        ("user", "hava nasıl"),
        ("assistant", "<tool> hava --sehir Ankara"),
        ("tool", '{"derece": 18}'),
        ("assistant", "Ankara'da on sekiz derece."),
    ]


async def test_a_turn_without_tools_writes_no_trace() -> None:
    """Çağrı yoksa iz de yok: boş bir iz satırı, geçmişe olmayan bir olayı yazmak olurdu."""
    sink = Recorder()
    memory = FakeMemory()
    session = Session(build(FakeLLM(["Merhaba."]), sink, memory=memory), sink)
    await speak(session, "selam")
    assert [role for role, _ in memory.lines] == ["user", "assistant"]


async def test_a_cancelled_turn_writes_no_answer() -> None:
    """Kullanıcının duymadığı yarım cümleyi "asistan bunu söyledi" diye kaydetmek,
    geçmişe olmamış bir konuşma yazmak olurdu."""
    sink = Recorder()
    memory = FakeMemory()
    llm = FakeLLM(["Uzun uzun anlatıyorum. " * 20], chunk_size=1)
    session = Session(build(llm, sink, tts=FakeTTS(chunk_size=1), memory=memory), sink)

    async def interrupt() -> None:
        while State.KONUSUYOR not in sink.states:
            await asyncio.sleep(0)
        await session.interrupt(active(session))

    task = asyncio.create_task(interrupt())
    await speak(session, "anlat")
    await task
    assert memory.lines == [("user", "anlat")]


async def test_summary_history_and_facts_reach_the_prompt() -> None:
    """§8.1'in dizilimi: özet geçmişin önünde, olgular bağlam bloğunun içinde en sonda."""
    sink = Recorder()
    memory = FakeMemory(
        window=Window(
            summary="dün hava konuşuldu",
            history=(PromptMessage(role="user", content="dün ne dedim"),),
            facts="[hatırlananlar]\n- (Ali, 2026-08-01) kahveyi sade içer",
            trimmed=0,
        )
    )
    llm = FakeLLM(["Tamam."])
    session = Session(build(llm, sink, memory=memory), sink)
    await speak(session, "selam")

    contents = [message.content for message in llm.calls[0]]
    assert any("dün hava konuşuldu" in text for text in contents)
    assert "dün ne dedim" in contents
    block = next(text for text in contents if text.startswith("[bağlam]"))
    assert block.endswith("kahveyi sade içer")
    # Sabit kısım pencereye verilirken sistem promptu da içindeydi (§11.1).
    assert memory.fixed and "SİSTEM" in memory.fixed[0]


async def test_the_approval_answer_reaches_the_turn_through_the_actor() -> None:
    """Onay cevabı **aktör döngüsünden** geçerek turu bulmalı (2026-08-16 kilitlenmesi).

    Buradaki `speak()` gibi doğrudan `deliver()` çağıran testler bu yolu hiç geçmiyordu:
    `DeviceActor._loop` koşan turu bekliyor, tur segmenti bekliyor, sahibin yazdığı
    "evet" ikisinin arasındaki kuyrukta kalıyordu. Üretimde her onay zaman aşımına düştü.
    """
    sink = Recorder()
    llm = FakeLLM(["<tool> sil --id 3", "Sildim."])
    session = Session(build(llm, sink, resolver_llm=FakeLLM(["ONAY"])), sink)
    actor = session.actor(DEVICE)
    actor.start()
    try:
        first = Segment(segment_id="s1", device_id=DEVICE, payload="üçüncü notu sil")
        await actor.submit(first)
        while State.ONAY_BEKLIYOR not in sink.states:
            await asyncio.sleep(0)
        await actor.submit(Segment(segment_id="s2", device_id=DEVICE, payload="evet"))
        async with asyncio.timeout(5):
            while not sink.spoken.endswith("Sildim."):
                await asyncio.sleep(0)
    finally:
        await actor.stop()
