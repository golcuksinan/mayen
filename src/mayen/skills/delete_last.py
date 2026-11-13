"""Kişinin son isteğini ve Mayen'in ona cevabını kalıcı olarak siler (§11.4): sözler, olay
kaydındaki kopyaları ve ses kayıtları gider. Geri alınamaz; her seferinde onay ister (§10.3).

Sonucu söylenmez (§7): silineni anlatan bir cevap, onu yeniden söylemek olurdu.
"""

from pydantic import BaseModel

from mayen.ports.tools import Effect, Sensitivity, Status, ToolContext, ToolResult, ToolSpec


class NoArgs(BaseModel):
    pass


async def run(_: NoArgs, ctx: ToolContext) -> ToolResult:
    deleted = ctx.deleting.last()
    if not deleted:
        return ToolResult(Status.OK, {"deleted": 0})
    return ToolResult(Status.OK, {"turns": len(deleted.turns)}, relay=False)


SPEC = ToolSpec(
    name="delete_last",
    description="Permanently deletes the user's last request and Mayen's answer to it from "
    "the records. Only when the user asks to delete what was said.",
    args=NoArgs,
    effect=Effect.IRREVERSIBLE,
    sensitivity=Sensitivity.PERSONAL,
    sends_outside=False,
    timeout_s=10.0,
    run=run,
)
