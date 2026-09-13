# Faz B/1: geçmişteki cevabın biçimi — beş aday ölçüldü

Tarih: 2026-08-16. Model: `Qwen3.8-27B-IQ4_XS`, biçim CLI, `presence_penalty` 1.5.
Ham raporlar: `docs/faz-b-bicim-91.md`, `docs/faz-b-bicim-118.md`.
Araç: `evals/replay.py --bicim` (bu koşu için eklendi).

Faz A (`docs/faz-a-bulgular.md` §6) Faz B'nin ilk maddesini "geçmişteki cevabın tool
verisini taşıması" yapmış ve **ne yapılacağını bilerek kararlaştırmamıştı**. Sahip
2026-08-16'da *tool verisini cevaptan ayır* adayını seçti; ilk koşudan sonra da haklı bir
itiraz getirdi — **böyle yaparsak geçmiş modelin gözünde yok olmuyor mu.** İkinci koşu
(`kısa-cevap`, `yer-tutucu`) o itirazın ölçüsü. **Karar değil, ölçüm** — kabul kapısı
hâlâ A2'nin oturum tablosu (taban 1/15, ilk atlama 9. tur).

## Ablasyonlar

Merdiven geçmişi **kısaltıyor**; bunlar kısaltmadan **yeniden yazıyor**. Kısaltmadan
sonra uygulanıyorlar, yani modele gerçekten giden satırlara. Beşi tek bir eksende
duruyor — eski cevaptan **ne kadarı kalıyor**:

| ablasyon | eski asistan satırları | en son asistan satırı |
|---|---|---|
| `cevapsız` | çıkarıldı | çıkarıldı |
| `son-cevap` | çıkarıldı | tam |
| `yer-tutucu` | `(cevaplandı)` | tam |
| `kısa-cevap` | ilk cümle | tam |
| `söylenen` | tam, `[söylenen]` etiketli | tam, etiketli |

**Etiket `[araç]` izine değil, bütün asistan satırlarına vuruyor**, ve sebebi ölçümde:
çöküş başladıktan sonra veriyi taşıyan cevapların `[araç]` satırı **yok** — 118'de model
hiç çağırmadan "yüzde kırk" diyor. Yalnızca tool çağıran turun cevabını işaretlemek,
arızanın kendi ürettiği satırları atlardı.

## Sonuç

Mesaj 91 (`bugün derslerim neler`) — Faz A'nın temiz çeviren turu:

| ablasyon | önek jetonu | çağrı |
|---|---:|---|
| tam | 2943 | — |
| `cevapsız` | 2429 | `course_schedule` |
| `kısa-cevap` | 2667 | — |
| **`yer-tutucu`** | 2586 | **`course_schedule` `day='7'`** |
| `son-cevap` | 2442 | `course_schedule` |
| `söylenen` | 3093 | — |
| geçmişsiz | 2181 | `course_schedule` |

Mesaj 118 (`sesi kıssana biraz`) — Faz A'nın hiçbir ablasyonun temizce çeviremediği turu:

| ablasyon | önek jetonu | çağrı | çıktı |
|---|---:|---|---|
| tam | 2961 | — | I will lower the volume, Administrator. |
| `cevapsız` | 2475 | — | I need the current level…  `<tool> volume` |
| `kısa-cevap` | 2743 | — | I will lower the volume, Administrator. |
| **`yer-tutucu`** | 2644 | **`volume`** | `<tool> volume` |
| `son-cevap` | 2488 | `volume` | `<tool> volume` |
| `söylenen` | 3123 | — | `[söylenen]` The volume is set to forty percent… |
| geçmişsiz | 2231 | — | I will lower the volume to 40 percent.  `<tool> volume --level 40` |

## Okuma

1. **Kısaltmak işe yaramıyor, ve sebebi tam olarak öngörülen sebep: veri ilk cümlede.**
   91'de kısaltılmış satır `Today is Sunday.` — cümle kısaldı, veri yerinde kaldı, model
   yine çağırmadı. 118'de çıktı `tam`'ın **birebir aynısı**. Yani "geçmişi koruyalım,
   sadece kırpalım" ölçüldü ve **düştü**. Bu, itirazın ölçüye çevrilmesinin karşılığı:
   umut edilen orta yol yok — işe yarayan tek şey içeriğin **tamamen** gitmesi.
2. **`yer-tutucu` iki turda da kazanıyor ve `son-cevap`'ı kapsıyor.** İkisi de eski
   cevapların içeriğini götürüyor, ama `yer-tutucu` turun **biçimini** bırakıyor:
   "soruldu, cevaplandı, sonra bu soru geldi". `son-cevap`'ın verdiği her şeyi veriyor
   (en son cevap ikisinde de tam), üstüne konuşmanın iskeletini de veriyor. Bedeli
   `son-cevap`'a göre +144/+156 jeton; `tam`'a göre hâlâ ~320 jeton **ucuz**.
3. **`söylenen` başarısız ve zararlı:** model `[söylenen]` etiketini **kendi çıktısına
   kopyaladı**, iki turda da. Faz 7'nin dersi — *yalnızca sesli söyleyeceğini yaz*;
   önekteki bir etiket konuşmaya sızıyor. Üstelik en pahalı satır. Bu aday **düşüyor**.
   Not: `(cevaplandı)` sızmadı — yani sızan şey etiket olması değil, **cevabın önüne
   konmuş** olması gibi görünüyor. Tek koşu, bu bir gözlem.
4. **`geçmişsiz` 118'i hâlâ çeviremiyor, `yer-tutucu` çeviriyor.** Yani geçmişi atmak
   düzeltme değil; düzeltme, geçmişi **doğru biçimde** vermek.
5. **`[araç]` izi dördüncü kez etkisiz:** `yer-tutucu` ve `son-cevap` penceresinde iz
   duruyor ve tek başına yetmiyordu; çeviren şey cevabın gitmesi.

## Ne ölçülmedi — bunlar okunurken bilinsin

- **İki tur, tek koşu.** Kural 14: bu bir eğilim, bir oran değil. 91'in `day='7'`
  argümanı da tek koşuluk bir gözlem (Faz A'nın `geçmiş-2` satırı aynısını vermişti).
- **Kabul kapısı koşulmadı.** `yer-tutucu`'yu üretime yazmadan `evals/session.py`
  koşturulamıyor — pencereyi üretimin kodu kuruyor. Sıradaki iş bu ve **ölçüm bitmeden
  madde kapanmıyor**.
- **Bedel duruyor ve ölçülmedi:** eski cevapların içeriği modelin gözünde yok. "Biraz
  önce saydığın dersleri tekrar söyle" diyen bir tur karşılıksız kalır. Hiçbir kümede bu
  sınıf senaryo yok; `bellek` kümesi olguları ölçüyor, bunu değil. Mimaride o içeriğin
  gideceği yer `[özet]` — **ve o özet bugün bozuk** (B1–B4, `docs/faz-a-bulgular.md`
  §2.1). Yani bugün üretime alınırsa, eski cevaplar çalışmadığı ölçülmüş bir bileşene
  emanet edilmiş olur. Bu, ölçümün çözdüğü bir sorun değil; sıralama sorusu.
- Dördüncü aday (**tazelik işareti**) koşulmadı. `söylenen`in sızıntısı ona da bir uyarı:
  aynı sınıf mekanizma, ve `[araç]` izi zaten dört kez etkisiz ölçüldü.
