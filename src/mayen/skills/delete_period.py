"""Bir zaman aralığında söylenen her şeyi kalıcı olarak siler (§11.4): turlar, tur dışında
duyulan sözler, olay kaydındaki kopyaları ve ses kayıtları. Geri alınamaz; her seferinde onay
ister (§10.3).

Sonucu söylenmez (§7): silineni anlatan bir cevap, onu yeniden söylemek olurdu.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec

LOCAL_FORMAT = "%Y-%m-%d %H:%M"


class Args(BaseModel):
    minutes: float | None = Field(
        default=None, gt=0, description="The last this many minutes; give this or since"
    )
    since: str | None = Field(
        default=None,
        description="Local start time as 'YYYY-MM-DD HH:MM'; give this or minutes",
    )
    until: str | None = Field(
        default=None,
        description="Local end time as 'YYYY-MM-DD HH:MM', only with since; omit for now",
    )


def _local(text: str) -> datetime:
    # Dilimsiz zaman makinenin saat dilimindedir, `time` skill'inin verdiği gibi.
    return datetime.strptime(text, LOCAL_FORMAT).astimezone()


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    if (args.minutes is None) == (args.since is None):
        return ToolResult(Status.ERROR, error="give exactly one of minutes and since")
    if args.until is not None and args.since is None:
        return ToolResult(Status.ERROR, error="until needs since")
    now = ctx.clock.now()
    try:
        since = (
            now - timedelta(minutes=args.minutes)
            if args.minutes is not None
            else _local(args.since or "")
        )
        until = now if args.until is None else _local(args.until)
    except ValueError:
        return ToolResult(Status.ERROR, error="times must look like 2026-10-13 15:30")
    if since >= until:
        return ToolResult(Status.ERROR, error="the start must be before the end")
    deleted = ctx.deleting.period(since, until)
    if not deleted:
        return ToolResult(Status.OK, {"deleted": 0})
    return ToolResult(
        Status.OK,
        {"turns": len(deleted.turns), "utterances": len(deleted.utterances)},
        relay=False,
    )


SPEC = ToolSpec(
    name="delete_period",
    description="Permanently deletes everything said in a span of time from the records. Only "
    "when the user asks to delete what was said.",
    args=Args,
    effect=Effect.IRREVERSIBLE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=10.0,
    run=run,
)
