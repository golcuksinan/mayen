"""Uygulama açar (DIŞ).

**Model komut yazmaz, listeden ad seçer** (Değişmez 8). Açılabilir uygulamalar
yapılandırmadaki ad → argv dosyasından gelir (`MAYEN_APPS_PATH`); WoL'un ham MAC adresini
reddetmesiyle bire bir aynı gerekçe — modelin yazabildiği bir komut, listenin dışındaki
her şeyi çalıştırabilirdi. Kabuk hiç devreye girmiyor: argv doğrudan `exec`'e gidiyor.

**Ad `ENUM` ve seçenekler yapılandırmadan geliyor**, yani tool bir sabit değil, defter
kurulurken üretiliyor. Bunun sebebi ölçülmüş bir başarısızlık: liste yalnızca gövdede
doğrulanırken katalogda "yapılandırmada tanımlı bir uygulama" yazıyordu ve model hangi
adların tanımlı olduğunu göremediği için **hiç denemeden** "tanımlı bir tarayıcım yok"
dedi. Bir izin listesi, ona sorulanı yapabilmek için görünür olmak zorunda.

**Hiç uygulama tanımlı değilse tool kataloğa hiç girmiyor.** Boş bir seçenek listesi
üretilemez; ama asıl sebep o değil: hiçbir şey açamayan bir tool, katalogda yer ve token
tutup modele yapamayacağı bir şeyi vaat ederdi.

"Açıldı" demek "çalışıyor" demek değil: süreç başlatılıyor, sonucu beklenmiyor. Konuşulan
cümle de o yüzden bunu söylüyor (`wake_on_lan`'ın aynı ayrımı).
"""

from collections.abc import Mapping, Sequence

from mayen.adapters.errors import AdapterError
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    name = text(arguments, "name")
    argv = context.config.apps.get(name)
    if argv is None:
        # Gramer bunu üretemez ama gramer bir güvenlik sınırı değil (Değişmez 4): asıl
        # kapı burası. Yapılandırma yeniden yüklendiğinde defterin eskimesi de mümkün.
        known = ", ".join(sorted(context.config.apps)) or "yok"
        return ToolResult(
            ok=False, error=f"{name}: tanımlı uygulama değil. Tanımlılar: {known}"
        )
    try:
        await context.desktop.launch(argv)
    except AdapterError as exc:
        return ToolResult(ok=False, error=str(exc))
    return ToolResult(ok=True, data={"uygulama": name}, speech=f"Launching {name}.")


def build(names: Sequence[str]) -> Tool | None:
    """Tanımlı uygulama adlarından tool'u üretir; ad yoksa tool da yok."""
    if not names:
        return None
    return Tool(
        name="app_launch",
        description="Yapılandırmada tanımlı bir uygulamayı açar.",
        effect=Effect.DIS,
        timeout_seconds=5.0,
        handler=_run,
        args=(Arg("name", ArgType.ENUM, "Açılacak uygulama", choices=tuple(names)),),
    )
