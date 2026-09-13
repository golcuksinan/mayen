"""Kalıcı bellek — kaydet (§11.3, YAZMA).

§11.3'ün belleği iki yoldan doluyordu: arka plan çıkarımı ve hiçbir şey. Kullanıcının
"şunu unutma" diyebildiği bir kapı yoktu; görme (`fact_list`) ve silme (`fact_forget`)
kapıları vardır ama yazma kapısı yalnızca modelin kendi çıkarımıydı.

**Olgu kişiye bağlanmıyor, ve bu bilinen bir eksik.** `ToolContext` süreç başına bir kez
kuruluyor (`main.py`), yani tool konuşanın kim olduğunu göremiyor; arka plan çıkarımı
bağlayabiliyor çünkü mesajın satırından okuyor. Bugün pratikte fark yok — §19.3 açık
olduğu sürece `person_id` zaten üretilmiyor (`MAYEN_ASSUME_OWNER`). Konuşmacı tanıma
gerçek olduğunda burası tura bağlı bir kimlik ister; o güne kadar boş bırakmak, olmayan
bir kimliği uydurmaktan doğru.
"""

from collections.abc import Mapping

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    fact = context.facts.create(text(arguments, "content"))
    return ToolResult(
        ok=True,
        data={"id": fact.id, "icerik": fact.content},
        speech="I will remember that.",
    )


TOOL = Tool(
    name="fact_save",
    description="Kalıcı olarak hatırlanmasını istediğin bir bilgiyi belleğe yazar.",
    effect=Effect.YAZMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("content", ArgType.STRING, "Hatırlanacak bilgi", trailing=True),),
)
