"""Aktif pencereyi kapatır (GERİ_ALINAMAZ — onay ister).

Ayrı bir tool olmasının sebebi `window_action`'ın başlığında: etki sınıfı tool başınadır,
ve kapatmanın bedeli diğer pencere eylemlerinden farklı — kaydedilmemiş iş geri gelmez.
WoL'un `GERİ_ALINAMAZ` sayılmasıyla aynı ölçü: sonucu makinede kalıcı olan ve asistanın
geri alamayacağı bir şey.

Argümanı yok: eylem her zaman **etkin** pencere üzerinde. Hangi pencere olduğunu seçmek
Wayland'da pencere listesi ister; adaptörün başlığında yazılı olduğu gibi o yol bu makinede
KWin'e script yüklemekten geçiyor ve bilerek açılmadı.
"""

from collections.abc import Mapping

from mayen.adapters.errors import AdapterError
from mayen.policy.effects import Effect
from mayen.tools.spec import Tool, ToolContext, ToolResult
from mayen.tools.window_action import CLOSE


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    try:
        await context.desktop.window(CLOSE)
    except AdapterError as exc:
        return ToolResult(ok=False, error=str(exc))
    return ToolResult(ok=True, data={"eylem": CLOSE}, speech="Window closed.")


TOOL = Tool(
    name="window_close",
    description="Etkin pencereyi kapatır.",
    effect=Effect.GERI_ALINAMAZ,
    confirm="Close the active window?",
    timeout_seconds=5.0,
    handler=_run,
    args=(),
)
