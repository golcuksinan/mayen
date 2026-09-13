"""Kalıcı bellek — silme (§11.3, GERİ_ALINAMAZ).

`GERİ_ALINAMAZ`, çünkü silinen olgunun geri getirileceği bir yer yok: satır gider ve onu
üreten konuşma çoktan özetlenmiş olabilir. §10.2'ye göre bu, sahipte bile onay ister —
"unut şunu" cümlesi yanlış anlaşıldığında geri alınamayacak tek bellek işlemi bu.

Numara `fact_list`'ten geliyor: içerikten silmek, benzeyen iki olgudan yanlış olanı silmeye
açık kapı bırakırdı.
"""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, number


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    fact_id = number(arguments, "id")
    if not context.facts.delete(fact_id):
        return ToolResult(ok=False, error=f"{fact_id}: böyle bir olgu yok")
    return ToolResult(ok=True, data={"id": fact_id}, speech="Forgotten.")


TOOL = Tool(
    name="fact_forget",
    description="Bellekteki bir olguyu numarasıyla siler.",
    effect=Effect.GERI_ALINAMAZ,
    confirm="Forget stored fact {id}?",
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("id", ArgType.INTEGER, "Silinecek olgunun numarası"),),
)
