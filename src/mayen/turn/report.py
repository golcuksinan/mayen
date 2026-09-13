"""Turun oturumla konuştuğu dar arayüz — ve §4'ün dördüncü kez zorladığı tersine bağımlılık.

Koşan tur iki şeye ihtiyaç duyar: koştuğu turun tutamağı ve ilerlemesini bildirecek bir yer.
İkisi de `session`'da yaşıyor ve `session` `turn`'ün **üstünde** (§4) — sınır testi bu
import'u reddediyor. Çözüm import eklemek değil: `turn` neye ihtiyacı olduğunu `Protocol`
olarak yazar, `session` onu uygular. `TraceSink`, `SessionSink` ve `AudioSink` ile aynı
kalıp.

**Neden olay enum'u değil de yedi metot:** §5'in sözlüğünün sahibi `session/state.py` ve
`Event`'i buraya kopyalamak, iki enum arasında elle bakımı yapılan bir çeviri katmanı
demekti — dokümanla kodun sapmaya başladığı yer tam olarak orası. Bunun yerine tur **kendi
diliyle** ne olduğunu söylüyor; olaya çeviren, tablonun sahibi olan taraf.

**Alanlar salt okunur `property`:** `Protocol`'de yazılabilir alan değişmez (invariant)
sayılır, yani `segment: SegmentLike` yazmak `Segment` taşıyan bir tutamağı reddederdi.
"""

import asyncio
from typing import Any, Protocol


class SegmentLike(Protocol):
    """Turun segmentten gördüğü kadarı. `payload` opak: sesi çözen de metni okuyan da tur."""

    @property
    def segment_id(self) -> str: ...

    @property
    def device_id(self) -> str: ...

    @property
    def payload(self) -> object: ...


class TurnHandle(Protocol):
    """Koşan turun tutamağı (§5). `session.ActiveTurn` bunu karşılar."""

    @property
    def turn_id(self) -> str: ...

    @property
    def segment(self) -> SegmentLike: ...

    @property
    def speech_stopped(self) -> asyncio.Event:
        """ "Konuşmayı kes, ama turu öldürme" (B3). Onay cümlesi okunurken kullanılır."""
        ...

    @property
    def segments(self) -> asyncio.Queue[Any]:
        """Kapalı durumdayken gelen segmentler (§5). Onay çözümleyicisinin girdisi.

        `Any` bilerek: kuyruk `session`'ın ve içindeki tip de onun; burada `SegmentLike`
        yazmak, `Queue`'nun değişmez (invariant) tipi yüzünden gerçek kuyruğu reddederdi.
        """
        ...


class TurnReport(Protocol):
    """Turun ilerlemesi. Her metot §5 tablosunda tek bir olaya karşılık gelir."""

    async def understood(self) -> None:
        """Segment çözümlendi: ÇÖZÜMLÜYOR → DÜŞÜNÜYOR."""
        ...

    async def speaking(self) -> None:
        """İlk ses hazır: DÜŞÜNÜYOR → KONUŞUYOR."""
        ...

    async def spoke(self) -> None:
        """Ses bitti: KONUŞUYOR → IDLE."""
        ...

    async def answer_empty(self) -> None:
        """Ajan hiç metin üretmedi: DÜŞÜNÜYOR → IDLE. Sebep hata kanalından ayrıca gider."""
        ...

    async def approval_needed(self) -> None:
        """§8.5 adım 2 — cümle **okunmadan önce** (B3)."""
        ...

    async def approved(self) -> None: ...

    async def refused(self) -> None: ...

    async def approval_timed_out(self) -> None:
        """Kural 5: zaman aşımı reddir; plan düşer ve konuşulmaz."""
        ...

    async def registration_needed(self) -> None:
        """Ses profili kaydı (§10.5). Gövdesi henüz yok — akış Faz 4'ün; ama §5 tabloda
        tanımlı ve arayüzün onu söyleyememesi, tablonun yarısını temsil etmemek olurdu."""
        ...

    async def registration_done(self) -> None: ...
