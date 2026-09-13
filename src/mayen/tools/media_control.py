"""Medya oynatıcısı — oynat/duraklat/atla (DIŞ).

Eylem **sayılı seçenek** (`ArgType.ENUM`): gramerde harfi harfine alternatif, yani
geçersiz bir eylem üretilemez. Serbest metin olsaydı model `duraklat`, `pause`,
`pause music` arasında seçim yapardı ve gövde bu üçünü elle eşlemek zorunda kalırdı.

Hangi oynatıcının etkilendiği sonuçta yazılı: birden çok MPRIS oynatıcısı açıkken
adaptör ilkini seçiyor ve "hangisini duraklattım" sorusunun cevabının kaybolmaması gerekiyor.
"""

from collections.abc import Mapping

from mayen.adapters.desktop import MEDIA_ACTIONS
from mayen.adapters.errors import AdapterError
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    action = text(arguments, "action")
    try:
        player = await context.desktop.media(action)
    except AdapterError as exc:
        return ToolResult(ok=False, error=str(exc))
    return ToolResult(
        ok=True,
        data={"eylem": action, "oynatici": player},
        speech=f"{action.replace('-', ' ').capitalize()} on {player}.",
    )


TOOL = Tool(
    name="media_control",
    description="Çalan medyayı denetler.",
    effect=Effect.DIS,
    timeout_seconds=5.0,
    handler=_run,
    args=(
        Arg(
            "action",
            ArgType.ENUM,
            "Uygulanacak eylem",
            choices=tuple(MEDIA_ACTIONS),
        ),
    ),
)
