"""Kalıcı bellek — listeleme (§11.3, OKUMA).

§11.3'ün son satırı: "kullanıcının göremediği ve silemediği bir bellek, hata ayıklanamaz
bir bellektir." Görme kapısı bu tool, silme kapısı `fact_forget`.

Kişi adı listede yazılı, çünkü olgu havuzu **ortak ve kişi etiketli**: kaynağı görünmeyen
bir olgu, "bunu ben mi söyledim" sorusunu cevapsız bırakır.
"""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Tool, ToolContext, ToolResult

_LIMIT = 50
"""Sesli okunacak bir listenin tavanı. Tamamını okumak dakikalarca sürerdi; en yeniler
alınıyor ve kaçının gösterildiği sonucun içinde yazılı (Kural 13: sessiz kesme yok)."""


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    facts = context.facts.list_all()
    total = len(facts)
    if not facts:
        return ToolResult(
            ok=True, data={"toplam": 0, "olgular": []}, speech="I remember nothing yet."
        )
    shown = facts[-_LIMIT:]
    names = {person.id: person.name for person in context.people.list_all()}
    rows = [
        {
            "id": fact.id,
            "kisi": names.get(fact.person_id) if fact.person_id is not None else None,
            "icerik": fact.content,
            "tarih": fact.created_at,
        }
        for fact in reversed(shown)
    ]
    return ToolResult(
        ok=True,
        data={"toplam": total, "gosterilen": len(rows), "olgular": rows},
        speech=f"I remember {total} things; showing {len(rows)}.",
    )


TOOL = Tool(
    name="fact_list",
    description="Bellekte tutulan kalıcı olguları, kaynağı ve tarihiyle listeler.",
    effect=Effect.OKUMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(),
)
