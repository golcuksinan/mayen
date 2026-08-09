"""Kişiler — oluştur/güncelle (§9.2, YAZMA).

**Yeni kişi `BEKLEYEN` yazılır** (§10.3): sesle kayıt hiçbir yetki açmaz. Kademe
yükseltmek ayrı, geri alınamaz bir iştir (§10.4) ve bu tool'un işi değil — burada
yapılabilseydi, "rehbere ekle" cümlesi sessizce yetki veren bir cümle olurdu.

Eşleştirme tam ad karşılaştırmasıdır, harf katlamalı değil: Türkçe `I`/`ı` katlaması
yanlıştır ve yanlış eşleşen bir ad, var olan bir kişinin telefonunu değiştirir.
"""

from collections.abc import Mapping

from mayen.data.repositories.people import Tier
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, optional_text, text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    name = text(arguments, "name")
    phone = optional_text(arguments, "phone")
    existing = next(
        (person for person in context.people.list_all() if person.name == name), None
    )
    if existing is None:
        person = context.people.create(name, Tier.BEKLEYEN, phone=phone)
        speech = f"Added {person.name} to contacts."
    else:
        updated = context.people.update(existing.id, phone=phone)
        if updated is None:
            return ToolResult(ok=False, error=f"{name}: kişi güncellenemedi")
        person = updated
        speech = f"Updated {person.name}."
    return ToolResult(
        ok=True,
        data={"id": person.id, "name": person.name, "phone": person.phone},
        speech=speech,
    )


TOOL = Tool(
    name="contact_save",
    description="Rehbere kişi ekler ya da var olan kişinin telefonunu günceller.",
    effect=Effect.YAZMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(
        Arg("name", ArgType.STRING, "Kişinin adı"),
        Arg("phone", ArgType.STRING, "Telefon numarası", required=False),
    ),
)
