# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen3.6-27B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.6000000238418579, `top_k`=20, `top_p`=0.949999988079071, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=0.0, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Toplam

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool | uydurulan argüman | desteksiz sayı (n) | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-27B-IQ4_XS × cli | 50 | 94% [84%–98%] | 97% | — | 0 | 0 | 2 (5) | 0 | 22 | 0.17 | 0.63 |
| Qwen3.6-27B-IQ4_XS × cli × kontrol | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 65 | 0.12 | 1.48 |
| Qwen3.6-27B-IQ4_XS × cli × adim2 | 8 | 100% [68%–100%] | 100% | 88% [53%–98%] (8) | 0 | 0 | 0 (0) | 0 | 10 | 0.54 | 0.77 |
| Qwen3.6-27B-IQ4_XS × cli × saglamlik | 10 | 90% [60%–98%] | 89% | — | 0 | 0 | 0 (0) | 0 | 15 | 0.17 | 0.49 |
| Qwen3.6-27B-IQ4_XS × cli × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 7 | 0.60 | 0.75 |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (3) | 0 | 16 | 0.51 | 0.85 |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (3) | 0 | 15 | 0.50 | 0.83 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu | 50 | 98% [90%–100%] | 94% | — | 0 | 0 | 0 (5) | 0 | 9 | 0.19 | 0.39 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 5 | 0.12 | 0.24 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × adim2 | 8 | 100% [68%–100%] | 100% | 100% [68%–100%] (8) | 0 | 0 | 0 (0) | 0 | 10 | 0.56 | 0.78 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × saglamlik | 10 | 100% [72%–100%] | 89% | — | 0 | 0 | 0 (0) | 0 | 15 | 0.17 | 0.49 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 7 | 0.61 | 0.76 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izli) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 15 | 0.51 | 0.84 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 15 | 0.50 | 0.83 |
| Qwen3.6-27B-IQ4_XS × json | 50 | 86% [74%–93%] | 91% | — | 0 | 0 | 3 (5) | 1 | 28 | 0.19 | 0.81 |
| Qwen3.6-27B-IQ4_XS × json × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 67 | 0.13 | 1.53 |
| Qwen3.6-27B-IQ4_XS × json × adim2 | 8 | 100% [68%–100%] | 100% | 88% [53%–98%] (8) | 0 | 0 | 0 (0) | 0 | 22 | 0.54 | 1.00 |
| Qwen3.6-27B-IQ4_XS × json × saglamlik | 10 | 90% [60%–98%] | 78% | — | 0 | 0 | 0 (0) | 0 | 26 | 0.17 | 0.73 |
| Qwen3.6-27B-IQ4_XS × json × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 17 | 0.57 | 0.94 |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (3) | 0 | 25 | 0.49 | 1.03 |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (3) | 0 | 25 | 0.49 | 1.02 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu | 50 | 94% [84%–98%] | 89% | — | 0 | 0 | 2 (5) | 0 | 18 | 0.18 | 0.56 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × kontrol | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 5 | 0.12 | 0.24 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × adim2 | 8 | 100% [68%–100%] | 100% | 100% [68%–100%] (8) | 0 | 0 | 0 (0) | 0 | 22 | 0.54 | 1.00 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × saglamlik | 10 | 80% [49%–94%] | 75% | — | 0 | 0 | 0 (0) | 0 | 25 | 0.17 | 0.70 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 17 | 0.55 | 0.92 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izli) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 29 | 0.51 | 1.13 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 29 | 0.50 | 1.12 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-27B-IQ4_XS × cli | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × kontrol | — | — | — | 100% | — | — |
| Qwen3.6-27B-IQ4_XS × cli × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-27B-IQ4_XS × cli × saglamlik | 100% | — | 0% | — | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu | 100% | 100% | 86% | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × saglamlik | 100% | — | 100% | — | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json | 100% | 83% | 14% | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-27B-IQ4_XS × json × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-27B-IQ4_XS × json × saglamlik | 100% | — | 0% | — | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × zorunlu | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × kontrol | — | — | — | 100% | — | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × saglamlik | 100% | — | 0% | — | 0% | 100% |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-27B-IQ4_XS × cli | 94% (50) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × kontrol | 100% (18) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × adim2 | 100% (8) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × saglamlik | 90% (10) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × uzun | 100% (4) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu | 98% (50) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × kontrol | 94% (18) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × adim2 | 100% (8) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × saglamlik | 100% (10) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × uzun | 100% (4) | — | — |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | — | 80% (5) | 80% (5) |
| Qwen3.6-27B-IQ4_XS × json | 86% (50) | — | — |
| Qwen3.6-27B-IQ4_XS × json × kontrol | 94% (18) | — | — |
| Qwen3.6-27B-IQ4_XS × json × adim2 | 100% (8) | — | — |
| Qwen3.6-27B-IQ4_XS × json × saglamlik | 90% (10) | — | — |
| Qwen3.6-27B-IQ4_XS × json × uzun | 100% (4) | — | — |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × json × zorunlu | 94% (50) | — | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × kontrol | 100% (18) | — | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × adim2 | 100% (8) | — | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × saglamlik | 80% (10) | — | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × uzun | 100% (4) | — | — |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | — | 80% (5) | 80% (5) |

## Zorunlu mod: `no_tool` kullanımı

Zorunlu modda çağrı gerekmeyen tur `<tool> no_tool` yazarak kapanır, yani **iki sütun eşit olmalı**: gramer başka bir çıkış yolu bırakmıyor. Eşit değilse aradaki fark, düzeltme tavanına kadar geçerli bir çağrı üretilemeyen turlardır — tek bir doğruluk yüzdesinde bu iki başarısızlık aynı görünür.

| koşu | mod | `no_tool` | çağrı üretilmeyen tur |
|---|---|---:|---:|
| Qwen3.6-27B-IQ4_XS × cli | serbest | 0 | 12 |
| Qwen3.6-27B-IQ4_XS × cli × kontrol | serbest | 0 | 18 |
| Qwen3.6-27B-IQ4_XS × cli × adim2 | serbest | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × cli × saglamlik | serbest | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × cli × uzun | serbest | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | serbest | 0 | 2 |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | serbest | 0 | 2 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu | zorunlu | 14 | 14 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × kontrol | zorunlu | 17 | 17 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × adim2 | zorunlu | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × saglamlik | zorunlu | 1 | 1 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × uzun | zorunlu | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izli) | zorunlu | 1 | 1 |
| Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | zorunlu | 1 | 1 |
| Qwen3.6-27B-IQ4_XS × json | serbest | 0 | 9 |
| Qwen3.6-27B-IQ4_XS × json × kontrol | serbest | 0 | 17 |
| Qwen3.6-27B-IQ4_XS × json × adim2 | serbest | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × json × saglamlik | serbest | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × json × uzun | serbest | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | serbest | 0 | 2 |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | serbest | 0 | 2 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu | zorunlu | 12 | 12 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × kontrol | zorunlu | 18 | 18 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × adim2 | zorunlu | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × saglamlik | zorunlu | 1 | 1 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × uzun | zorunlu | 0 | 0 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izli) | zorunlu | 1 | 1 |
| Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | zorunlu | 1 | 1 |

## İkinci adım

Tool sonucu geri beslendikten sonraki adım (P25.2). Zincirin ikinci halkası bugüne kadar hiç ölçülmemişti; `Step2.expected` `None` olan satırlarda doğru davranış **çağrı yazmamaktır** — o satırlar olmadan bu sayaç, fazla çağrıyı iyileşme diye raporlardı.

**Qwen3.6-27B-IQ4_XS × cli × adim2** — ikinci adımda düşenler:

- `adm-05`: 2. adımda `çağrı yok`

**Qwen3.6-27B-IQ4_XS × json × adim2** — ikinci adımda düşenler:

- `adm-05`: 2. adımda `çağrı yok`


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-27B-IQ4_XS × cli** — desteksiz sayı geçen senaryolar:

- `tek-05`: `29.4` — yanıt: `Bilgisayarın bellek durumu şu şekildedir:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB

Yaklaşık %29.4'ü kullanılıyor, yani bellek kullanımı oldukça düşük ve sağlıklı seviyede.`
- `tek-10`: `1` — yanıt: `Şu an 1 bekleyen hatırlatıcınız var:

*   **İlaç** - 10 Ağustos 2026, 06:00 (UTC)`

**Qwen3.6-27B-IQ4_XS × json** — desteksiz sayı geçen senaryolar:

- `tek-05`: `29`, `22.6` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Kullanılabilir Bellek:** 22.6 GB

Bellek kullanımı toplam kapasitenin yaklaşık %29'unu oluşturuyor, yani sistemde yeterli boş bellek bulunuyor.`
- `tek-10`: `1` — yanıt: `Şu an 1 bekleyen hatırlatıcınız var:

*   **İlaç** - 10 Ağustos 2026, 06:00 (UTC)`

**Qwen3.6-27B-IQ4_XS × json × zorunlu** — desteksiz sayı geçen senaryolar:

- `tek-05`: `29.4`, `22.6` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB

Bellek kullanımı oldukça düşük (%29.4), sistem rahat çalışıyor.`

## Başarısız senaryolar

### Qwen3.6-27B-IQ4_XS × cli — 4/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city Ankara`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target default`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`

### Qwen3.6-27B-IQ4_XS × cli × kontrol — 0/18

Yok.

### Qwen3.6-27B-IQ4_XS × cli × adim2 — 1/8

- `adm-05` (çok tool): 2. adım: contact_save beklenirken çağrı üretilmedi — çıktı: `<tool> contact_get --name Ayşe`

### Qwen3.6-27B-IQ4_XS × cli × saglamlik — 2/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'bugün çok yoğun geçti.' geldi — çıktı: `<tool> note_create --body bugün çok yoğun geçti.`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city Ankara`

### Qwen3.6-27B-IQ4_XS × cli × uzun — 0/4

Yok.

### Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message Bir şey yapman gerekiyor!`

### Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message Bir şey yapman gerekiyor!`

### Qwen3.6-27B-IQ4_XS × cli × zorunlu — 3/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`

### Qwen3.6-27B-IQ4_XS × cli × zorunlu × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-27B-IQ4_XS × cli × zorunlu × adim2 — 0/8

Yok.

### Qwen3.6-27B-IQ4_XS × cli × zorunlu × saglamlik — 1/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'bugün çok yoğun geçti.' geldi — çıktı: `<tool> note_create --body bugün çok yoğun geçti.`

### Qwen3.6-27B-IQ4_XS × cli × zorunlu × uzun — 0/4

Yok.

### Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message Bir şey yapman gerekiyor!`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-27B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message Bir şey yapman gerekiyor!`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-27B-IQ4_XS × json — 10/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-06` (çok tool): contact_save beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Veli"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:05:00Z", "message": "Hatırlatıcı"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `eks-07` (eksik argüman): contact_save: 'phone' boş olamaz; düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`

### Qwen3.6-27B-IQ4_XS × json × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul", "fields": ["condition"]}}`

### Qwen3.6-27B-IQ4_XS × json × adim2 — 1/8

- `adm-05` (çok tool): 2. adım: contact_save beklenirken çağrı üretilmedi — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`

### Qwen3.6-27B-IQ4_XS × json × saglamlik — 3/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'Bugün çok yoğun geçti.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Bugün çok yoğun geçti."}}`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "humidity"]}}`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.6-27B-IQ4_XS × json × uzun — 0/4

Yok.

### Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "Bir şey yapman gerekiyor!"}}`

### Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "Bir şey yapman gerekiyor!"}}`

### Qwen3.6-27B-IQ4_XS × json × zorunlu — 7/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:00Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.6-27B-IQ4_XS × json × zorunlu × kontrol — 0/18

Yok.

### Qwen3.6-27B-IQ4_XS × json × zorunlu × adim2 — 0/8

Yok.

### Qwen3.6-27B-IQ4_XS × json × zorunlu × saglamlik — 4/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'bugün çok yoğun geçti.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "bugün çok yoğun geçti."}}`
- `sag-06` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<tool> no_tool`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "humidity"]}}`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.6-27B-IQ4_XS × json × zorunlu × uzun — 0/4

Yok.

### Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "Bir şey yapman gerekiyor!"}}`
- `gec-10` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:10:00Z", "message": "Çayı hatırlat"}}`

### Qwen3.6-27B-IQ4_XS × json × zorunlu × geçmiş(izsiz) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "Bir şey yapman gerekiyor!"}}`
- `gec-10` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:10:00Z", "message": "Çayı hatırlat"}}`
