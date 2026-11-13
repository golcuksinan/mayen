"""Kişinin son isteğini ve Mayen'in ona cevabını unutur (§11.4): silinmez, ama Mayen onu bir
daha hiçbir yoldan görmez.

Argümanı yoktur: "son söylediğim" ile aralık aynı tool'da dururken model boş kalması gereken
süreyi doldurup son turu bir aralığa çeviriyordu. Sonucu söylenmez (§7, "Sessiz kal"):
unutulanı anlatan bir cevap, onu yeniden söylemek olurdu.
"""

from pydantic import BaseModel

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class NoArgs(BaseModel):
    pass


async def run(_: NoArgs, ctx: ToolContext) -> ToolResult:
    forgotten = ctx.forgetting.last()
    if not forgotten:
        return ToolResult(Status.OK, {"forgotten": 0})
    return ToolResult(Status.OK, {"turns": len(forgotten.turns)}, relay=False)


SPEC = ToolSpec(
    name="forget_last",
    description="Forgets the user's last request and Mayen's answer to it: it stays recorded, "
    "but Mayen never sees it again. Only when the user asks to forget.",
    args=NoArgs,
    effect=Effect.WRITE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=5.0,
    run=run,
)
