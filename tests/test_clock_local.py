"""Konuşulan saat yerel, saklanan saat UTC (2026-08-16).

Sahibin elle koşusunda asistan saati üç saat geride ve "UTC" diyerek söylüyordu. Depo
biçimi doğruydu ve öyle kalmalı (`clock.FORMAT`, tek biçim kuralı); yanlış olan sunum
kenarıydı. Bu dosya ikisinin **ayrı kaldığını** kilitliyor — birleştikleri gün sıralama
sessizce bozulur, ki modül başlığının uyarısı tam olarak budur.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from mayen.agent.prompt import ContextBlock
from mayen.data import clock


def test_local_is_wall_clock_and_now_is_utc() -> None:
    """İkisi aynı anı gösterir ama biçimleri ve dilimleri ayrıdır."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", clock.local())
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", clock.now())
    # Aynı an: yerel damga, UTC damganın yerel karşılığıyla dakika dakika örtüşmeli.
    expected = clock.parse(clock.now()).astimezone().strftime(clock.LOCAL_FORMAT)
    assert clock.local() == expected


def test_stored_stamps_stay_utc() -> None:
    """`parse` yalnızca UTC biçimini okur; yerel biçim depoya giremez."""
    assert clock.parse("2026-08-16T15:47:00Z").tzinfo is UTC
    try:
        clock.parse("2026-08-16 18:47")
    except ValueError:
        return
    raise AssertionError("yerel biçim damga olarak kabul edildi")


def test_from_local_reads_wall_clock_back_into_a_stored_stamp() -> None:
    """`local()`'in tersi. Sabit bir saat/dilim yazılmıyor: test makinenin dilimine göre
    farklı sonuç verirdi. Gidiş-dönüş dilimden bağımsız."""
    stored = clock.from_local(clock.local())
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stored)
    # Dakikaya yuvarlandığı için bir dakikadan fazla sapamaz.
    assert abs((clock.parse(stored) - clock.parse(clock.now())).total_seconds()) < 60


def test_the_context_block_carries_one_clock_and_it_is_local() -> None:
    """**Öneğin tek saat kaynağı var, ve o yerel (2026-08-17).**

    İkinci bir satır vardı — "aynı an UTC (tool argümanları için)" — ve `task_create`'in
    UTC isteyen `due` alanı içindi. İki alanı birlikte vermek dönüşümü güvenli kılmadı:
    model "yarın dokuzda" için `2026-08-18T09:00:00Z` yazdı, hatırlatıcı yerel 12:00'a
    kuruldu. Tool yerel saate geçtikten *sonra bile* satır durduğu sürece model onu
    izlemeye devam etti; hata ancak satır silinince bitti. Bu yüzden bu test damga
    biçiminin öneğe hiç girmediğini kilitliyor, "iki alan da var"ı değil.
    """
    rendered = ContextBlock(now="2026-08-16 18:47").render()
    assert "tarih/saat: 2026-08-16 18:47" in rendered
    # Damga biçimi öneğe hiç girmiyor: girdiği sürece model `due`'ya onu yazıyordu.
    assert "Z" not in rendered
    assert "UTC" not in rendered


def test_the_block_has_no_second_timestamp_field() -> None:
    """Alan tamamen kaldırıldı, yalnızca satırı gizlenmedi: `utc=` ile kurmak bir
    `TypeError`. Gizlemek, bir sonraki oturumun onu geri açmasına davet olurdu."""
    with pytest.raises(TypeError):
        ContextBlock(now="2026-08-16 18:47", utc="2026-08-16T15:47:00Z")  # type: ignore[call-arg]


async def test_date_time_puts_local_time_in_data_not_only_speech() -> None:
    """**Cümleyi model yazıyor ve elindeki tek şey `data`.**

    `ToolResult.speech` üretimde hiçbir yerden okunmuyor — modele geri beslenen şey
    `agent/loop.py:_feedback()`'in verdiği `data`'nın JSON'u. Bu 2026-08-16'da pahalıya
    öğrenildi: `speech` yerel saate çevrildi, sahip yine "15:58:22 UTC" duydu, çünkü
    `data`'da yalnızca UTC vardı. Test bu yüzden `speech`'e değil `data`'ya bakıyor.
    """
    from mayen.tools.date_time import TOOL

    result = await TOOL.handler(None, {})  # type: ignore[arg-type]
    assert result.ok
    data = result.data or {}
    assert set(data) == {"local", "utc"}
    assert data["local"] == clock.local()
    assert datetime.strptime(str(data["utc"]), clock.FORMAT)
    # Yerel alan dilim adı taşımaz: model onu okuyup "UTC" diye söylemesin.
    assert "UTC" not in str(data["local"])


async def test_task_create_puts_the_local_due_time_in_data(tmp_path: Path) -> None:
    """Hatırlatıcı onayı da `data`'dan konuşuluyor — `due_at` tek başına UTC söyletir."""
    from mayen.data.db import Database
    from mayen.data.migrate import migrate
    from mayen.data.repositories.tasks import TaskRepository
    from mayen.tools.task_create import TOOL

    with Database(tmp_path / "t.db") as db:
        migrate(db)
        context = SimpleNamespace(tasks=TaskRepository(db))
        result = await TOOL.handler(
            context,  # type: ignore[arg-type]
            {"due": "2026-08-16 18:58", "message": "çamaşırları as"},
        )
    assert result.ok
    data = result.data or {}
    assert data["due_at"] == clock.from_local("2026-08-16 18:58")
    assert data["due_local"] == "2026-08-16 18:58"
    assert data["message"] == "çamaşırları as"


async def test_task_create_takes_the_hour_the_user_said(tmp_path: Path) -> None:
    """**2026-08-17'nin gerçek turu:** "yarın sabah dokuzda hatırlat" → model `due`'ya
    `2026-08-18T09:00:00Z` yazdı, hatırlatıcı yerel 12:00'a kuruldu, model "dokuzda
    kurdum" dedi. Sapma tam saat dilimi kadardı (+03).

    Kilit şu: kullanıcının söylediği saat, geri okunan saate **eşit** olmak zorunda.
    Dilim yazılmadığı için test her makinede aynı şeyi doğruluyor.
    """
    from mayen.data.db import Database
    from mayen.data.migrate import migrate
    from mayen.data.repositories.tasks import TaskRepository
    from mayen.tools.task_create import TOOL

    with Database(tmp_path / "t.db") as db:
        migrate(db)
        context = SimpleNamespace(tasks=TaskRepository(db))
        result = await TOOL.handler(
            context,  # type: ignore[arg-type]
            {"due": "2026-08-18 09:00", "message": "ilaçlarını al"},
        )
    assert result.ok
    data = result.data or {}
    assert data["due_local"] == "2026-08-18 09:00"
    assert data["due_at"] == clock.from_local("2026-08-18 09:00")
    # Saklanan damga yine UTC: yerel biçim depoya girmiyor (`test_stored_stamps_stay_utc`).
    assert clock.parse(str(data["due_at"]))
