# Faz B uygulandı: geçmişe doğru şeyi yazmak

Tarih: 2026-08-16. Model: `Qwen3.8-27B-IQ4_XS`, CLI. Ham rapor: `docs/faz-b-oturum.md`.

`issues.md` #7 — birkaç turdan sonra hiç tool çağrılmaması — **kapandı** (ölçüm + elle
koşu, aşağıdaki doğrulamanın 4. maddesi). **Düzelten şey bir prompt değişikliği değil,
geçmişe yazılan satırların kendisi.**

## Kabul kapısı

`uv run --env-file .env python -m evals.session --model Qwen3.8-27B-IQ4_XS`

| koşu | beklenen | gelen [%95] | ilk atlanan tur | gereksiz çağrı |
|---|---:|---:|---:|---:|
| **taban** (Faz A, 2026-08-16 sabahı) | 15 | **1 (7%)** [1%–30%] | **9** | 1 |
| özetleme açık | 15 | **13 (87%)** [62%–96%] | **23** | 4 |
| özetleme kapalı (**üretimin bugünkü hâli**) | 15 | **12 (80%)** [55%–93%] | **23** | 4 |

Wilson aralıkları **örtüşmüyor** (üst sınır 30%, alt sınır 55%): bu bir eğilim değil.
İki kol birbirinden ayrılmıyor (62–96 ve 55–93 örtüşüyor) — yani özetleme açık olmak bu
ölçümde bir şey kazandırmıyor, ki kapatılmasının gerekçelerinden biri buydu.

Ödenen bedel görünür ve kabul edilebilir: **gereksiz çağrı 1 → 4**, dördü de `date_time`
("saat kaç" turları). Bu sınıf **gecikme**; alternatifi "yaptım" deyip yapmamaktı.
CLAUDE.md'nin kaydettiği takas bu.

## Yapılan iki değişiklik

### 1. Tool sonucu geçmişte, kendi rolünde

`turn/runner.py` artık her tool adımını **iki satır** olarak yazıyor: çağrı `assistant`,
sonuç `tool`. Öncesinde yalnızca `[araç] bu turda çağrıldı: …` yazılıyor, sonuç
atılıyordu.

Eski kuralın gerekçesi "sonuç ertesi tur bayat"tı. Ölçüm bedelini gösterdi: sonuç
atılınca veri geçmişte **yalnızca asistanın cevabında** kalıyor, yani bir tool'dan
geldiği hiçbir yerde yazmıyor ve model onu kendi bilgisi sanıyor. **Bayatlık ortadan
kalkmıyordu, kaynağı gizleniyordu.** Sonuç `tool` rolünde durduğunda kaynak da tarih de
rollerden okunuyor — §11.3'ün "bayatsa tool çağır" kuralı ancak o zaman uygulanabilir.

Yan kazanç: ajanın **tur içinde** gördüğü dizi ile **ertesi tur** göreceği dizi artık
aynı biçimde. Eskiden ilki iki mesajdı, ikincisi tek satırlık bir izdi; model kendi
geçmişinde hiç üretmediği bir biçim görüyordu.

`called_line` üretimden çıktı, `evals/runner.py`'ye taşındı — tek turluk kümelerin
geçmişi o biçimde yazılmış ve elli senaryo bilerek sürülmüyor.

### 2. `Digest` ve `Recall` kapatıldı (`main.py:DIGEST_ON = False`)

Silinmedi, kapatıldı. Üç gerekçe:

- **Bugün faydası ölçülemiyor:** pencere 16384, 60 mesajlık önek ~2961 jeton (%19), ve
  `ContextWindow`'un kırpıcısı bugüne kadar **hiç çalışmadı**.
- **Bozukluğu ölçüldü:** özet birikimli ve anlatı kipinde, olguların yedide altısı yanlış.
- **Arızanın sebebi değildi:** `Digest` kapalıyken çöküş birebir aynı turda oluyordu.

Konuşmanın oturum sınırı yok; bütçe bir gün dolacak ve katman geri gerekecek. Geri açmak
sabiti `True` yapmak.

## Yapılmayanlar, ve neden

- **`yer-tutucu` uygulanmadı.** `docs/faz-b-bicim.md`'nin kazananıydı — eski asistan
  cevaplarının içeriğini geçmişten çıkarmak. **Gerek kalmadı:** asıl eksik olan şey
  cevabın *silinmesi* değil, sonucun *yazılması*ymış. Sahibin "geçmiş yok olmuyor mu"
  itirazı böylece bedelsiz karşılandı — geçmişten hiçbir şey çıkarılmadı, üstüne satır
  eklendi. Ablasyonlar `replay --bicim`'de duruyor; gerekirse dönülecek yer orası.
- **`CallFormat.YEREL` yapılmadı.** Sondaj (`docs/faz-b-sondaj-yerel.md`) yerel tool
  çağrısının çalıştığını ve gecikme bedeli olmadığını gösterdi, ama **tek başına
  yetmediğini** de gösterdi. Kapı zaten geçildiğine göre bu artık bir düzeltme değil, bir
  iyileştirme adayı — ve büyük bir arayüz değişikliği (`adapters/llm.py`'nin `stream`
  sözleşmesi yapılandırılmış çağrı taşımak zorunda kalır). **Ölçülecek yeni bir sorusu
  var:** sonuç artık `tool` rolünde saklandığına göre yerel biçim ne kadarını ekliyor?
  Karar sahibin.

## Sıradaki

1. Kalan iki atlama: 23 (`tamam kıs artık`) ve 28 (`hayır kullanmadın şimdi kullan`).
   İkisi de "kullanıcı ısrar ediyor, model zaten yaptığını söylüyor" sınıfı.
2. Özet ve olgular kapalıyken duruyor; B1–B4 (birikimli özet, yanlış olgular) hâlâ
   **düzeltilmedi**, yalnızca yoldan çekildi.
3. Düzeltme eski geçmişi onarmıyor; burada veritabanı silinerek kurtarıldı. Yıkıcı
   olmayan yol (pencere taban işareti) yazılmadı.

---

## Doğrulama (aynı gün, uygulamadan sonra)

**1. Tek turluk kümeler kıpırdamadı** (`docs/faz-b-dogrulama.md`): `kontrol` 94/94,
`halusinasyon` 93/93, `bellek` 88/88 — hepsi öncekiyle birebir. Altın küme CLI 98 → 96
(tek senaryo, aralıklar örtüşüyor), JSON 100 → 100.

**Ve bu bir kaza değil, yapısal:** tek turluk kümeler kendi özetini, olgusunu ve geçmişini
senaryodan kuruyor, veritabanından değil. `DIGEST_ON`'u da yeni geçmiş biçimini de
**göremezler**. Kabul kapısının oturum ölçümü olmasının sebebi tam olarak bu.

**2. Oturum ölçümü belirlenimci** (`docs/faz-b-tekrar.md`): üç koşu, üçü de birebir
12/15, ilk atlama 23, gereksiz çağrı 4.

**3. Elle koşu — ve asıl bulgu burada.**

Üç tur konuşuldu (`saat kaç`, `ses seviyesi kaç`, `kahveyi sade içtiğimi unutma`).
Sistem uçtan uca çalıştı: durum geçişleri, `Reply` çerçeveleri, ses, hepsi yerinde.
**Ama hiçbir turda tool çağrılmadı** ve "The volume is at forty percent" uydurmaydı.

Sebep veritabanında görünür: **145 mesajlık geçmişin tamamı düzeltme öncesi biçimde.**
60 mesajlık pencere baştan sona "kullanıcı sordu / asistan veriyle cevapladı, çağrı yok"
örnekleriyle dolu. Düzeltme **yeni** turların biçimini değiştiriyor; **eski geçmişi
onarmıyor.** Oturum ölçümü boş bir veritabanından başladığı için geçiyor.

**Ve arıza kendi kendini besliyor:** çağrısız geçen her yeni tur, geçmişe bir örnek daha
yazıyor. Kendiliğinden iyileşmesi beklenemez — 136–145 arası satırlar, düzeltmeden
*sonra* eklenmiş ve hepsi eski kalıbı sürdürüyor.

**4. Sahip `mayen.db`'yi sildi, elle koşu tekrarlandı — ve üretimde çalışıyor.**

Altı tur, **altı doğru tool çağrısı**, hiç atlama yok:

| tur | çağrı |
|---|---|
| saat kaç | `date_time` |
| ses seviyesi kaç | `volume` |
| bugün derslerim neler | `course_schedule --day 6` |
| **sesi kıssana biraz** | **`volume`** |
| kahveyi sade içtiğimi unutma | `fact_save` |
| neleri hatırlıyorsun | `fact_list` |

Dördüncü tur, Faz A'nın hiçbir ablasyonun temizce çeviremediği mesaj 118'in ta kendisi.
Son iki tur `fact_save` → `fact_list` gidiş-dönüşü: yazılan olgu ertesi turda geri
okunuyor.

Geçmiş de beklenen biçimde:

```
1 user       saat kaç
2 assistant  <tool> date_time
3 tool       {"utc": "2026-08-16T15:35:32Z"}
4 assistant  It is 15:35 UTC.
```

**`issues.md` #7 kapandı.** Ama kapanış koşulu kayda geçsin: **düzeltme eski geçmişi
onarmıyor.** Bozuk bir geçmiş taşıyan bir veritabanı düzeltmeden sonra da bozuk kalır ve
arıza kendini besleyerek sürer. Buradaki kurtarma **veritabanının silinmesiydi**
(sahibin kararı, 2026-08-16). Yıkıcı olmayan alternatif — pencerenin belirli bir mesaj
id'sinden sonra başlaması — yazılmadı; bir daha gerekirse yol o.
