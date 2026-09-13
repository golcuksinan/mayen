"""Tarih/saat (§9.2, OKUMA). Kaynak: sistem saati.

**İkisi de `data`'da: yerel ve UTC.** Cümleyi model yazıyor ve elindeki tek şey `data` —
`speech` üretimde hiçbir yerden okunmuyor (bkz. `spec.ToolResult`). Yerel olan söylenmek
için, UTC olan bir sonraki adımda `task_create`'in `due` alanına gitmek için; o alan UTC
istiyor (`data/clock.py`'nin tek-biçim kuralı). Tek bir alan olsaydı biri diğerinin
yerine kullanılır ve saat dilimi sessizce kaybolurdu.

**"UTC" kelimesi konuşmadan çıktı** (2026-08-16, sahibin elle koşusu): asistan saati üç
saat geride ve "UTC" diyerek söylüyordu. Kullanıcının sorduğu şey duvardaki saat; dilim
adı ona bilgi vermiyor, yanlış saat ise doğrudan yanlış cevap.
"""

from collections.abc import Mapping

from mayen.data import clock
from mayen.policy.effects import Effect
from mayen.tools.spec import Tool, ToolContext, ToolResult


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    return ToolResult(
        ok=True,
        data={"local": clock.local(), "utc": clock.now()},
        speech=f"It is {clock.local()}.",
    )


TOOL = Tool(
    name="date_time",
    description="Şu anki tarih ve saati verir (yerel saat).",
    effect=Effect.OKUMA,
    timeout_seconds=1.0,
    handler=_run,
)
