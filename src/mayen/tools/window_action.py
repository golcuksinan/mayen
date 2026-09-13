"""Aktif pencere — geri alınabilir eylemler (DIŞ).

**Kapatma burada değil, `window_close`'da.** Etki sınıfı tool başınadır, seçenek başına
değil: kapatmayı da bu tool'a koymak ya küçültmeyi de onaya sokardı (her seferinde
"emin misin") ya da kapatmayı onaysız bırakırdı — ikincisi kaydedilmemiş işi sessizce
götürür. Ayrım seçeneğin değil tool'un düzeyinde olmak zorunda.

Eylem `ArgType.ENUM`: geçerli kısayol adları adaptörde, gramerde de harfi harfine yazılı.
`Kill Window` da bir KWin kısayoludur ve listede olmadığı için erişilemez.
"""

from collections.abc import Mapping

from mayen.adapters.desktop import WINDOW_ACTIONS
from mayen.adapters.errors import AdapterError
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text

CLOSE = "close"
REVERSIBLE = tuple(action for action in WINDOW_ACTIONS if action != CLOSE)


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    action = text(arguments, "action")
    try:
        await context.desktop.window(action)
    except AdapterError as exc:
        return ToolResult(ok=False, error=str(exc))
    return ToolResult(
        ok=True, data={"eylem": action}, speech=f"Done: {action.replace('-', ' ')}."
    )


TOOL = Tool(
    name="window_action",
    description="Etkin pencere üzerinde geri alınabilir bir eylem uygular.",
    effect=Effect.DIS,
    timeout_seconds=5.0,
    handler=_run,
    args=(Arg("action", ArgType.ENUM, "Uygulanacak eylem", choices=REVERSIBLE),),
)
