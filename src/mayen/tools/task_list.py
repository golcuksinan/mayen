"""Zamanlanmış görev — listele (§9.2, OKUMA)."""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Tool, ToolContext, ToolResult


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    tasks = context.tasks.pending()
    if not tasks:
        return ToolResult(ok=True, data={"tasks": []}, speech="No pending reminders.")
    rows = [
        {"id": task.id, "due_at": task.due_at, "message": task.payload.get("message")}
        for task in tasks
    ]
    return ToolResult(
        ok=True,
        data={"tasks": rows},
        speech="; ".join(f"{row['id']}: {row['due_at']} {row['message']}" for row in rows),
    )


TOOL = Tool(
    name="task_list",
    description="Bekleyen zamanlanmış görevleri listeler.",
    effect=Effect.OKUMA,
    timeout_seconds=2.0,
    handler=_run,
)
