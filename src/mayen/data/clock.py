"""Zaman damgası biçimi. Tek yerde, çünkü iki farklı biçim yazan iki modül sıralamayı bozar."""

from datetime import UTC, datetime

FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def stamp(moment: datetime) -> str:
    """Bir anı damgaya çevirir. Biçimi yazan tek yer burası olsun diye ayrı bir işlev:
    `.strftime(FORMAT)`'ı çağıran ikinci bir modül, modül başlığının uyardığı şeyin ta
    kendisi."""
    return moment.astimezone(UTC).strftime(FORMAT)


def now() -> str:
    """Şu an, ISO-8601 UTC ('2026-08-09T14:03:11Z')."""
    return stamp(datetime.now(UTC))


LOCAL_FORMAT = "%Y-%m-%d %H:%M"
"""İnsana okunan biçim. `FORMAT`'tan ayrı ve ayrı kalmalı: biri saklanan damga, diğeri
sesli söylenen saat. Saniye yok — "on sekiz kırk yedi" söylenir, "on sekiz kırk yedi ve
otuz iki saniye" söylenmez."""


def local() -> str:
    """Şu an, **yerel** saatle ve insana okunacak biçimde ('2026-08-16 18:47').

    **Saklanan hiçbir şey bu biçimde değil** (bkz. `FORMAT`): depoda, `task_create`'in
    `due` alanında ve karşılaştırmalarda daima UTC var. Bu yalnızca konuşma kenarı.
    İkisi karışırsa sıralama bozulur ve kimse fark etmez — modül başlığının uyarısı bu.

    **Saat dilimi sistemden, yapılandırmadan değil.** Makine sahibinin kendi makinesi
    (tek makine, kendi verisi) ve orada zaten doğru dilim kurulu; ayrı bir ayar, sistem
    saatiyle ayrışabilecek ikinci bir gerçek olurdu. Bu, `context_size()`'ın sunucudan
    sorulmasıyla aynı gerekçe.
    """
    return datetime.now().astimezone().strftime(LOCAL_FORMAT)


def from_local(reading: str) -> str:
    """`LOCAL_FORMAT` ile yazılmış yerel bir saati saklanacak damgaya çevirir.

    Dönüşüm burada, çünkü iki biçimi de bilen tek modül bu.

    **Varlık sebebi ölçülmüş bir hata (2026-08-17, gerçek tur):** "yarın sabah dokuzda
    hatırlat" denince model `due`'ya `2026-08-18T09:00:00Z` yazdı — yerel saati UTC
    alanına koydu, yani hatırlatıcı 12:00'a kuruldu ve model "dokuzda kurdum" dedi.
    Öneğin hem `now` (yerel) hem `utc` alanını taşıması bunu **önlemedi**; saat dilimi
    kadar, burada üç saat sapma. Çare, aritmetiği modelden almak — `task_create`'in
    göreli biçiminin (`+5m`) ölçülmüş gerekçesiyle birebir aynı sınıf.

    Naif `datetime`'a `.astimezone()` uygulanıyor: yazılmayan dilim yerel sayılır, ki
    kullanıcının söylediği saatin anlamı bu. Dilim sistemden gelir (`local()`).
    """
    return stamp(datetime.strptime(reading, LOCAL_FORMAT).astimezone())


def parse(stamp: str) -> datetime:
    """Damgayı geri okur. Yazan taraf gibi okuyan taraf da tek yerde: zamanlayıcı
    "vakti ne kadar geçmiş" diye sorarken (§12 tolerans) ikinci bir biçim varsayamaz.
    `ValueError` yükseltir — tanınmayan damga sessizce şimdiye düşmez (Kural 13)."""
    return datetime.strptime(stamp, FORMAT).replace(tzinfo=UTC)
