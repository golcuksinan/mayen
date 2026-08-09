"""Ders programı (§9.2, OKUMA). Kaynak: depodaki program dosyasından yüklenen tablo (§19.8).

Dönem argüman değil, bağlamdan gelir: model hangi dönemde olunduğunu bilmez ve tahmin
etmesi istenmez.
"""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, optional_number

_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    day = optional_number(arguments, "day")
    if day is not None and not 1 <= day <= 7:
        return ToolResult(ok=False, error=f"{day}: gün 1 (Pazartesi) ile 7 (Pazar) arasında")
    sessions = (
        context.courses.for_term(context.course_term)
        if day is None
        else context.courses.for_day(context.course_term, day)
    )
    if not sessions:
        return ToolResult(ok=True, data={"sessions": []}, speech="No classes scheduled.")
    return ToolResult(
        ok=True,
        data={
            "sessions": [
                {
                    "course_code": session.course_code,
                    "title": session.title,
                    "day_of_week": session.day_of_week,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "location": session.location,
                }
                for session in sessions
            ]
        },
        speech="; ".join(
            f"{_DAYS[session.day_of_week - 1]} {session.start_time}-{session.end_time} "
            f"{session.title}" + (f" at {session.location}" if session.location else "")
            for session in sessions
        ),
    )


TOOL = Tool(
    name="course_schedule",
    description="Ders programını verir; gün verilirse yalnızca o günü.",
    effect=Effect.OKUMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("day", ArgType.INTEGER, "Haftanın günü, 1=Pazartesi … 7=Pazar", required=False),),
)
