"""§9.2 kataloğunun kurulduğu tek yer.

Tool eklemek: bir dosya yaz, buraya bir satır ekle. `builtin_registry()` her çağrıda yeni
bir defter kurar — modül düzeyinde tek bir global defter, testlerin birbirine sızmasının
ve "hangi tool ne zaman kaydoldu" sorusunun kaynağı olurdu.

**Henüz burada olmayan** — ses profili kaydet/sil (§9.2, §10.5). Kaydın kendisi ayrı bir
oturum durumu (`KAYIT`) ve birden fazla ses örneği istiyor; konuşmacı adaptörü tur akışına
bağlanmadan (P8) gövdesi yazılamaz.
"""

from mayen.config import Config
from mayen.tools import (
    app_launch,
    contact_delete,
    contact_get,
    contact_save,
    course_schedule,
    date_time,
    fact_forget,
    fact_list,
    fact_save,
    media_control,
    note_create,
    note_delete,
    note_search,
    system_metrics,
    task_cancel,
    task_create,
    task_list,
    volume,
    wake_on_lan,
    weather,
    window_action,
    window_close,
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
    fact_list.TOOL,
    fact_save.TOOL,
    fact_forget.TOOL,
    wake_on_lan.TOOL,
    volume.TOOL,
    media_control.TOOL,
    window_action.TOOL,
    window_close.TOOL,
)


def builtin_registry(config: Config | None = None) -> Registry:
    """§9.2'nin defteri. Yapılandırma verilirse ona bağlı tool'lar da kurulur.

    `app_launch` bir sabit değil: açılabilir uygulamaların adları gramere seçenek olarak
    giriyor, çünkü modelin göremediği bir izin listesi kullanılamıyor (gerekçesi o
    dosyanın başlığında). Yapılandırma yoksa ya da liste boşsa **tool da yok** — hiçbir
    şey açamayan bir tool katalogda yalnızca token tutardı.
    """
    registry = Registry()
    for tool in _TOOLS:
        registry.register(tool)
    launcher = app_launch.build(sorted(config.apps)) if config is not None else None
    if launcher is not None:
        registry.register(launcher)
    return registry
