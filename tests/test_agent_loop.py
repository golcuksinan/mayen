"""§8.2'nin ajan döngüsü."""

import asyncio
from collections.abc import Mapping

import pytest

from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.llm import NativeCall
from mayen.agent.calls import CallFormat
from mayen.agent.loop import AgentLoop, Approver, TextChunk, ToolDone, ToolStarted
from mayen.agent.prompt import ContextBlock, system_prompt
from mayen.policy.approval import PendingPlan
from mayen.policy.authority import Authority, Identity
from mayen.policy.effects import Effect
from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult

OWNER = Identity(authority=Authority.SAHIP, person_id=1)
GUEST = Identity(authority=Authority.KAYITLI_KISI, person_id=2)
CONTEXT = ContextBlock(now="2026-08-09T10:00:00Z")


@pytest.fixture
def registry() -> Registry:
    """İki tool: biri okuma, biri geri alınamaz — matrisin iki farklı hücresi."""

    async def echo(ctx: ToolContext, args: Mapping[str, object]) -> ToolResult:
        return ToolResult(ok=True, data={"sehir": args["sehir"]}, speech="on sekiz derece")

    async def wipe(ctx: ToolContext, args: Mapping[str, object]) -> ToolResult:
        return ToolResult(ok=True, data={"silindi": True})

    reg = Registry()
    reg.register(
        Tool(
            name="hava",
            description="hava durumunu söyler",
            effect=Effect.OKUMA,
            timeout_seconds=5,
            handler=echo,
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
    registry: Registry,
    llm: FakeLLM,
    *,
    max_steps: int = 3,
    max_corrections: int = 2,
) -> AgentLoop:
    return AgentLoop(
        llm=llm,
        registry=registry,
        tools=object.__new__(ToolContext),  # gövdeler bağlamı kullanmıyor
        call_format=CallFormat.CLI,
        max_steps=max_steps,
        max_corrections=max_corrections,
    )


def approver(*, approve: bool = True, seen: list[PendingPlan] | None = None) -> Approver:
    async def ask(plan: PendingPlan) -> bool:
        if seen is not None:
            seen.append(plan)
        return approve

    return ask


async def collect(
    loop: AgentLoop,
    user: str,
    identity: Identity = OWNER,
    approve: Approver | None = None,
) -> list[object]:
    return [
        event
        async for event in loop.run(
            "SİSTEM",
            identity=identity,
            context=CONTEXT,
            user=user,
            approve=approve if approve is not None else approver(),
        )
    ]


async def test_prose_answer_streams_without_a_tool(registry: Registry) -> None:
    llm = FakeLLM(["Merhaba, nasılsın?"], chunk_size=3)
    events = await collect(build(registry, llm), "selam")
    assert all(isinstance(e, TextChunk) for e in events)
    assert "".join(e.text for e in events if isinstance(e, TextChunk)) == "Merhaba, nasılsın?"


async def test_prose_branch_is_decided_before_the_whole_answer(registry: Registry) -> None:
    """§6: tampon önek kadar, bir cümle kadar değil — ilk parça sonu beklemeden çıkar."""
    llm = FakeLLM(["Merhaba dünya, bu uzun bir yanıt"], chunk_size=2)
    stream = build(registry, llm).run(
        "SİSTEM", identity=OWNER, context=CONTEXT, user="selam", approve=approver()
    )
    first = await anext(stream)
    assert isinstance(first, TextChunk)
    assert len(first.text) <= len("<tool> ")
    await stream.aclose()


async def test_tool_call_then_answer(registry: Registry) -> None:
    llm = FakeLLM(["<tool> hava --sehir Ankara", "Ankara'da on sekiz derece."])
    events = await collect(build(registry, llm), "hava nasıl")
    assert ToolStarted("hava") in events
    text = "".join(e.text for e in events if isinstance(e, TextChunk))
    assert text == "Ankara'da on sekiz derece."


async def test_tool_result_is_fed_back_on_the_same_prefix(registry: Registry) -> None:
    """§8.2: sonuç eklendikten sonraki çağrı ayrı bir istek değil, aynı öneğin devamı."""
    llm = FakeLLM(["<tool> hava --sehir Ankara", "on sekiz derece"])
    await collect(build(registry, llm), "hava nasıl")
    first, second = llm.calls
    assert second[: len(first)] == first
    assert second[-2].content == "<tool> hava --sehir Ankara"
    assert second[-1].role == "tool"
    assert "Ankara" in second[-1].content


async def test_denied_tool_is_fed_back_not_raised(registry: Registry) -> None:
    """§8.2: red bir istisna değil, modele geri beslenen gerekçe."""
    llm = FakeLLM(["<tool> sil --id 3", "Bunu yapamıyorum."])
    events = await collect(build(registry, llm), "üçüncü notu sil", identity=GUEST)
    assert "hata: yetki yok" in llm.calls[1][-1].content
    assert any(isinstance(e, TextChunk) for e in events)


async def test_approval_is_asked_for_irreversible_tools(registry: Registry) -> None:
    seen: list[PendingPlan] = []
    llm = FakeLLM(["<tool> sil --id 3", "Sildim."])
    await collect(build(registry, llm), "üçüncü notu sil", approve=approver(seen=seen))
    assert len(seen) == 1
    assert seen[0].tool == "sil"
    assert "3" in seen[0].spoken  # argümanlar açıkça okunur (§8.5 adım 3)


async def test_refused_approval_becomes_a_tool_result(registry: Registry) -> None:
    llm = FakeLLM(["<tool> sil --id 3", "Peki, silmedim."])
    await collect(build(registry, llm), "üçüncü notu sil", approve=approver(approve=False))
    assert "onaylamadı" in llm.calls[1][-1].content


async def test_read_tool_never_asks_for_approval(registry: Registry) -> None:
    seen: list[PendingPlan] = []
    llm = FakeLLM(["<tool> hava --sehir Ankara", "on sekiz"])
    await collect(build(registry, llm), "hava nasıl", approve=approver(seen=seen))
    assert seen == []


async def test_tool_timeout_is_a_result_not_an_error() -> None:
    """§8.2: zaman aşımı modele geri beslenir; tur patlamaz."""

    async def hangs(ctx: ToolContext, args: Mapping[str, object]) -> ToolResult:
        await asyncio.sleep(10)
        raise AssertionError("buraya gelinmemeli")

    reg = Registry()
    reg.register(
        Tool(
            name="yavas",
            description="asla dönmez",
            effect=Effect.OKUMA,
            timeout_seconds=0.01,
            handler=hangs,
        )
    )
    llm = FakeLLM(["<tool> yavas", "Şu an ulaşamadım."])
    events = await collect(build(reg, llm), "dene")
    assert "zaman aşımı" in llm.calls[1][-1].content
    assert any(isinstance(e, TextChunk) for e in events)


async def test_max_steps_ends_with_an_answer_not_silence(registry: Registry) -> None:
    """§8.2: sınıra ulaşılırsa eldeki sonuçlarla yanıt üretilir."""
    llm = FakeLLM(
        [
            "<tool> hava --sehir Ankara",
            "<tool> hava --sehir İzmir",
            "Elimdekiyle şunu söyleyebilirim.",
        ]
    )
    events = await collect(build(registry, llm, max_steps=2), "hava nasıl")
    text = "".join(e.text for e in events if isinstance(e, TextChunk))
    assert text == "Elimdekiyle şunu söyleyebilirim."
    assert len(llm.calls) == 3


async def test_final_call_cannot_produce_a_tool_call(registry: Registry) -> None:
    """Sınırdaki üretim tool dalı **kapalı** gramerle yapılır."""
    llm = FakeLLM(["<tool> hava --sehir Ankara", "yeter"])
    await collect(build(registry, llm, max_steps=1), "hava nasıl")
    assert "tool-call" not in (llm.grammars[1] or "")


async def test_unknown_tool_is_fed_back_and_corrected(registry: Registry) -> None:
    """§8.3: bozuk çağrı modele geri beslenir, ikinci deneme çalışır."""
    llm = FakeLLM(["<tool> ucmayan --sehir Ankara", "<tool> hava --sehir Ankara", "on sekiz"])
    events = await collect(build(registry, llm), "hava nasıl")
    assert "defterde böyle bir tool yok" in llm.calls[1][-1].content
    assert ToolStarted("hava") in events
    assert "".join(e.text for e in events if isinstance(e, TextChunk)) == "on sekiz"


async def test_invalid_argument_feedback_carries_usage(registry: Registry) -> None:
    """Modelin yeniden görmesi gereken şey imza: `usage()` geri beslemenin içinde."""
    llm = FakeLLM(["<tool> sil --id abc", "<tool> sil --id 3", "Sildim."])
    await collect(build(registry, llm), "üçüncü notu sil")
    feedback = llm.calls[1][-1].content
    assert "hata:" in feedback
    assert registry.get("sil").usage() in feedback


async def test_correction_does_not_spend_a_step(registry: Registry) -> None:
    """`MAX_ADIM` tool sayısı; düzeltme turu ondan düşmez."""
    llm = FakeLLM(["<tool> ucmayan", "<tool> hava --sehir Ankara", "on sekiz"])
    events = await collect(build(registry, llm, max_steps=1), "hava nasıl")
    assert ToolStarted("hava") in events


async def test_correction_ceiling_ends_with_an_answer_not_an_error(registry: Registry) -> None:
    """Tavan aşılınca tur ölmüyor: düz metin dalıyla kapanıyor (Kural 13'e rağmen sessiz
    değil — olay günlüğe yazılıyor ve modele söyleniyor)."""
    llm = FakeLLM(["<tool> ucmayan", "<tool> ucmayan", "Bunu yapamadım."])
    events = await collect(build(registry, llm, max_corrections=1), "dene")
    assert "".join(e.text for e in events if isinstance(e, TextChunk)) == "Bunu yapamadım."
    assert not any(isinstance(e, ToolStarted) for e in events)
    assert "tool-call" not in (llm.grammars[2] or "")


async def test_zero_corrections_still_answers(registry: Registry) -> None:
    llm = FakeLLM(["<tool> ucmayan", "Bunu yapamadım."])
    events = await collect(build(registry, llm, max_corrections=0), "dene")
    assert any(isinstance(e, TextChunk) for e in events)


async def test_max_steps_below_one_is_rejected(registry: Registry) -> None:
    with pytest.raises(ValueError):
        build(registry, FakeLLM(), max_steps=0)


async def test_negative_corrections_is_rejected(registry: Registry) -> None:
    with pytest.raises(ValueError):
        build(registry, FakeLLM(), max_corrections=-1)


async def test_system_prompt_reaches_the_model(registry: Registry) -> None:
    llm = FakeLLM(["merhaba"])
    system = system_prompt(registry, CallFormat.CLI, role="ROL")
    loop = build(registry, llm)
    async for _ in loop.run(
        system, identity=OWNER, context=CONTEXT, user="selam", approve=approver()
    ):
        pass
    assert llm.calls[0][0].content == system


# --- Yerel çağrı biçimi (CallFormat.YEREL, Faz B/2) ---------------------------------


def native(registry: Registry, llm: FakeLLM, *, max_steps: int = 3) -> AgentLoop:
    return AgentLoop(
        llm=llm,
        registry=registry,
        tools=object.__new__(ToolContext),
        call_format=CallFormat.YEREL,
        max_steps=max_steps,
        max_corrections=2,
    )


def _name(schema: dict[str, object]) -> object:
    function = schema["function"]
    assert isinstance(function, dict)
    return function["name"]


async def _events(loop: AgentLoop) -> list[object]:
    return [
        event
        async for event in loop.run(
            "önek", identity=OWNER, context=CONTEXT, user="hava nasıl", approve=approver()
        )
    ]


async def test_the_model_can_speak_and_call_in_the_same_generation(registry: Registry) -> None:
    """Yerel biçimin var olma sebebi. Metin biçimlerinde bu imkânsız (§6/C3) ve model
    çağrıyı düz metnin içinde taklit ediyordu."""
    llm = FakeLLM(["Bakıyorum.", "On sekiz derece."])
    llm.queue_native(NativeCall(name="hava", arguments={"sehir": "Denizli"}))
    events = await _events(native(registry, llm))

    said = "".join(e.text for e in events if isinstance(e, TextChunk))
    assert said.startswith("Bakıyorum.")
    assert [e.name for e in events if isinstance(e, ToolStarted)] == ["hava"]


async def test_the_call_is_kept_out_of_the_assistant_text(registry: Registry) -> None:
    """Çağrı `tool_calls`'ta duruyor, `content`'te değil: metne çevrilirse model bir
    sonraki turda biçimi kopyalıyor (`docs/faz-b-yerel.md`)."""
    llm = FakeLLM(["", "On sekiz derece."])
    call = NativeCall(name="hava", arguments={"sehir": "Denizli"})
    llm.queue_native(call)
    events = await _events(native(registry, llm))

    done = next(e for e in events if isinstance(e, ToolDone))
    assert done.tool_calls == (call,)
    assert "hava" not in done.call_text


async def test_the_catalog_travels_as_a_schema(registry: Registry) -> None:
    """Katalog `tools` alanından gidiyor; sistem promptunda ikinci bir kopyası yok."""
    llm = FakeLLM(["Tamam."])
    await _events(native(registry, llm))
    names = [_name(tool) for tool in llm.tool_schemas[0]]
    assert names == ["hava", "sil"]


async def test_typed_arguments_still_pass_through_validate(registry: Registry) -> None:
    """Şema tipli değer üretiyor (`id` bir `int`), `validate` metin bekliyor; esneyen
    taraf `from_native` (§9.1: doğrulama tek noktada kalıyor)."""
    llm = FakeLLM(["", "Silindi."])
    llm.queue_native(NativeCall(name="sil", arguments={"id": 7}))
    events = await _events(native(registry, llm))
    assert [e.name for e in events if isinstance(e, ToolStarted)] == ["sil"]


async def test_an_unknown_tool_is_fed_back_not_raised(registry: Registry) -> None:
    """§8.3: bozuk çağrı modele geri beslenir. Gramerde uydurulan ad üretilemezdi;
    şemada üretilebilir, yani bu dal yerel biçimde gerçekten koşuyor."""
    # İkinci üretim düzeltme turu: model çağrısız cevap veriyor ve tur orada bitiyor.
    llm = FakeLLM(["", "Yapamadım."])
    llm.queue_native(NativeCall(name="yok_boyle_bir_sey", arguments={}))
    events = await _events(native(registry, llm))
    assert not [e for e in events if isinstance(e, ToolStarted)]
    assert "".join(e.text for e in events if isinstance(e, TextChunk))
