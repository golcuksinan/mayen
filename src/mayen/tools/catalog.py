"""§9.2 kataloğunun kurulduğu tek yer.

Tool eklemek: bir dosya yaz, buraya bir satır ekle. `builtin_registry()` her çağrıda yeni
bir defter kurar — modül düzeyinde tek bir global defter, testlerin birbirine sızmasının
ve "hangi tool ne zaman kaydoldu" sorusunun kaynağı olurdu.

**Henüz burada olmayan** — ses profili kaydet/sil (§9.2, §10.5). Kaydın kendisi ayrı bir
oturum durumu (`KAYIT`) ve birden fazla ses örneği istiyor; konuşmacı adaptörü tur akışına
bağlanmadan (P8) gövdesi yazılamaz.
"""

from mayen.tools import (
    contact_delete,
    contact_get,
    contact_save,
    course_schedule,
    date_time,
    note_create,
    note_delete,
    note_search,
    system_metrics,
    task_cancel,
    task_create,
    task_list,
    wake_on_lan,
    weather,
)
from mayen.tools.registry import Registry

_TOOLS = (
    date_time.TOOL,
    contact_get.TOOL,
    contact_save.TOOL,
    contact_delete.TOOL,
    note_search.TOOL,
    note_create.TOOL,
    note_delete.TOOL,
    course_schedule.TOOL,
    task_create.TOOL,
    task_list.TOOL,
    task_cancel.TOOL,
    weather.TOOL,
    system_metrics.TOOL,
    wake_on_lan.TOOL,
)


def builtin_registry() -> Registry:
    registry = Registry()
    for tool in _TOOLS:
        registry.register(tool)
    return registry
