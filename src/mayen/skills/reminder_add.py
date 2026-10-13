"""Bir hatırlatma kurar: vaktinde Mayen kendiliğinden bir tur açar (§12)."""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec
from mayen.ports.triggers import Priority

LOCAL_FORMAT = "%Y-%m-%d %H:%M"


class Args(BaseModel):
    text: str = Field(description="What to remind, in the user's own words")
    at: str | None = Field(
        default=None,
        description="Local date and time as 'YYYY-MM-DD HH:MM'; give this or in_minutes",
    )
    in_minutes: float | None = Field(
        default=None, gt=0, description="Minutes from now; give this or at"
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="'urgent' only when the user says it must get through",
    )
    tolerance_minutes: float | None = Field(
        default=None,
        ge=0,
        description="How late it may still go off if Mayen was off at that time; "
        "only when the user says",
    )


async def run(args: Args, ctx: ToolContext) -> ToolResult:
    now = ctx.clock.now()
    if (args.at is None) == (args.in_minutes is None):
        return ToolResult(Status.ERROR, error="give exactly one of at and in_minutes")
    if args.in_minutes is not None:
        due = now + timedelta(minutes=args.in_minutes)
    else:
        assert args.at is not None
        try:
            # Dilimsiz zaman makinenin saat dilimindedir, `time` skill'inin verdiği gibi.
            due = datetime.strptime(args.at, LOCAL_FORMAT).astimezone()
        except ValueError:
            return ToolResult(Status.ERROR, error="at must look like 2026-10-13 15:30")
        if due <= now:
            return ToolResult(Status.ERROR, error=f"{args.at} is in the past")
    # Öncelik sırası kayıt, config, skill (§9.1); config'inki bağlamın varsayılanlarındadır.
    tolerance = args.tolerance_minutes
    if tolerance is None:
        tolerance = float(ctx.defaults["tolerance_minutes"])
    timer = ctx.timers.add(
        due, args.text, args.priority, tolerance * 60, SPEC.sensitivity, ctx.caller.person_id
    )
    return ToolResult(
        Status.OK, {"id": timer.id, "due": timer.due.astimezone().strftime(LOCAL_FORMAT)}
    )


SPEC = ToolSpec(
    name="reminder_add",
    description="Sets a reminder; at that time Mayen brings it up by itself.",
    args=Args,
    effect=Effect.WRITE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
    # Kaynağı olan bir değer değil, Claude'un seçimi: sahip config'te üzerine yazar.
    defaults={"tolerance_minutes": 30.0},
)
