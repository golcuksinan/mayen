"""Kişiler — sil (§9.2, GERİ_ALINAMAZ; onay ister).

Onayı bu dosya sormaz: etki sınıfı bildirilir, kararı `policy.authorize()` verir (Kural 4).
"""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    
    name = text(arguments, "name")
    person = next((row for row in context.people.list_all() if row.name == name), None)
    # contact_delete.py -> _run başında:
    print(f"DEBUG TOOL ÇALIŞTI: name={name!r}, rehberdekiler={[r.name for r in context.people.list_all()]}")
    if person is None:
        return ToolResult(ok=False, error=f"{name}: rehberde böyle bir kişi yok")
    if not context.people.delete(person.id):
        return ToolResult(ok=False, error=f"{name}: silinemedi")
    return ToolResult(ok=True, data={"id": person.id, "name": name}, speech=f"Deleted {name}.")


TOOL = Tool(
    name="contact_delete",
    description="Rehberden bir kişiyi siler.",
    effect=Effect.GERI_ALINAMAZ,
    confirm="Remove {name} from contacts?",
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("name", ArgType.STRING, "Silinecek kişinin adı"),),
)
