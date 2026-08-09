"""Zamanlanmış görev — oluştur (§9.2, YAZMA).

Zaman damgası biçimi `data.clock`'unkiyle aynı olmak zorunda: iki biçim yazan iki yer,
kimsenin fark etmediği bozuk bir sıralama demektir. Bu yüzden burada doğrulanıyor —
geçersiz zaman modele geri beslenir, veritabanına yazılmaz.
"""

from collections.abc import Mapping
from datetime import datetime

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text

_KIND = "reminder"
_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    due_at = text(arguments, "due")
    try:
        datetime.strptime(due_at, _FORMAT)
    except ValueError:
        return ToolResult(
            ok=False, error=f"{due_at!r}: zaman 2026-08-09T14:03:11Z biçiminde olmalı"
        )
    message = text(arguments, "message")
    task = context.tasks.create(_KIND, {"message": message}, due_at)
    return ToolResult(
        ok=True,
        data={"id": task.id, "due_at": task.due_at, "message": message},
        speech=f"Reminder set for {task.due_at}.",
    )


TOOL = Tool(
    name="task_create",
    description="Belirtilen zamanda hatırlatılacak bir görev oluşturur.",
    effect=Effect.YAZMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(
        Arg("due", ArgType.STRING, "Zaman, UTC: 2026-08-09T14:03:11Z"),
        Arg("message", ArgType.STRING, "Hatırlatılacak metin", trailing=True),
    ),
)
