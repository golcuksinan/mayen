"""Unut ve silin hattaki ve tool'daki yüzü (§11.4): canlı bağlamdan çıkarma, tool'ların
sözleşmesi ve yetkisi."""

import uuid
from datetime import timedelta
from typing import Any

from pipecat.processors.aggregators.llm_context import LLMContext

from fakes import T0, FakeClock, FakeErasing
from mayen.app.wiring import ToolCtx
from mayen.core.policy import ROLE_TABLE, decide
from mayen.core.turns import Turn, new_turn
from mayen.pipeline.forget import ContextTurns
from mayen.ports.forget import Chosen
from mayen.ports.tools import Caller, Confirmation, Role, Status, TurnFlags, Verdict
from mayen.ports.transcript import UtteranceId
from mayen.ports.triggers import Priority, Trigger, TriggerSource, TurnId
from mayen.skills import delete_last, delete_period, forget_last, forget_period

OWNER = Caller(Role.OWNER, "1", has_personal_device=True)


def turn() -> Turn:
    return new_turn(Trigger("s1", Priority.NORMAL, TriggerSource.TEXT, "", OWNER))


def said(text: str) -> Any:  # noqa: ANN401  # Pipecat'in mesaj tipi
    return {"role": "user", "content": text}


def context_with_turns(*texts: str) -> tuple[LLMContext, ContextTurns, list[Turn]]:
    """Her metin bir tur: kişinin sözü ve Mayen'in cevabı."""
    context = LLMContext()
    spans = ContextTurns()
    spans.bind(context)
    turns = []
    for text in texts:
        t = turn()
        spans.started(t)
        context.add_messages([said(text), said(f"→ {text}") | {"role": "assistant"}])
        turns.append(t)
    return context, spans, turns


def contents(context: LLMContext) -> list[str]:
    return [str(m["content"]) for m in context.messages]  # type: ignore[index]


def test_a_forgotten_turn_leaves_the_live_context_with_its_answer() -> None:
    context, spans, (_, second, third) = context_with_turns("bir", "iki", "üç")
    spans.drop(Chosen(turns=(second.id,)))
    assert contents(context) == ["bir", "→ bir", "üç", "→ üç"]
    # Yerleri kayar: sonra unutulan tur doğru mesajları götürür.
    spans.drop(Chosen(turns=(third.id,)))
    assert contents(context) == ["bir", "→ bir"]


def test_a_turn_from_another_session_or_a_session_without_turns_changes_nothing() -> None:
    context, spans, _ = context_with_turns("bir")
    spans.drop(Chosen(turns=(TurnId(uuid.uuid4()),)))
    assert contents(context) == ["bir", "→ bir"]
    empty = ContextTurns()
    empty.bind(LLMContext())
    empty.drop(Chosen(turns=(TurnId(uuid.uuid4()),)))  # turu olmayan oturum


def test_messages_before_the_first_turn_stay() -> None:
    context = LLMContext(messages=[said("önce") | {"role": "developer"}])
    spans = ContextTurns()
    spans.bind(context)
    t = turn()
    spans.started(t)
    context.add_messages([said("bir")])
    spans.drop(Chosen(turns=(t.id,)))
    assert contents(context) == ["önce"]


def ctx(
    forgetting: FakeErasing | None = None,
    deleting: FakeErasing | None = None,
    clock: FakeClock | None = None,
) -> ToolCtx:
    return ToolCtx(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        clock or FakeClock(),
        None,  # type: ignore[arg-type]
        None,
        None,
        OWNER,
        {},
        forgetting or FakeErasing(),
        deleting or FakeErasing(),
    )


async def test_forget_last_is_silent_only_when_something_was_forgotten() -> None:
    gone = FakeErasing(Chosen(turns=(TurnId(uuid.uuid4()),)))
    result = await forget_last.run(forget_last.NoArgs(), ctx(gone))
    assert (result.status, result.relay, gone.asked) == (Status.OK, False, [("last",)])
    # Unutacak bir şey yoksa model bunu söyler.
    nothing = await forget_last.run(forget_last.NoArgs(), ctx(FakeErasing()))
    assert (nothing.data, nothing.relay) == ({"forgotten": 0}, True)


async def test_forget_period_turns_minutes_into_a_span_ending_now() -> None:
    forgetting = FakeErasing(Chosen(turns=(TurnId(uuid.uuid4()),)))
    result = await forget_period.run(forget_period.Args(minutes=5), ctx(forgetting))
    assert result.relay is False
    assert forgetting.asked == [("period", T0 - timedelta(minutes=5), T0)]


async def test_forget_period_reads_local_times() -> None:
    forgetting = FakeErasing()
    args = forget_period.Args(since="2026-10-13 09:00", until="2026-10-13 10:30")
    await forget_period.run(args, ctx(forgetting))
    (_, since, until) = forgetting.asked[0]
    assert (until - since) == timedelta(minutes=90)
    assert since.astimezone().strftime("%H:%M") == "09:00"


async def test_forget_period_refuses_unclear_spans() -> None:
    cases = [
        forget_period.Args(),
        forget_period.Args(minutes=5, since="2026-10-13 09:00"),
        forget_period.Args(minutes=5, until="2026-10-13 09:00"),
        forget_period.Args(since="yarın"),
        forget_period.Args(since="2026-10-13 10:00", until="2026-10-13 09:00"),
    ]
    for args in cases:
        forgetting = FakeErasing()
        result = await forget_period.run(args, ctx(forgetting))
        assert result.status is Status.ERROR, args
        assert forgetting.asked == []


def test_only_the_owner_may_forget() -> None:
    # Unut ve sil yalnızca sahibindir (§11.4); misafir ve tanınmayan reddedilir.
    for spec in (forget_last.SPEC, forget_period.SPEC):
        for role, verdict in [
            (Role.OWNER, Verdict.ALLOW),
            (Role.ACQUAINTANCE, Verdict.DENY),
            (Role.UNKNOWN, Verdict.DENY),
        ]:
            caller = Caller(role, None, has_personal_device=False)
            assert decide(spec, caller, ROLE_TABLE, TurnFlags()).verdict is verdict


async def test_delete_uses_its_own_side_and_is_silent_when_something_went() -> None:
    gone = FakeErasing(Chosen(turns=(TurnId(uuid.uuid4()),)))
    result = await delete_last.run(delete_last.NoArgs(), ctx(deleting=gone))
    assert (result.status, result.relay, gone.asked) == (Status.OK, False, [("last",)])
    span = FakeErasing(Chosen(utterances=(UtteranceId(uuid.uuid4()),)))
    result = await delete_period.run(delete_period.Args(minutes=10), ctx(deleting=span))
    assert result.data == {"turns": 0, "utterances": 1}
    assert span.asked == [("period", T0 - timedelta(minutes=10), T0)]
    nothing = await delete_last.run(delete_last.NoArgs(), ctx())
    assert (nothing.data, nothing.relay) == ({"deleted": 0}, True)


async def test_delete_period_refuses_unclear_spans() -> None:
    for args in (delete_period.Args(), delete_period.Args(minutes=5, since="2026-10-13 09:00")):
        deleting = FakeErasing()
        result = await delete_period.run(args, ctx(deleting=deleting))
        assert result.status is Status.ERROR
        assert deleting.asked == []


def test_deleting_asks_the_owner_every_time_and_refuses_everyone_else() -> None:
    # Geri alınamaz: sahip için her seferinde onay, başkası için ret (§10.3, §11.4).
    for spec in (delete_last.SPEC, delete_period.SPEC):
        owner = decide(spec, OWNER, ROLE_TABLE, TurnFlags())
        assert (owner.verdict, owner.confirmation) == (Verdict.CONFIRM, Confirmation.INTENT)
        for role in (Role.ACQUAINTANCE, Role.UNKNOWN):
            caller = Caller(role, None, has_personal_device=False)
            assert decide(spec, caller, ROLE_TABLE, TurnFlags()).verdict is Verdict.DENY
