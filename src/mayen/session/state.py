"""Sunucu durum makinesi (§5).

**Sunucunun durumları istemcinin durumları değildir.** Endpointing istemcide çalıştığı
için (§7) sunucuya yalnızca tamamlanmış segment gelir: burada `DINLIYOR` diye bir durum
yoktur, `IDLE`'dan doğrudan `COZUMLUYOR`'a geçilir. `DINLIYOR` istemcinin durumudur.

Tablo eksiksizdir ve tanımsız (durum, olay) çifti `InvalidTransitionError` yükseltir.
Sessizce aynı durumda kalmak Kural 13'ün ihlali olurdu: bir sıra hatası ancak
patladığında görülür.
Bu yüzden `ONAY_BEKLIYOR`'un kendine dönen geçişleri de tabloda **açıkça** yazılıdır —
"yazılmayan her şey kendine döner" kuralı, tabloyu okuyanın hangi olayın beklendiğini
göremediği bir tablo demektir.

Tanımlar Türkçe (`ARCHITECTURE.md` ile birebir), semboller aksansız: `İ`/`ı` üzerinde
`.upper()`/`.lower()` Türkçe için yanlış çalışır. Aksanlı biçim yalnızca değerde.
"""

from enum import StrEnum


class State(StrEnum):
    """§5'teki sunucu durumları."""

    IDLE = "IDLE"
    COZUMLUYOR = "ÇÖZÜMLÜYOR"
    DUSUNUYOR = "DÜŞÜNÜYOR"
    KONUSUYOR = "KONUŞUYOR"
    ONAY_BEKLIYOR = "ONAY_BEKLİYOR"
    KAYIT = "KAYIT"


class Event(StrEnum):
    """Durumu değiştirebilen olaylar. Adlar olayın *kaynağını* değil ne olduğunu söyler."""

    SEGMENT_ALINDI = "segment_alındı"
    COZUMLEME_BITTI = "çözümleme_bitti"
    ILK_SES_HAZIR = "ilk_ses_hazır"
    ONAY_GEREKLI = "onay_gerekli"
    KAYIT_GEREKLI = "kayıt_gerekli"
    SES_BITTI = "ses_bitti"
    SOZ_KESILDI = "söz_kesildi"
    ONAY_VERILDI = "onay_verildi"
    ONAY_REDDEDILDI = "onay_reddedildi"
    ONAY_ZAMAN_ASIMI = "onay_zaman_aşımı"
    KAYIT_BITTI = "kayıt_bitti"


class InvalidTransitionError(Exception):
    """Bu durumda bu olay tanımlı değil."""

    def __init__(self, state: State, event: Event) -> None:
        super().__init__(f"{state.name} durumunda {event.name} olayı tanımlı değil")
        self.state = state
        self.event = event


# §5'teki geçiş tablosunun kendisi. Tek yazıldığı yer burası.
TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.IDLE, Event.SEGMENT_ALINDI): State.COZUMLUYOR,
    (State.COZUMLUYOR, Event.COZUMLEME_BITTI): State.DUSUNUYOR,
    (State.DUSUNUYOR, Event.ILK_SES_HAZIR): State.KONUSUYOR,
    (State.DUSUNUYOR, Event.ONAY_GEREKLI): State.ONAY_BEKLIYOR,
    (State.DUSUNUYOR, Event.KAYIT_GEREKLI): State.KAYIT,
    (State.KONUSUYOR, Event.SES_BITTI): State.IDLE,
    # Söz kesme turu iptal eder; kapsamı **tur**, TTS kuyruğunun tamamı değil (§12).
    (State.KONUSUYOR, Event.SOZ_KESILDI): State.IDLE,
    # Onay cümlesi ONAY_BEKLIYOR'un *içinde* okunur (B3). Okurken söz kesilirse ses durur
    # ama durum değişmez ve bekleyen plan yaşar; gelen segment onay çözümleyicisine gider.
    (State.ONAY_BEKLIYOR, Event.SOZ_KESILDI): State.ONAY_BEKLIYOR,
    (State.ONAY_BEKLIYOR, Event.ONAY_VERILDI): State.DUSUNUYOR,
    # Red de DÜŞÜNÜYOR'a döner: §8.2'ye göre tool sonucu olarak modele geri beslenir.
    (State.ONAY_BEKLIYOR, Event.ONAY_REDDEDILDI): State.DUSUNUYOR,
    # Zaman aşımı = red (Kural 5), ama plan düşer ve konuşulmaz: karşıda kimse yok.
    (State.ONAY_BEKLIYOR, Event.ONAY_ZAMAN_ASIMI): State.IDLE,
    (State.KAYIT, Event.KAYIT_BITTI): State.DUSUNUYOR,
}

# Kapalı durumlar (§5): buradayken gelen metin ajan katmanına **hiç** ulaşmaz.
# ONAY_BEKLIYOR'da yalnızca onay çözümleyicisine, KAYIT'ta yalnızca kayıt akışına gider.
CLOSED_STATES: frozenset[State] = frozenset({State.ONAY_BEKLIYOR, State.KAYIT})


def transition(state: State, event: Event) -> State:
    """Tabloyu uygular. Tanımsız çift `InvalidTransitionError` yükseltir (Kural 13)."""
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise InvalidTransitionError(state, event) from None


def is_closed(state: State) -> bool:
    """Bu durumdayken gelen metin ajana ulaşmıyor mu?"""
    return state in CLOSED_STATES
