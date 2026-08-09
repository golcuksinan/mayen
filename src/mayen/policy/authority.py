"""Kademe × etki sınıfı matrisi — sistemin tek zorlayıcı yetki noktası (§10.2, Kural 4).

Sistem promptu modele kademelerden bahseder, ama bu bir kolaylıktır: modelin o bilgiyi yok
sayması güvenlik olayı değildir, çünkü kararı model vermez. Karar `authorize()`'dır ve
başka hiçbir yerde yetki kontrolü yazılmaz.

**Neden `Tier` değil de ayrı bir `Authority`:** `data.people.Tier` saklanan sözlüktür ve
şemadaki CHECK kısıtı onun sahibidir; `TANINMAYAN` orada yoktur çünkü profili olmayan
kişinin satırı da yoktur (§10.1). Matris ise dört kademeyi de tanımak zorunda. Bu yüzden
dördüncüsü burada, kimliği yetkiye çeviren yerde duruyor; `data`'nın sözlüğü olduğu gibi
kalıyor.

**Matris eksiksizdir.** On altı hücrenin hepsi açıkça yazılı; eksik hücre `KeyError`
demektir, sessiz bir "izin yok" değil (Kural 13). Ama eksiksizliği testin ölçmesi için
sözlük hücre hücre yazıldı, `dict.fromkeys` gibi bir kısayolla üretilmedi: üretilen bir
matris, testi de üretenin varsayımını doğrular.
"""

from dataclasses import dataclass
from enum import StrEnum

from mayen.data.repositories.people import Tier
from mayen.policy.effects import Effect


class Authority(StrEnum):
    """§10.2'nin dört kademesi."""

    SAHIP = "SAHIP"
    KAYITLI_KISI = "KAYITLI_KISI"
    BEKLEYEN = "BEKLEYEN"
    TANINMAYAN = "TANINMAYAN"


class Decision(StrEnum):
    """`authorize()`'ın üç sonucu. `ONAY_GEREKLI` bir "evet" değil, bir ön koşuldur."""

    IZIN_VAR = "İZİN_VAR"
    ONAY_GEREKLI = "ONAY_GEREKLİ"
    RED = "RED"


@dataclass(frozen=True, slots=True)
class Identity:
    """Kimliğin yetkiye çevrilmiş hâli.

    `person_id` yalnızca kayıt/iz içindir; yetki kararı **yalnızca** `authority`'den çıkar.
    Kimlik alanı kullanıcının metninden hiç okunmaz (Kural 7, §10.1) — bu nesneyi kuran
    yer ses gömüsünü karşılaştıran taraftır, modelin çıktısı değil.
    """

    authority: Authority
    person_id: int | None = None


def authority_of(tier: Tier | None) -> Authority:
    """Tanınmayan kişinin rehberde satırı yoktur; `None` bu yüzden `TANINMAYAN`."""
    if tier is None:
        return Authority.TANINMAYAN
    return Authority(tier.value)


# §10.2'nin matrisi. Tek yazıldığı yer burası.
#
# SAHİP her şeyi yapar, ama geri alınamazlar onay ister — sahiplik onayı kaldırmaz, çünkü
# onay yetki sorusu değil niyet sorusudur (§8.5).
# KAYITLI_KİŞİ yalnızca OKUMA ve DIŞ: DIŞ okuma gibi davranır (hava durumu), sistemin
# durumunu değiştirmez.
# BEKLEYEN ve TANINMAYAN'da hiçbir yetki açılmaz (§10.3); sohbet ve kayıt akışı tool
# çağırmadığı için matrise girmez.
_MATRIX: dict[tuple[Authority, Effect], Decision] = {
    (Authority.SAHIP, Effect.OKUMA): Decision.IZIN_VAR,
    (Authority.SAHIP, Effect.YAZMA): Decision.IZIN_VAR,
    (Authority.SAHIP, Effect.DIS): Decision.IZIN_VAR,
    (Authority.SAHIP, Effect.GERI_ALINAMAZ): Decision.ONAY_GEREKLI,
    (Authority.KAYITLI_KISI, Effect.OKUMA): Decision.IZIN_VAR,
    (Authority.KAYITLI_KISI, Effect.YAZMA): Decision.RED,
    (Authority.KAYITLI_KISI, Effect.DIS): Decision.IZIN_VAR,
    (Authority.KAYITLI_KISI, Effect.GERI_ALINAMAZ): Decision.RED,
    (Authority.BEKLEYEN, Effect.OKUMA): Decision.RED,
    (Authority.BEKLEYEN, Effect.YAZMA): Decision.RED,
    (Authority.BEKLEYEN, Effect.DIS): Decision.RED,
    (Authority.BEKLEYEN, Effect.GERI_ALINAMAZ): Decision.RED,
    (Authority.TANINMAYAN, Effect.OKUMA): Decision.RED,
    (Authority.TANINMAYAN, Effect.YAZMA): Decision.RED,
    (Authority.TANINMAYAN, Effect.DIS): Decision.RED,
    (Authority.TANINMAYAN, Effect.GERI_ALINAMAZ): Decision.RED,
}


def authorize(identity: Identity, effect: Effect) -> Decision:
    """Yetki kararı. Sistemdeki tek yetki kapısı (Kural 4).

    Tool'un adına bakmaz: karar yalnızca etki sınıfından çıkar (§9.1). Bir tool'un adına
    göre istisna yazmak, ikinci bir "hassas tool listesi" kurmak olurdu.
    """
    return _MATRIX[(identity.authority, effect)]
