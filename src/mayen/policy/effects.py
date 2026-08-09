"""Etki sınıfları (§9.1).

Burada, `tools`'ta değil: her tool etki sınıfını **bildirir**, kararı vermez. Kararı veren
tek yer politika katmanı (Kural 4), o yüzden sözlüğün sahibi de burası — `tools` (rütbe 5)
`policy`'yi (rütbe 6) import edebilir, tersi §4'ü kırar.

`data`'daki `Tier`'ın aksine bu enum saklanan bir değer değil: veritabanında etki sınıfı
tutan bir sütun yok, tool tanımı koddadır. Bu yüzden `data`'ya değil buraya ait.

Ayrıca "hassas tool listesi" diye ikinci bir yer yok (§9.1): onay ve yetki kararları
yalnızca bu alandan türer.
"""

from enum import StrEnum


class Effect(StrEnum):
    """§9.1. Semboller aksansız, değerler dokümandaki gibi."""

    OKUMA = "OKUMA"
    YAZMA = "YAZMA"
    DIS = "DIŞ"
    GERI_ALINAMAZ = "GERİ_ALINAMAZ"
