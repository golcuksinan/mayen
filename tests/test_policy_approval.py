"""§8.5 onay akışı testleri."""

import pytest

from mayen.adapters.fakes.llm import FakeLLM
from mayen.policy.approval import (
    GRAMMAR,
    ApprovalFlow,
    ApprovalResolver,
    Outcome,
    PendingPlan,
    Resolution,
    ResolverError,
    needs_approval,
)
from mayen.policy.authority import Authority, Identity
from mayen.policy.effects import Effect

PLAN = PendingPlan(tool="kisiler_sil", spoken="Ahmet'i rehberden sileceğim, onaylıyor musun?")


def flow(llm: FakeLLM) -> ApprovalFlow:
    return ApprovalFlow(PLAN, ApprovalResolver(llm), timeout_seconds=20.0)


def test_only_irreversible_asks_for_approval() -> None:
    owner = Identity(Authority.SAHIP)
    assert needs_approval(owner, Effect.GERI_ALINAMAZ)
    assert not needs_approval(owner, Effect.YAZMA)
    # Reddedilen bir işlem onaya da çıkmaz: kayıtlı kişiye silme sorusu hiç sorulmaz.
    assert not needs_approval(Identity(Authority.KAYITLI_KISI), Effect.GERI_ALINAMAZ)


async def test_resolver_uses_constrained_output() -> None:
    llm = FakeLLM(["ONAY"])
    assert await ApprovalResolver(llm).resolve("evet, sil") is Resolution.ONAY
    assert llm.grammars == [GRAMMAR]


async def test_resolver_sees_the_segment_verbatim() -> None:
    llm = FakeLLM(["RED"])
    await ApprovalResolver(llm).resolve("hayır, vazgeçtim")
    assert llm.calls[0][-1].content == "hayır, vazgeçtim"


async def test_off_grammar_answer_raises() -> None:
    # Kural 13: yutulmaz. BELİRSİZ de sayılmaz — bozuk servis kararsızlık değildir.
    with pytest.raises(ResolverError):
        await ApprovalResolver(FakeLLM(["tabii ki"])).resolve("olur")


async def test_approval_approves() -> None:
    assert await flow(FakeLLM(["ONAY"])).resolve_segment("evet") is Outcome.ONAYLANDI


async def test_rejection_rejects() -> None:
    assert await flow(FakeLLM(["RED"])).resolve_segment("hayır") is Outcome.REDDEDILDI


async def test_conditional_sentence_is_not_approval() -> None:
    # "Tamam ama önce hava durumu" — anahtar kelime araması olsaydı onay sayılırdı.
    llm = FakeLLM(["BELİRSİZ"])
    assert await flow(llm).resolve_segment("tamam ama önce hava durumu") is Outcome.TEKRAR_SOR


async def test_second_unclear_answer_cancels() -> None:
    # §8.5 adım 5: bir kez daha sorulur, yine belirsizse iptal.
    f = flow(FakeLLM(["BELİRSİZ", "BELİRSİZ"]))
    assert await f.resolve_segment("hmm") is Outcome.TEKRAR_SOR
    assert await f.resolve_segment("bilmem") is Outcome.REDDEDILDI


async def test_unclear_then_clear_answer_is_honoured() -> None:
    f = flow(FakeLLM(["BELİRSİZ", "ONAY"]))
    assert await f.resolve_segment("hmm") is Outcome.TEKRAR_SOR
    assert await f.resolve_segment("evet sil") is Outcome.ONAYLANDI


def test_timeout_is_denial() -> None:
    assert flow(FakeLLM()).timed_out() is Outcome.REDDEDILDI


def test_timeout_has_no_invented_default() -> None:
    # Doküman bir süre vermiyor; süreyi çağıran verir.
    with pytest.raises(TypeError):
        ApprovalFlow(PLAN, ApprovalResolver(FakeLLM()))  # type: ignore[call-arg]
