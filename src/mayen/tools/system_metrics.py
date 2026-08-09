"""Sistem metrikleri (§9.2, OKUMA).

`psutil` çağrıları bloklar; en uzunu CPU örneklemesi. Bu yüzden ölçüm bir iş parçacığına
alınıyor — olay döngüsünü kilitleyen bir tool, iptal edilebilirliği (Kural 12) ve tur
gecikmesini birlikte bozar.
"""

import asyncio
from collections.abc import Mapping

import psutil

from mayen.policy.effects import Effect
from mayen.tools.spec import Tool, ToolContext, ToolResult

_CPU_SAMPLE_SECONDS = 0.2


def _read() -> dict[str, object]:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=_CPU_SAMPLE_SECONDS),
        "memory_percent": memory.percent,
        "memory_available_gb": round(memory.available / 1024**3, 1),
        "disk_percent": disk.percent,
        "disk_free_gb": round(disk.free / 1024**3, 1),
    }


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    data = await asyncio.to_thread(_read)
    return ToolResult(
        ok=True,
        data=data,
        speech=(
            f"CPU {data['cpu_percent']} percent, memory {data['memory_percent']} percent, "
            f"{data['disk_free_gb']} gigabytes free on disk."
        ),
    )


TOOL = Tool(
    name="system_metrics",
    description="Makinenin CPU, bellek ve disk kullanımını verir.",
    effect=Effect.OKUMA,
    timeout_seconds=5.0,
    handler=_run,
)
