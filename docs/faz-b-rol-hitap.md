# Rol metni: "Administrator" her cümlenin sonundan kalktı

Tarih: 2026-08-16. Model: `Qwen3.8-27B-IQ4_XS`. Ham raporlar: `docs/faz-b-rol-hitap-ham.md`
(dil kuralsız, dört küme) ve `docs/faz-b-rol-hitap2.md` (dil kurallı, altın + kontrol).

## Neden

Sahibin elle koşusunda asistan hitabı **her cevabın sonuna** iliştiriyordu: "I am here,
Administrator." / "I am operational, Administrator." / "It is 19:03, Administrator."
Kaynak rol metninin tek bir satırıydı:

```
You call them "Administrator" and you use that word in your answers.
```

"use that word in your answers" cümlesi kelimeyi zorunlu kılıyor. Yeni hâli hitabı
koruyor ama zorunluluğu kaldırıyor: *"…when you address them. It is how you would begin a
sentence or answer a direct question, not a word you attach to every reply. Most answers
need it nowhere."* Metnin geri kalanı **baytı baytına aynı**.

## Sonuç

Hitap sıklığı (dil kuralı açık, yani üretimin koşulu):

| küme / biçim | eski | yeni |
|---|---:|---:|
| kontrol, CLI | 7/17 | **1/16** |
| altın, CLI | 6/15 | **0/14** |
| kontrol, JSON | 8/17 | **1/16** |
| altın, JSON | 6/13 | **0/…** |

Tool doğruluğu dört kümede de kıpırdamadı — hepsi ±1 senaryo, Wilson aralıkları örtüşüyor:

| küme | CLI eski → yeni | JSON eski → yeni |
|---|---|---|
| altın (50) | 98% → 96% | 98% → 98% |
| kontrol (18) | 94% → 94% | 94% → 94% |
| halüsinasyon (15) | 93% → 93% | 100% → 93% |
| bellek (17) | 88% → 82% | 76% → 82% |

Yön yok: bellek CLI'da düşüyor, JSON'da yükseliyor; halüsinasyon JSON'da bir senaryo
kaybediyor, CLI'da duruyor. Kural 14 gereği bunlar bir sıralama değil.

## Ne ölçülmedi

- **İngilizce oranı kaba bir sezgiyle sayıldı** (cevapta Türkçe'ye özgü harf var mı).
  Türkçe özel ad taşıyan bir İngilizce cümle ile diakritiksiz bir Türkçe cümleyi
  ayıramaz. Ölçülen: eski 17/17, 15/15, 16/17; yeni 15/16, 14/14, 14/16. **Dil tutuyor**
  denebilir, "hiç bozulmadı" denemez.
- **Tek koşu**, ve `bellek`'in 17 senaryosunda tek bir senaryo %6 oynatıyor.
- İlk raporda (`faz-b-rol-hitap-ham.md`) dil kuralı **verilmedi** ve cevaplar Türkçe çıktı;
  tool karşılaştırması orada da adil (iki kolda da yok) ama dil ekseni okunmaz. Üretimin
  koşulu ikinci rapor.
