# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.699999988079071, `top_k`=20, `top_p`=0.800000011920929, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=1.5, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Toplam

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool | uydurulan argüman | desteksiz sayı (n) | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 2 (5) | 0 | 21 | 0.28 | 0.46 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 52 | 0.18 | 0.61 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | 8 | 100% [68%–100%] | 100% | 100% [68%–100%] (8) | 0 | 0 | 0 (0) | 0 | 11 | 0.74 | 0.84 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | 10 | 80% [49%–94%] | 62% | — | 0 | 0 | 0 (0) | 0 | 14 | 0.25 | 0.37 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 7 | 0.73 | 0.80 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | 10 | 80% [49%–94%] | 71% | — | 0 | 0 | 0 (3) | 0 | 17 | 0.78 | 0.93 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | 10 | 80% [49%–94%] | 71% | — | 0 | 0 | 0 (3) | 0 | 18 | 0.74 | 0.88 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu | 50 | 88% [76%–94%] | 89% | — | 0 | 0 | 2 (5) | 0 | 10 | 0.27 | 0.36 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | 18 | 72% [49%–88%] | — | — | 0 | 0 | 0 (0) | 0 | 7 | 0.18 | 0.25 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × adim2 | 8 | 100% [68%–100%] | 100% | 100% [68%–100%] (8) | 0 | 0 | 0 (0) | 0 | 11 | 0.75 | 0.84 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × saglamlik | 10 | 80% [49%–94%] | 57% | — | 0 | 0 | 0 (0) | 0 | 14 | 0.25 | 0.37 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 7 | 0.75 | 0.81 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izli) | 9 | 78% [45%–94%] | 100% | — | 0 | 0 | 0 (2) | 0 | 17 | 0.74 | 0.88 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | 9 | 78% [45%–94%] | 83% | — | 0 | 0 | 0 (2) | 0 | 17 | 0.71 | 0.85 |
| Qwen3.6-35B-A3B-IQ4_XS × json | 50 | 94% [84%–98%] | 94% | — | 0 | 0 | 2 (5) | 1 | 29 | 0.26 | 0.50 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 73 | 0.18 | 0.77 |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | 8 | 100% [68%–100%] | 100% | 88% [53%–98%] (8) | 0 | 0 | 0 (0) | 0 | 21 | 0.74 | 0.93 |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | 10 | 80% [49%–94%] | 75% | — | 0 | 0 | 0 (0) | 0 | 25 | 0.26 | 0.47 |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 17 | 0.71 | 0.86 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 26 | 0.75 | 0.97 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 26 | 0.72 | 0.93 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu | 50 | 84% [71%–92%] | 94% | — | 0 | 0 | 2 (5) | 0 | 20 | 0.27 | 0.44 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | 18 | 50% [29%–71%] | — | — | 0 | 0 | 0 (0) | 0 | 10 | 0.18 | 0.28 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × adim2 | 8 | 100% [68%–100%] | 100% | 88% [53%–98%] (8) | 0 | 0 | 0 (0) | 0 | 22 | 0.74 | 0.93 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × saglamlik | 10 | 70% [40%–89%] | 71% | — | 0 | 0 | 0 (0) | 0 | 25 | 0.26 | 0.47 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 17 | 0.53 | 0.68 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izli) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 26 | 0.69 | 0.90 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 26 | 0.77 | 0.99 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | 100% | — | 0% | — | 100% | 75% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu | 100% | 100% | 14% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | — | — | — | 72% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × saglamlik | 100% | — | 100% | — | 0% | 75% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izli) | 80% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | 80% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | 100% | — | 0% | — | 100% | 75% |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu | 100% | 100% | 0% | 88% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | — | — | — | 50% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × saglamlik | 100% | — | 0% | — | 0% | 75% |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | 100% (8) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | 80% (10) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | 100% (4) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu | 88% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | 72% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × adim2 | 100% (8) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × saglamlik | 80% (10) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × uzun | 100% (4) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izli) | — | 80% (5) | 75% (4) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | — | 80% (5) | 75% (4) |
| Qwen3.6-35B-A3B-IQ4_XS × json | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | 100% (8) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | 80% (10) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | 100% (4) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu | 84% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | 50% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × adim2 | 100% (8) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × saglamlik | 70% (10) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × uzun | 100% (4) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | — | 80% (5) | 80% (5) |

## Zorunlu mod: `no_tool` kullanımı

Zorunlu modda çağrı gerekmeyen tur `<tool> no_tool` yazarak kapanır, yani **iki sütun eşit olmalı**: gramer başka bir çıkış yolu bırakmıyor. Eşit değilse aradaki fark, düzeltme tavanına kadar geçerli bir çağrı üretilemeyen turlardır — tek bir doğruluk yüzdesinde bu iki başarısızlık aynı görünür.

| koşu | mod | `no_tool` | çağrı üretilmeyen tur |
|---|---|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli | serbest | 0 | 12 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | serbest | 0 | 17 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | serbest | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | serbest | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | serbest | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | serbest | 0 | 1 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | serbest | 0 | 1 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu | zorunlu | 9 | 9 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | zorunlu | 13 | 13 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × adim2 | zorunlu | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × saglamlik | zorunlu | 1 | 1 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × uzun | zorunlu | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izli) | zorunlu | 1 | 2 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) | zorunlu | 1 | 2 |
| Qwen3.6-35B-A3B-IQ4_XS × json | serbest | 0 | 12 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | serbest | 0 | 17 |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | serbest | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | serbest | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | serbest | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | serbest | 0 | 1 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | serbest | 0 | 1 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu | zorunlu | 7 | 7 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | zorunlu | 9 | 9 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × adim2 | zorunlu | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × saglamlik | zorunlu | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × uzun | zorunlu | 0 | 0 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izli) | zorunlu | 1 | 1 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izsiz) | zorunlu | 1 | 1 |

## İkinci adım

Tool sonucu geri beslendikten sonraki adım (P25.2). Zincirin ikinci halkası bugüne kadar hiç ölçülmemişti; `Step2.expected` `None` olan satırlarda doğru davranış **çağrı yazmamaktır** — o satırlar olmadan bu sayaç, fazla çağrıyı iyileşme diye raporlardı.

**Qwen3.6-35B-A3B-IQ4_XS × json × adim2** — ikinci adımda düşenler:

- `adm-05`: 2. adımda `çağrı yok`

**Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × adim2** — ikinci adımda düşenler:

- `adm-08`: 2. adımda `note_search`


## Ölçülemeyen senaryolar

Servis iki denemede de düştü. Bu satırlar **hiçbir doğruluk paydasına girmiyor**: modelin yanlışı değil, ölçümün eksiği. Yanlış cevap sayılsalardı model servisin kopmasından sorumlu tutulurdu; hiç yazılmasalardı payda sessizce küçülür ve rapor eksikliğini gizlerdi (Kural 13, Kural 14).

**Bir sayı burada görünüyorsa o koşu eksiktir ve öyle okunmalıdır.**

**Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izli)** — 1/10:

- `gec-09`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: 

**Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izsiz)** — 1/10:

- `gec-09`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: 


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × cli** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `71` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB (yaklaşık %71 boş)

Sistem belleği açısından oldukça rahat bir durumda.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `29` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB

Genel olarak bellek kullanımı oldukça düşük (%29 civarı) ve sistem rahat çalışıyor.`

**Qwen3.6-35B-A3B-IQ4_XS × json** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `29` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB

Genel olarak bellek kullanımı oldukça düşük (%29 civarı) ve sistem rahat çalışıyor.`

**Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `29` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB

Genel olarak bellek kullanımı oldukça düşük (%29 civarı) ve sistem rahat çalışıyor.`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli — 6/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target cihaz_adi`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name Yeni Kişi`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken '"Anneni ara ve doğum gününü kutla."' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:01:00Z --message "Anneni ara ve doğum gününü kutla."`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 — 0/8

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik — 5/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'Bugün çok yoğun geçti.' geldi — çıktı: `<tool> note_create --body Bugün çok yoğun geçti.`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul --fields temperature`
- `sag-07` (serbest metin): body: '"acele etme" dedi, ben de tamam dedim' beklenirken 'acele etme dedi, ben de tamam dedim.' geldi — çıktı: `<tool> note_create --body acele etme dedi, ben de tamam dedim.`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature,humidity`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`

### Qwen3.6-35B-A3B-IQ4_XS × cli × uzun — 0/4

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) — 4/10

- `gec-02` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city İzmir --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message On saniye sonra bir şey yapman gerekiyor.`
- `gec-09` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) — 4/10

- `gec-02` (tek tool): city: 'İzmir' beklenirken '"İzmir"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "İzmir" --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message On saniye sonra bir şey yapman gerekiyor.`
- `gec-09` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu — 10/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone ""`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query ""`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target device_name`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T17:00:00Z --message "Hatırlatma zamanı geldi!"`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name ?`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken '"süt, ekmek ve yumurta almayı unutma."' geldi — çıktı: `<tool> note_create --body "süt, ekmek ve yumurta almayı unutma."`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken '"annemi ara ve doğum gününü kutla"' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:01:00Z --message "annemi ara ve doğum gününü kutla"`

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol — 5/18

- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-10` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message "Deneme hatırlatıcısı"`
- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-18` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 4`

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × adim2 — 0/8

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × saglamlik — 5/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'Bugün çok yoğun geçti.' geldi — çıktı: `<tool> note_create --body Bugün çok yoğun geçti.`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> weather --city "kullanıcı" --fields temperature`
- `sag-06` (ayırt etme): note_delete beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 3`
- `sag-07` (serbest metin): body: '"acele etme" dedi, ben de tamam dedim' beklenirken 'acele etme dedi, ben de tamam dedim.' geldi — çıktı: `<tool> note_create --body acele etme dedi, ben de tamam dedim.`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature,humidity`

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × uzun — 0/4

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message on saniye sonra bir şey yapman gerekiyor`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × geçmiş(izsiz) — 3/10

- `gec-02` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city İzmir --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message on saniye sonra bir şey yapman gerekiyor`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × json — 5/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "default_device"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × adim2 — 1/8

- `adm-05` (çok tool): 2. adım: contact_save beklenirken çağrı üretilmedi — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik — 4/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'bugün çok yoğun geçti.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "bugün çok yoğun geçti."}}`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "humidity"]}}`
- `sag-10` (eksik argüman): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × uzun — 0/4

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu — 10/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "default_device"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:00:00Z", "message": "Hatırlatma zamanı!"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`
- `yok-06` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol — 9/18

- `kon-03` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-16` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-18` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × adim2 — 1/8

- `adm-08` (tek tool): 2. adım: düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Zeynep"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × saglamlik — 5/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'bugün çok yoğun geçti.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "bugün çok yoğun geçti."}}`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `sag-06` (ayırt etme): note_delete beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 3}}`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "humidity"]}}`
- `sag-10` (eksik argüman): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × uzun — 0/4

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × geçmiş(izsiz) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
