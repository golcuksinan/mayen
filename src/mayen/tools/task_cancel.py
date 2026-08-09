"""Zamanlanmış görev — iptal (§9.2, YAZMA).

`GERİ_ALINAMAZ` değil: iptal edilen görev satırda kalır, durumu `IPTAL` olur; yeniden
kurulabilir. §9.2 de bu satırı YAZMA sayıyor.
"""

from collections.abc import Mapping

from mayen.data.repositories.tasks import TaskStatus
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, number


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    task_id = number(arguments, "id")
    task = context.tasks.settle(task_id, TaskStatus.IPTAL)
    if task is None:
        return ToolResult(ok=False, error=f"{task_id}: bekleyen böyle bir görev yok")
    return ToolResult(ok=True, data={"id": task.id}, speech="Reminder cancelled.")


TOOL = Tool(
    name="task_cancel",
    description="Bekleyen bir zamanlanmış görevi numarasıyla iptal eder.",
    effect=Effect.YAZMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("id", ArgType.INTEGER, "İptal edilecek görevin numarası"),),
)
