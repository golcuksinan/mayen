"""Henüz çalmamış hatırlatmaları vade sırasıyla listeler."""

from pydantic import BaseModel

from mayen.ports.tools import (
    Effect,
    Record,
    Sensitivity,
    Status,
    ToolContext,
    ToolResult,
    ToolSpec,
)

LOCAL_FORMAT = "%Y-%m-%d %H:%M"


class NoArgs(BaseModel):
    pass


async def run(_: NoArgs, ctx: ToolContext) -> ToolResult:
    # Her hatırlatma kendi hassasiyetini taşır; kimin okuyabileceğine yetki süzgeci bakar.
    records = [
        Record(
            t.sensitivity,
            {
                "id": t.id,
                "text": t.text,
                "due": t.due.astimezone().strftime(LOCAL_FORMAT),
                "priority": t.priority.value,
            },
        )
        for t in ctx.timers.pending()
    ]
    return ToolResult(Status.OK, records=records)


SPEC = ToolSpec(
    name="reminder_list",
    description="Lists the reminders that have not gone off yet.",
    args=NoArgs,
    effect=Effect.READ,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
