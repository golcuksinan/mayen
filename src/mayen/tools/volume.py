"""Ses seviyesi — oku/ayarla (DIŞ).

**Tek tool, isteğe bağlı alan.** `contact_get`'in gerekçesinin aynısı: ayrı bir okuma
tool'u kataloğu büyütür ve modele "oku mu yaz mı" diye ikinci bir seçim ekler. Alan
verilmezse seviye okunur, verilirse ayarlanır.

**Etki `DIŞ`, okuma için de.** Etki sınıfı tool başınadır ve tool'un yapabildiği en güçlü
şeyi anlatmak zorundadır; okumayı gerekçe gösterip `OKUMA` demek, yetki kararını tool'un
argümanına bağlamak olurdu — §9.1'in "ad'a göre istisna yok" kuralının argüman hâli.

Aralık kodda sınırlanıyor. Gramer `cli-integer`'ı sınırsız üretebilir ve %5000 bir yazım
hatası değil, duyulur bir kaza.
"""

from collections.abc import Mapping

from mayen.adapters.errors import AdapterError
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, optional_number

MAX_LEVEL = 100


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    level = optional_number(arguments, "level")
    try:
        if level is None:
            current = await context.desktop.volume()
            return ToolResult(
                ok=True, data={"seviye": current}, speech=f"Volume is at {current} percent."
            )
        if not 0 <= level <= MAX_LEVEL:
            return ToolResult(ok=False, error=f"seviye 0 ile {MAX_LEVEL} arasında olmalı")
        await context.desktop.set_volume(level)
    except AdapterError as exc:
        return ToolResult(ok=False, error=str(exc))
    return ToolResult(ok=True, data={"seviye": level}, speech=f"Volume set to {level} percent.")


TOOL = Tool(
    name="volume",
    description="Ses seviyesini söyler; seviye verilirse onu ayarlar.",
    effect=Effect.DIS,
    timeout_seconds=5.0,
    handler=_run,
    args=(Arg("level", ArgType.INTEGER, "Yüzde 0-100", required=False),),
)
