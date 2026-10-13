"""Notlarda metin arar; boş sorgu bütün notları döndürür."""

from pydantic import BaseModel, Field

from mayen.ports.tools import (
    Effect,
    Record,
    Sensitivity,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
)


class Args(BaseModel):
    query: str = Field("", description="The text to search for")


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    # Her not kendi hassasiyetini taşır; kimin okuyabileceğine yetki süzgeci karar verir.
    notes = ctx.notes.search(args.query)
    records = [Record(n.sensitivity, {"id": n.id, "text": n.text}) for n in notes]
    return ToolResult(Status.OK, records=records)


SPEC = ToolSpec(
    name="note_search",
    description="Searches the notes for a text; returns every note when the query is empty.",
    args=Args,
    effect=Effect.READ,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
