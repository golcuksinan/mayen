# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/LFM2.5-2.6B-Q8_0.gguf` (Q8_0)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.009999999776482582, `top_k`=50, `top_p`=0.949999988079071, `min_p`=0.05000000074505806, `repeat_penalty`=1.100000023841858, `presence_penalty`=0.0, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Toplam

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool | uydurulan argüman | desteksiz sayı (n) | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli | 50 | 60% [46%–72%] | 41% | — | 0 | 5 | 1 (5) | 4 | 83 | 0.05 | 0.57 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × kontrol | 18 | 17% [6%–39%] | — | — | 0 | 9 | 0 (0) | 6 | 21 | 0.04 | 0.37 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × adim2 | 8 | 75% [41%–93%] | 33% | 67% [30%–90%] (6) | 0 | 0 | 0 (0) | 0 | 43 | 0.05 | 0.27 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × saglamlik | 10 | 70% [40%–89%] | 67% | — | 0 | 4 | 0 (0) | 3 | 96 | 0.04 | 0.87 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × uzun | 4 | 100% [51%–100%] | 75% | — | 0 | 0 | 0 (4) | 0 | 52 | 0.06 | 0.34 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izli) | 10 | 50% [24%–76%] | 50% | — | 0 | 4 | 0 (2) | 3 | 32 | 0.05 | 0.44 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izsiz) | 10 | 50% [24%–76%] | 50% | — | 0 | 4 | 0 (2) | 3 | 20 | 0.05 | 0.21 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu | 50 | 60% [46%–72%] | 39% | — | 0 | 9 | 4 (5) | 7 | 78 | 0.04 | 0.62 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × kontrol | 18 | 11% [3%–33%] | — | — | 0 | 8 | 0 (0) | 6 | 49 | 0.04 | 0.70 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × adim2 | 8 | 75% [41%–93%] | 33% | 67% [30%–90%] (6) | 0 | 0 | 0 (0) | 0 | 71 | 0.04 | 0.41 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × saglamlik | 10 | 50% [24%–76%] | 80% | — | 0 | 5 | 0 (0) | 4 | 76 | 0.04 | 0.84 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × uzun | 4 | 100% [51%–100%] | 75% | — | 0 | 0 | 0 (4) | 0 | 89 | 0.05 | 0.49 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izli) | 10 | 50% [24%–76%] | 60% | — | 0 | 4 | 0 (2) | 3 | 46 | 0.05 | 0.55 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izsiz) | 10 | 50% [24%–76%] | 60% | — | 0 | 4 | 0 (2) | 3 | 26 | 0.04 | 0.27 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json | 50 | 58% [44%–71%] | 76% | — | 0 | 0 | 1 (5) | 0 | 20 | 0.05 | 0.15 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × kontrol | 18 | 0% [0%–18%] | — | — | 0 | 0 | 0 (0) | 0 | 19 | 0.05 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × adim2 | 8 | 75% [41%–93%] | 83% | 67% [30%–90%] (6) | 0 | 0 | 0 (0) | 1 | 18 | 0.05 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × saglamlik | 10 | 60% [31%–83%] | 83% | — | 0 | 0 | 0 (0) | 0 | 23 | 0.05 | 0.16 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 18 | 0.06 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izli) | 10 | 50% [24%–76%] | 100% | — | 0 | 0 | 0 (2) | 0 | 19 | 0.05 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izsiz) | 10 | 60% [31%–83%] | 80% | — | 0 | 0 | 0 (3) | 0 | 19 | 0.05 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu | 50 | 60% [46%–72%] | 70% | — | 0 | 0 | 2 (5) | 0 | 20 | 0.04 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × kontrol | 18 | 0% [0%–18%] | — | — | 0 | 0 | 0 (0) | 0 | 20 | 0.04 | 0.13 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × adim2 | 8 | 75% [41%–93%] | 83% | 67% [30%–90%] (6) | 0 | 0 | 0 (0) | 1 | 18 | 0.04 | 0.13 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × saglamlik | 10 | 60% [31%–83%] | 83% | — | 0 | 0 | 0 (0) | 0 | 23 | 0.04 | 0.15 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 18 | 0.05 | 0.14 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izli) | 10 | 60% [31%–83%] | 83% | — | 0 | 0 | 0 (3) | 0 | 25 | 0.05 | 0.17 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izsiz) | 10 | 60% [31%–83%] | 83% | — | 0 | 0 | 0 (3) | 0 | 23 | 0.04 | 0.16 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli | 100% | 33% | 14% | 25% | 75% | 71% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × kontrol | — | — | — | 17% | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × adim2 | 100% | 80% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × saglamlik | 100% | — | 100% | — | 100% | 25% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × uzun | 100% | — | — | — | — | 100% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izli) | 50% | — | — | 50% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izsiz) | 50% | — | — | 50% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu | 100% | 33% | 14% | 12% | 88% | 71% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × kontrol | — | — | — | 11% | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × adim2 | 100% | 80% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × saglamlik | 75% | — | 0% | — | 100% | 25% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × uzun | 100% | — | — | — | — | 100% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izli) | 67% | — | — | 0% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izsiz) | 67% | — | — | 0% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json | 100% | 33% | 0% | 0% | 88% | 86% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × kontrol | — | — | — | 0% | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × adim2 | 100% | 80% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × saglamlik | 100% | — | 0% | — | 100% | 25% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × uzun | 100% | — | — | — | — | 100% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izli) | 50% | — | — | 50% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izsiz) | 67% | — | — | 50% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu | 100% | 50% | 0% | 0% | 88% | 86% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × kontrol | — | — | — | 0% | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × adim2 | 100% | 80% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × saglamlik | 100% | — | 0% | — | 100% | 25% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × uzun | 100% | — | — | — | — | 100% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izli) | 83% | — | — | 0% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izsiz) | 83% | — | — | 0% | 100% | 0% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli | 60% (50) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × kontrol | 17% (18) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × adim2 | 75% (8) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × saglamlik | 70% (10) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × uzun | 100% (4) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izli) | — | 40% (5) | 60% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izsiz) | — | 40% (5) | 60% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu | 60% (50) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × kontrol | 11% (18) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × adim2 | 75% (8) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × saglamlik | 50% (10) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × uzun | 100% (4) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izli) | — | 40% (5) | 60% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izsiz) | — | 40% (5) | 60% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json | 58% (50) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × kontrol | 0% (18) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × adim2 | 75% (8) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × saglamlik | 60% (10) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × uzun | 100% (4) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izli) | — | 60% (5) | 40% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izsiz) | — | 60% (5) | 60% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu | 60% (50) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × kontrol | 0% (18) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × adim2 | 75% (8) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × saglamlik | 60% (10) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × uzun | 100% (4) | — | — |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izli) | — | 60% (5) | 60% (5) |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izsiz) | — | 60% (5) | 60% (5) |

## Zorunlu mod: `no_tool` kullanımı

Zorunlu modda çağrı gerekmeyen tur `<tool> no_tool` yazarak kapanır, yani **iki sütun eşit olmalı**: gramer başka bir çıkış yolu bırakmıyor. Eşit değilse aradaki fark, düzeltme tavanına kadar geçerli bir çağrı üretilemeyen turlardır — tek bir doğruluk yüzdesinde bu iki başarısızlık aynı görünür.

| koşu | mod | `no_tool` | çağrı üretilmeyen tur |
|---|---|---:|---:|
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli | serbest | 0 | 3 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × kontrol | serbest | 0 | 3 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × adim2 | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × saglamlik | serbest | 0 | 1 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × uzun | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izli) | serbest | 0 | 4 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izsiz) | serbest | 0 | 4 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu | zorunlu | 0 | 2 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × kontrol | zorunlu | 0 | 2 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × adim2 | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × saglamlik | zorunlu | 0 | 1 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × uzun | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izli) | zorunlu | 0 | 1 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izsiz) | zorunlu | 0 | 1 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × kontrol | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × adim2 | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × saglamlik | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × uzun | serbest | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izli) | serbest | 0 | 4 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izsiz) | serbest | 0 | 3 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × kontrol | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × adim2 | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × saglamlik | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × uzun | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izli) | zorunlu | 0 | 0 |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izsiz) | zorunlu | 0 | 0 |

## İkinci adım

Tool sonucu geri beslendikten sonraki adım (P25.2). Zincirin ikinci halkası bugüne kadar hiç ölçülmemişti; `Step2.expected` `None` olan satırlarda doğru davranış **çağrı yazmamaktır** — o satırlar olmadan bu sayaç, fazla çağrıyı iyileşme diye raporlardı.

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × adim2** — ikinci adımda düşenler:

- `adm-07`: 2. adımda `weather`
- `adm-08`: 2. adımda `contact_get`

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × adim2** — ikinci adımda düşenler:

- `adm-07`: 2. adımda `weather`
- `adm-08`: 2. adımda `contact_get`

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × adim2** — ikinci adımda düşenler:

- `adm-07`: 2. adımda `date_time`
- `adm-08`: 2. adımda `contact_get`

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × adim2** — ikinci adımda düşenler:

- `adm-07`: 2. adımda `date_time`
- `adm-08`: 2. adımda `contact_get`


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `Saat şu an 9:00 UTC'tur. (Gün 7 = Pazar)`

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `Şu an 2026-08-09T09:00:00Z (Pazartesi) saat 9:00 UTC'tur.`
- `tek-05`: `0.294`, `29` — yanıt: `Bilgisayarın durumu şu an şöyledir:

- **CPU%** : 12% (çok düşük, çok rahat çalışıyor)
- **Toplam bellek** : 32 GB
- **Kullanılmış bellek** : 9.4 GB

Bu durumda bellek kullanımı %29 civarındadır (9.4/32 ≈ 0.294), yani hala yeterli kapasitede. Bellek çok dolmamış, rahat bir durumdadır.

Eğer daha detaylı bellek analizi yapmanız isterseniz, `fact_list` toolü ile de bilgi alabilirsiniz. Ancak şu anki durumda bellek kısıtlaması yok.`
- `tek-10`: `1` — yanıt: ````json
{
  "task_list": [
    {
      "id": 4,
      "due": "2026-08-10T06:00:00Z",
      "message": "ilaç"
    }
  ]
}
```

Bekleyen hatırlatıcılarınız şu şekilde listelenmiştir:

1. **ID: 4** - *ilaç* (2026-08-10T06:00:00Z)

Bu görev, gelecekte 2026-08-10 tarihinde 06:00 UTC'ye kadar "ilaç" ifadesi ile hatırlatılacaktır. Başka bekleyen görevler yoktur.`

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × json** — desteksiz sayı geçen senaryolar:

- `tek-05`: `29.1` — yanıt: `Bilgisayarın belleği şu an 9.4 GB kullanılmış, toplam kapasite 32 GB'dir. Yani kullanım oranı yaklaşık %29.1'dir. Bellek durumu açısından bakarsak, 9.4 GB kullanılarak 32 GB'lik bellek capacity'te 29.1% kullanımı yapıyor.`

**LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `Saat 9:00 (2026-08-09T09:00:00Z) - Şu an saat 9:00'te.`
- `tek-05`: `29.5` — yanıt: `Bilgisayarın durumu şu an şöyledir:

- **CPU Yükü:** 12%
- **Toplam Bellek:** 32 GB
- **Kullanılmış Bellek:** 9.4 GB

Bellek kullanımı yaklaşık %29,5 oranında (9.4/32) olduğu için hala yeterli durumdadır. Sistem çok yavaş değil, normal çalışıyor.`

## Başarısız senaryolar

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli — 36/50

- `tek-02` (tek tool): name: 'Veli' beklenirken '"Veli" || contact_get || note_search || system_metrics || fact_list || course_schedule || task_create || weather || date_time || task_list || task_cancel || note_delete || fact_forget || wake_on_lan || system_metrics || contact_save || contact_delete || note_create || date_time || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || course_schedule || contact_get || contact_save || contact_delete || note_search || note_create || task_create || task_list || task_cancel || weather || date_time || system_metrics || fact_list || fact_forget || wake_on_lan || tool_adi || date_time || contact_get || contact_save || contact_delete || note_search || note_create || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || course_schedule || date_time || system_metrics || contact_get || contact_save || contact_delete || note_search || note_create || task_create || task_list || task_cancel || weather || date_time || system_metrics || fact_list || fact_forget || wake_on_lan || tool_' geldi — çıktı: `<tool> contact_get --name "Veli" || contact_get || note_search || system_metrics || fact_list || course_schedule || task`
- `tek-03` (tek tool): city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" > "Denizli hava durumu"`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken '"Istanbul"' geldi; fields: 'temperature' beklenirken 'temperature | etki: DIŞ | değer: 32°C (Bu değer hava durumunun sıcaklığını gösterir) | alan: temperature | değer: 32°C | alan: condition | değer: Sıcak | alan: city | değer: İstanbul | alan: fields | değer: ["temperature"] | alan: city | değer: İstanbul | alan: fields | değer: ["temperature", "condition"] | alan: temperature | değer: 32 | alan: condition | değer: Sıcak | alan: city | değer: İstanbul | alan: fields | değer: ["temperature", "condition"] | alan: temperature | değer: 32 | alan: condition | değer: Sıcak | alan: city | değer: İstanbul | alan: fields | değer: ["temperature", "condition"] | alan: temperature | değer: 32 | alan: condition | değer: Sıcak | alan: city | değer: İstanbul | alan: fields | değer: ["temperature", "condition"] | alan: temperature | değer: 32 | alan: condition | değer: Sıcak | alan: city | değer: İstanbul | alan: fields | değer: ["temperature", "' geldi — çıktı: `<tool> weather --city "Istanbul" --fields temperature | etki: DIŞ | değer: 32°C (Bu değer hava durumunun sıcaklığını gös`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken '"masaüstü bilgisayarı" , etki: GERİ_ALINAMAZ (onay ister)' geldi — çıktı: `<tool> wake_on_lan --target "masaüstü bilgisayarı" , etki: GERİ_ALINAMAZ (onay ister)`
- `tek-08` (tek tool): name: 'Ali' beklenirken '"Ali" */' geldi — çıktı: `<tool> contact_get --name "Ali" */`
- `tek-09` (tek tool): name fazladan verildi — çıktı: `<tool> contact_get --name "Rehber" || contact_get || contact_get [--name "Rehber"] /contact_get [--name "Rehber"] || con`
- `tek-11` (tek tool): day fazladan verildi — çıktı: `<tool> course_schedule --day 1`
- `cok-01` (çok tool): name: 'Ali' beklenirken '"Ali" || contact_get || contact_save || note_create || task_create || system_metrics || fact_list || weather || date_time || course_schedule || task_list || task_cancel || wake_on_lan || fact_forget || system_metrics || date_time || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact_list || weather || contact_get || note_create || task_create || system_metrics || fact' geldi — çıktı: `<tool> contact_get --name "Ali" || contact_get || contact_save || note_create || task_create || system_metrics || fact_l`
- `cok-02` (çok tool): weather: imzada böyle bir argüman yok: 'başka_alan'; date_time beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Ankara" etki: DIŞ | not: Weather tool ile Ankara hava durumu verisi alındı. Saat 2026-08-09T09:00`
- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 2`
- `cok-04` (çok tool): weather: imzada böyle bir argüman yok: 'alan'; course_schedule beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ | Not: Hava durumu verisi Alındı. Denizli'de`
- `cok-06` (çok tool): contact_save beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Veli'ye" | note_search [--query "Veli'ye"] | task_create [--due "2026-08-09T14:00:00Z", "--me`
- `eks-02` (eksik argüman): düz metin beklenirken note_delete çağrıldı — çıktı: `<tool> note_delete --id 1`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target "Cihaz adı" , etki: GERİ_ALINAMAZ (onay ister)`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due "2026-08-10T14:00:00Z" --message "Günlük görev hatırlatması" > YAZMA`
- `eks-05` (eksik argüman): düz metin beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 0`
- `eks-06` (eksik argüman): düz metin beklenirken contact_delete çağrıldı — çıktı: `<tool> contact_delete --name "Adınız" ", etki: GERİ_ALINAMAZ (onay ister) >`
- `eks-07` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Yeni Kişi" || contact_save "--name New Person" || contact_delete "--name New Person" || note_`
- `yok-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `yok-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `yok-04` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Paris" --fields "temperature, condition" > "Paris hava durumu" | python3 -c "print('Paris başkent`
- `yok-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `yok-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `yok-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `ayr-01` (ayırt etme): query: 'alışveriş' beklenirken '"alışveriş" --alan değer "notlar" --etki OKUMA > 0 | jq -r \'.[] | .body\' | head -n 1 | xargs -I {} echo "{}" | python3 -c "import sys; print(sys.stdin.read().strip())" | grep -oP \'(?s).*?\' || true' geldi — çıktı: `<tool> note_search --query "alışveriş" --alan değer "notlar" --etki OKUMA > 0 | jq -r '.[] | .body' | head -n 1 | xargs `
- `ayr-02` (ayırt etme): body: 'Alışveriş' beklenirken '"Alışveriş" --etki YAZMA' geldi — çıktı: `<tool> note_create --body "Alışveriş" --etki YAZMA`
- `ayr-03` (ayırt etme): contact_save beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Ayşe" */ Rehberdeki kişileri listeler; ad verilirse ona göre süzer. */ Etki: OKUMA (Bu adın v`
- `ayr-04` (ayırt etme): name: 'Ayşe' beklenirken '"Ayşe" */' geldi — çıktı: `<tool> contact_get --name "Ayşe" */`
- `ayr-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `ayr-07` (ayırt etme): name: 'Ali' beklenirken "Ali'ı siler | etki: GERİ_ALINAMAZ (onay ister) ```" geldi — çıktı: `<tool> contact_delete --name Ali'ı siler | etki: GERİ_ALINAMAZ (onay ister) ````
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken '"süt, ekmek ve yumurta almayı unutma" --etki YAZMA > not_1",0"> Notu oluşturuyor... (Bu işlem bitince not numarası 1 olarak kaydedilecek)' geldi — çıktı: `<tool> note_create --body "süt, ekmek ve yumurta almayı unutma" --etki YAZMA > not_1",0"> Notu oluşturuyor... (Bu işlem `
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken '"yarın erken kalk" --önemli --önemli_ayar "yarın erken kalk" --başka_alan "yarın erken kalk" etki: YAZMA > "Not oluştur" | "Yazıldı" | "Tool çağırma" | "note_create" | "Body: yarın erken kalk" | "Önemli: Evet" | "İşlem başarıyla tamamlandı." | "Tool çağırma sonucu: YAZMA" > "Not oluştur" | "yarın erken kalk" | "önemli" | "yarın erken kalk" | "Yazıldı" | "Tool çağırma" | "note_create" | "Body: yarın erken kalk" | "İşlem başarıyla tamamlandı." > "Not oluştur" | "yarın erken kalk" | "önemli" | "yarın erken kalk" | "Yazıldı" | "Tool çağırma" | "note_create" | "Body: yarın erken kalk" | "İşlem başarıyla tamamlandı." > "Not oluştur" |' geldi — çıktı: `<tool> note_create --body "yarın erken kalk" --önemli --önemli_ayar "yarın erken kalk" --başka_alan "yarın erken kalk" e`
- `ser-03` (serbest metin): note_create beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Ali" >`
- `ser-05` (serbest metin): task_create beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken '"Kütüphane kitabını ayın on beşine kadar geri ver." --etki="YAZMA"' geldi — çıktı: `<tool> note_create --body "Kütüphane kitabını ayın on beşine kadar geri ver." --etki="YAZMA"`
- `ser-07` (serbest metin): query: 'elektrik faturası' beklenirken '"elektrik faturası" --alan değer --başka_alan çok kelimeli değer "elektrik faturası" | okuma | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur | not_lisansla_okunur' geldi — çıktı: `<tool> note_search --query "elektrik faturası" --alan değer --başka_alan çok kelimeli değer "elektrik faturası" | okuma `

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × kontrol — 15/18

- `kon-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-03` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-04` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-08` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-10` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-11` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "not" --başka_alan "notlar" --etki OKUMA, notlarınızın listesini alayım. Notlarınız var mı di`
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Rehber" etki: OKUMA`
- `kon-13` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-14` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-16` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Ali" */ Rehberdeki kişileri listeler; ad verilirse ona göre süzer. Ali adlı kişi bulursa onu `
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-18` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 2`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × adim2 — 7/8

- `adm-01` (çok tool): name: 'Veli' beklenirken '"Veli" || contact_get || contact_save || note_create || task_create || system_metrics || fact_list || weather || date_time || course_schedule || task_list || task_cancel || wake_on_lan || fact_forget || tool_adi || note_search || contact_delete || date_time || system_metrics || fact_list || weather || course_schedule || task_create || task_list || task_cancel || wake_on_lan || fact_forget || tool_adi || note_search || contact_get || contact_save || contact_delete || date_time || system_metrics || fact_list || weather || course_schedule || task_create || task_list || task_cancel || wake_on_lan || fact_forget || tool_adi || note_create || note_delete || course_schedule || task_create || task_list || task_cancel || wake_on_lan || fact_forget || system_metrics || date_time || contact_get || contact_save || contact_delete || note_search || note_create || note_delete || weather || system_metrics || fact_list || fact_forget || tool_adi || date_time || course_schedule || task_create || task_list || task_cancel || wake_on_lan || fact_forget || system_metrics' geldi — çıktı: `<tool> contact_get --name "Veli" || contact_get || contact_save || note_create || task_create || system_metrics || fact_`
- `adm-02` (çok tool): 2. adım: city: 'İzmir' beklenirken '"İzmir"' geldi — çıktı: `<tool> date_time`
- `adm-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 1`
- `adm-05` (çok tool): name: 'Ayşe' beklenirken '"Ayşe" */' geldi; 2. adım: name: 'Ayşe' beklenirken '"Ayşe" */' geldi — çıktı: `<tool> contact_get --name "Ayşe" */`
- `adm-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `adm-07` (tek tool): city: 'Bursa' beklenirken '"Bursa"' geldi; fields fazladan verildi; 2. adım: düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Bursa" --fields "temperature, condition" > {"temperature": "23°C", "condition": "Güzel"}`
- `adm-08` (tek tool): name: 'Zeynep' beklenirken '"Zeynep" */' geldi; 2. adım: düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Zeynep" */`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × saglamlik — 5/10

- `sag-01` (serbest metin): note_create beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "bugün" --fields "temperature, condition" --city "İstanbul" --fields "temperature, condition"`
- `sag-02` (serbest metin): weather: imzada böyle bir argüman yok: 'başka_alan'; note_create beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Istanbul" --fields temperature, condition etki: DIŞ | Not al: sıcaklık 18°C, hafif rüzgân | Montu`
- `sag-07` (serbest metin): note_create beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "acele etme" --başka_alan "not" --etki OKUMA > not_sonu || true; echo "Not bulundu" >> /tmp/n`
- `sag-08` (serbest metin): body: 'sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en son da haberleri aç' beklenirken '"Sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en son da haberleri aç." --etki: YAZMA' geldi — çıktı: `<tool> note_create --body "Sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken '"Istanbul"' geldi — çıktı: `<tool> weather --city "Istanbul" --fields "temperature, condition" > "İstanbul hava durumu: sıcaklık {temperature}°C, ko`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × uzun — 1/4

- `uzn-03` (tek tool): name fazladan verildi — çıktı: `<tool> contact_get --name "" etki: OKUMA », bu komut rehberdeki tüm kişileri listeler. Sonraki adımda sayımı yapabilirim`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izli) — 7/10

- `gec-01` (tek tool): weather: imzada böyle bir argüman yok: 'alan'; city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ`
- `gec-02` (tek tool): weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather beklenirken çağrı üretilmedi — çıktı: `<tool> weather --city "İzmir" --fields temperature, condition --alan değer | Denizli'de hava açık, otuz bir derece. | İz`
- `gec-04` (tek tool): task_list beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "Sağ ol, iyi geceler" --başka_alan notlar_arama_sonucu --etki OKUMA`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `Su içme hatırlatması için 1 dakika bekliyorum...`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `Notun içeriği "kitabı geri ver" idi.`
- `gec-09` (tek tool): city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition"`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × geçmiş(izsiz) — 7/10

- `gec-01` (tek tool): weather: imzada böyle bir argüman yok: 'başka_alan'; city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ`
- `gec-02` (tek tool): weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather beklenirken çağrı üretilmedi — çıktı: `<tool> weather --city "İzmir" --fields temperature, condition --alan değer "İzmir hava durumu" --başka_alan "Denizli hav`
- `gec-04` (tek tool): task_list beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "sağ ol, iyi geceler"`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `Su içme hatırlatması için 1 dakika bekliyorum...`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `Notun içeriği "kitabı geri ver" idi.`
- `gec-09` (tek tool): city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition"`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu — 37/50

- `tek-02` (tek tool): name: 'Veli' beklenirken '"Veli" || contact_get || contact_save || note_search || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || system_metrics || fact_list || fact_forget || wake_on_lan || contact_get || contact_save || note_search || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || system_metrics || fact_list || fact_forget || wake_on_lan || contact_get || contact_save || note_search || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || system_metrics || fact_list || fact_forget || wake_on_lan || contact_get || contact_save || note_search || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || system' geldi — çıktı: `<tool> contact_get --name "Veli" || contact_get || contact_save || note_search || course_schedule || task_create || task`
- `tek-03` (tek tool): city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" > weather_cevap | python3 -c "print(weather_cevap)" | `
- `tek-04` (tek tool): city: 'İstanbul' beklenirken '"Istanbul"' geldi; fields: 'temperature' beklenirken 'temperature **etki: DIŞ**' geldi — çıktı: `<tool> weather --city "Istanbul" --fields temperature **etki: DIŞ**`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken '"masaüstü bilgisayarı" , etki: GERİ_ALINAMAZ (onay ister)' geldi — çıktı: `<tool> wake_on_lan --target "masaüstü bilgisayarı" , etki: GERİ_ALINAMAZ (onay ister)`
- `tek-08` (tek tool): name: 'Ali' beklenirken '"Ali" || contact_get || note_search || course_schedule || task_create || task_list || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || no_tool || tool_adi || contact_save || contact_delete || note_create || task_cancel || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || no_tool || tool_adi || contact_get || contact_save || contact_delete || note_search || note_create || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || no_tool || tool_adi || contact_get || contact_save || contact_delete || note_search || note_create || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || no_tool || tool_adi || contact_get || contact_save || contact_delete || note_search || note_create || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || no_tool || tool_' geldi — çıktı: `<tool> contact_get --name "Ali" || contact_get || note_search || course_schedule || task_create || task_list || weather `
- `tek-09` (tek tool): name fazladan verildi — çıktı: `<tool> contact_get --name "Rehber" || contact_get || contact_get [--name "Rehber"] ", " " >`
- `tek-11` (tek tool): day fazladan verildi — çıktı: `<tool> course_schedule --day 1`
- `cok-01` (çok tool): name: 'Ali' beklenirken '"Ali" || contact_get || contact_save || note_create || task_create || system_metrics || fact_list || wake_on_lan || date_time || course_schedule || task_list || weather || fact_forget || contact_delete || note_search || date_time || contact_get || contact_save || contact_delete || note_create || task_create || task_list || weather || system_metrics || fact_list || fact_forget || wake_on_lan || tool_adi || no_tool || bir_tools_kullanimisiz_mesaj | "Ali\'nin numarasını bul, sonra ona akşam ararım diye not düş" | "tool_adi" || "no_tool" || "bir_tools_kullanimisiz_mesaj" | "Ali\'nin numarasını bul, sonra ona akşam ararım diye not düş" | "note_create" || "task_create" || "system_metrics" || "fact_list" || "wake_on_lan" || "date_time" || "course_schedule" || "task_list" || "weather" || "system_metrics" || "fact_forget" || "contact_delete" || "note_search" | "Ali\'nin' geldi — çıktı: `<tool> contact_get --name "Ali" || contact_get || contact_save || note_create || task_create || system_metrics || fact_l`
- `cok-02` (çok tool): weather: imzada böyle bir argüman yok: 'başka_alan'; date_time beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Ankara" --fields "temperature, condition" etki: DIŞ | okudu: "Ankara hava durumu: 22°C, güneşli" `
- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 2`
- `cok-04` (çok tool): weather: imzada böyle bir argüman yok: 'alan'; course_schedule beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ | Not: Hava durumu sorgulandı. | Cevap: Deni`
- `cok-06` (çok tool): contact_save beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Veli'ye" || true && contact_save [--name "Veli'ye"] || true && task_create [--due "2026-08-09`
- `eks-02` (eksik argüman): düz metin beklenirken note_delete çağrıldı — çıktı: `<tool> note_delete --id 1`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target "Cihaz adı" —alan değer: "Cihaz adı" (tek satır)`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due "2026-08-10T14:00:00Z" --message "Günlük görev hatırlatması" >`
- `eks-05` (eksik argüman): düz metin beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 0`
- `eks-06` (eksik argüman): düz metin beklenirken contact_delete çağrıldı — çıktı: `<tool> contact_delete --name "Aranacak kişi adı" > Geri alınmayacaktır (onay ister)`
- `eks-07` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Aranacak kişi adı" >`
- `yok-01` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `yok-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `yok-03` (tool gerekmez): weather: imzada böyle bir argüman yok: 'başka_alan'; düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Istanbul" --fields temperature, condition etki: DIŞ > 0.5 | 28°C | "Güneşli ve hafif rüzgâr" (oku`
- `yok-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `yok-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `yok-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `yok-08` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `ayr-01` (ayırt etme): query: 'alışveriş' beklenirken '"alışveriş" --alan değer --başka_alan çok kelimeli değer | head -n 20 | jq -r \'.[] | .id\' | while read id; do echo "$id"; done | xargs -I {} note_get --id {} | grep -A5 "Notun metni" | tail -n +2 | sed \'s/^[[:space:]]*//\' | head -1 | jq -r \'.body // empty\' | tr \'\\n\' \' \' | sed \'s/  */ /g\' | xargs -I {} echo "--- {} ---" | while read line; do if [ "$line" = "Notun metni" ]; then continue; fi; done | grep -v "^$" | head -1 | tr \'\\n\' \' \' | sed \'s/  */ /g\' | xargs -I {} echo "--- {} ---" | while read line; do if [ "$line" = "Notun metni" ]; then continue; fi; done | grep -v "^$" | head -1 | tr \'\\n\' \' \' | sed \'s/  */ /g\'' geldi — çıktı: `<tool> note_search --query "alışveriş" --alan değer --başka_alan çok kelimeli değer | head -n 20 | jq -r '.[] | .id' | w`
- `ayr-02` (ayırt etme): body: 'Alışveriş' beklenirken '"Alışveriş" --etki YAZMA' geldi — çıktı: `<tool> note_create --body "Alışveriş" --etki YAZMA`
- `ayr-03` (ayırt etme): name: 'Ayşe' beklenirken "Ayşe'ye" geldi; phone fazladan verildi — çıktı: `<tool> contact_save --name Ayşe'ye --phone "0541234567"`
- `ayr-04` (ayırt etme): name: 'Ayşe' beklenirken '"Ayşe" */' geldi — çıktı: `<tool> contact_get --name "Ayşe" */`
- `ayr-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `ayr-07` (ayırt etme): name: 'Ali' beklenirken "Ali'ı siler | GERİ_ALINAMAZ (onay ister) | Silinmeyi onaylayın, onay verirse işlem yapılır. |" geldi — çıktı: `<tool> contact_delete --name Ali'ı siler | GERİ_ALINAMAZ (onay ister) | Silinmeyi onaylayın, onay verirse işlem yapılır.`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken '"süt, ekmek ve yumurta almayı unutma" --etki YAZMA' geldi — çıktı: `<tool> note_create --body "süt, ekmek ve yumurta almayı unutma" --etki YAZMA`
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken '"yarın erken kalk" --önemli --önemli_ayar "yarın erken kalk" --başka_alan "yarın erken kalk" etki: YAZMA > 2026-08-09T10:00:00Z (geri alınabilir) > Not oluşturuldu. > Sonraki adımda bu notu listelemek için task_list veya note_search kullanabiliriz. > Ancak kullanıcı sadece "not oluştur" dedi, bu yüzden not oluşturma işlemi tamamlandı. > Şimdi bir sonraki adımda ne yapmalıyız? > Önceki adımda not oluşturuldu, şimdi bu notu listelemek veya başka bir işlem yapmak gerekebilir. > Kullanıcıya notun oluşturulduğunu bildiririm ve sonraki adımı sorarım. > Ancak sistem, not oluşturma işlemi tamamlandı. > Sonuç: Not oluşturuldu. > Şimdi kullanıcı ne istiyor? > "Bir tool çağırmak için tek satır yaz" ifadesiyle başlamış ama bu bir tool çağırma değil' geldi — çıktı: `<tool> note_create --body "yarın erken kalk" --önemli --önemli_ayar "yarın erken kalk" --başka_alan "yarın erken kalk" e`
- `ser-03` (serbest metin): note_create beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Ali" >`
- `ser-05` (serbest metin): task_create beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken '"Kütüphane kitabını ayın on beşine kadar geri ver." --etki>YAZMA' geldi — çıktı: `<tool> note_create --body "Kütüphane kitabını ayın on beşine kadar geri ver." --etki>YAZMA`
- `ser-07` (serbest metin): query: 'elektrik faturası' beklenirken '"elektrik faturası" --alan değer --başka_alan çok kelimeli değer | head -n 20 | jq -r \'.results[].body\' | paste -sd \' \', -1 > /tmp/notes.txt && cat /tmp/notes.txt | wc -l", --başka_alan "notlar" | jq -r \'.count\'")]' geldi — çıktı: `<tool> note_search --query "elektrik faturası" --alan değer --başka_alan çok kelimeli değer | head -n 20 | jq -r '.resul`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × kontrol — 16/18

- `kon-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-02` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-03` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-04` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-05` (tool gerekmez): weather: imzada böyle bir argüman yok: 'başka_alan'; weather: imzada böyle bir argüman yok: 'başka_alan'; düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Istanbul" --fields temperature, condition etki: DIŞ > The current weather in Istanbul is 28°C and`
- `kon-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-08` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-10` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-11` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "not" --başka_alan "notlar" --etki OKUMA | jq -r '.[] | .id' | head -n 5 | while read id; do `
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Rehber" etki: OKUMA`
- `kon-13` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`
- `kon-14` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-16` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Ali" ", etki: OKUMA`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-18` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 2`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × adim2 — 7/8

- `adm-01` (çok tool): name: 'Veli' beklenirken '"Veli" || contact_get || contact_save || note_create || task_create || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_cancel || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_create || task_list || task_cancel || weather || system_metrics || fact_list || fact_forget || wake_on_lan || date_time || course_schedule || task_create || task_list' geldi — çıktı: `<tool> contact_get --name "Veli" || contact_get || contact_save || note_create || task_create || weather || system_metri`
- `adm-02` (çok tool): 2. adım: city: 'İzmir' beklenirken '"İzmir"' geldi — çıktı: `<tool> date_time`
- `adm-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 1`
- `adm-05` (çok tool): name: 'Ayşe' beklenirken '"Ayşe" */' geldi; 2. adım: name: 'Ayşe' beklenirken '"Ayşe" */' geldi — çıktı: `<tool> contact_get --name "Ayşe" */`
- `adm-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `adm-07` (tek tool): city: 'Bursa' beklenirken '"Bursa"' geldi; fields fazladan verildi; 2. adım: düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Bursa" --fields "temperature, condition" > weather_cevap | python3 -c "print(weather_cevap)" | tr`
- `adm-08` (tek tool): name: 'Zeynep' beklenirken '"Zeynep" */' geldi; 2. adım: düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name "Zeynep" */`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × saglamlik — 6/10

- `sag-01` (serbest metin): note_create beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "bugün" --başka_alan "not" etki: OKUMA`
- `sag-02` (serbest metin): weather: imzada böyle bir argüman yok: 'başka_alan'; note_create beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Istanbul" --fields temperature, condition etki: DIŞ | not_ok | weather_data | {"temperature": 18,`
- `sag-07` (serbest metin): note_create beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "acele etme" --başka_alan "notlar" --etki OKUMA > not_sonuc.json | python3 -c "import json,sy`
- `sag-08` (serbest metin): body: 'sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en son da haberleri aç' beklenirken '"Sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en son da haberleri aç." --etki: YAZMA' geldi — çıktı: `<tool> note_create --body "Sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en`
- `sag-09` (tek tool): weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather beklenirken çağrı üretilmedi — çıktı: `<tool> weather --city "Istanbul" --fields temperature, condition --alan değer "Istanbul hava durumu sıcaklığı" | jq -r '`
- `sag-10` (eksik argüman): weather: imzada böyle bir argüman yok: 'başka_alan'; düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city "Istanbul" --fields temperature, condition | etki: DIŞ | yanıt: Hava durumu bilgisi (temperature v`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × uzun — 1/4

- `uzn-03` (tek tool): name fazladan verildi — çıktı: `<tool> contact_get --name "" — tüm kişileri listeler. — Etki: OKUMA (Bu adımda tüm kişileri listelemek için contact_get `

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izli) — 7/10

- `gec-01` (tek tool): weather: imzada böyle bir argüman yok: 'başka_alan'; city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ`
- `gec-02` (tek tool): weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather beklenirken çağrı üretilmedi — çıktı: `<tool> weather --city "İzmir" --fields temperature, condition --alan değer "İzmir hava durumu" --başka_alan "Denizli hav`
- `gec-04` (tek tool): task_list beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "sağ ol, iyi geceler" --etki OKUMA`
- `gec-08` (serbest metin): note_search beklenirken note_create çağrıldı — çıktı: `<tool> note_create --body "kitabı geri ver" --etki YAZMA`
- `gec-09` (tek tool): city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition"`
- `gec-10` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> note_create --body "Kitabı geri ver" --etki YAZMA`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × cli × zorunlu × geçmiş(izsiz) — 7/10

- `gec-01` (tek tool): weather: imzada böyle bir argüman yok: 'başka_alan'; city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ`
- `gec-02` (tek tool): weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather: imzada böyle bir argüman yok: 'alan'; weather beklenirken çağrı üretilmedi — çıktı: `<tool> weather --city "Denizli" --fields temperature, condition --alan değer Denizli'de hava durumu için kullanılacak. S`
- `gec-04` (tek tool): task_list beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query "sağ ol" --başka_alan "notlar" etki: OKUMA`
- `gec-08` (serbest metin): note_search beklenirken note_create çağrıldı — çıktı: `<tool> note_create --body "kitabı geri ver" --etki YAZMA`
- `gec-09` (tek tool): city: 'Denizli' beklenirken '"Denizli"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "Denizli" --fields "temperature, condition"`
- `gec-10` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> note_create --body "Kitabı geri ver" --etki YAZMA`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json — 28/50

- `tek-02` (tek tool): name eksik — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi; fields eksik — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-11` (tek tool): day fazladan verildi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
- `cok-01` (çok tool): name eksik — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 2}}`
- `cok-04` (çok tool): course_schedule beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `cok-06` (çok tool): contact_save beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Veli"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_delete çağrıldı — çıktı: `<tool> {"name": "note_delete", "arguments": {"id": 1}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "Cihazın adı"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Hatırlatıcı görev"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 1}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_delete çağrıldı — çıktı: `<tool> {"name": "contact_delete", "arguments": {"name": "Rehberden birini sil"}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi", "phone": "+1234567890"}}`
- `yok-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `yok-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `yok-03` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `yok-04` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Paris"}}`
- `yok-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `yok-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-07` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-08` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `ayr-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken 'yarin erken kalk' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "yarin erken kalk"}}`
- `ser-03` (serbest metin): body: "Ali'ye akşam mesaj at, cevap gelmezse tekrar dene" beklenirken "Ali'ye akşam mesaj at" geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Ali'ye akşam mesaj at"}}`
- `ser-05` (serbest metin): task_create beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "annem doğum günü"}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × kontrol — 18/18

- `kon-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-03` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-04` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "güzel"}}`
- `kon-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-08` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `kon-10` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-11` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "not"}}`
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Rehber"}}`
- `kon-13` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-10T09:00:00Z", "message": "Önce hatırlatıcı kurmayı düşünec`
- `kon-14` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `kon-16` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-18` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 2}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × adim2 — 6/8

- `adm-01` (çok tool): name eksik — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `adm-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 1}}`
- `adm-05` (çok tool): 2. adım: phone fazladan verildi — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`
- `adm-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `adm-07` (tek tool): 2. adım: düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Bursa"}}`
- `adm-08` (tek tool): 2. adım: düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Zeynep"}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × saglamlik — 5/10

- `sag-01` (serbest metin): note_create beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "bugün"}}`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `sag-07` (serbest metin): note_create beklenirken note_delete çağrıldı — çıktı: `<tool> {"name": "note_delete", "arguments": {"id": 1}}`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi; fields eksik — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × uzun — 0/4

Yok.

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izli) — 5/10

- `gec-04` (tek tool): task_list beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "sağ ol, iyi geceler"}}`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `Su içme hatırlatması için 1 dakika sonra uyaracağım.`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `Notlar listesi:`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `Denizli'de hava şu an açık, otuz altı derece.`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × geçmiş(izsiz) — 5/10

- `gec-02` (tek tool): city: 'İzmir' beklenirken 'Denizli' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `gec-04` (tek tool): task_list beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "sağ ol, iyi geceler"}}`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `Su içme hatırlatması için 1 dakika sonra uyaracağım.`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `Notlar listesi:`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu — 29/50

- `tek-02` (tek tool): name eksik — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi; fields eksik — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-11` (tek tool): day fazladan verildi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 4}}`
- `cok-01` (çok tool): name eksik — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 2}}`
- `cok-04` (çok tool): day: '4' beklenirken '2' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 2}}`
- `cok-06` (çok tool): contact_save beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Veli"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_delete çağrıldı — çıktı: `<tool> {"name": "note_delete", "arguments": {"id": 1}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "Cihazın adı"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Belirtilen görev hatırlatılacak"`
- `eks-05` (eksik argüman): düz metin beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 1}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_delete çağrıldı — çıktı: `<tool> {"name": "contact_delete", "arguments": {"name": "Aranacak kişi adı"}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi", "phone": "+1234567890"}}`
- `yok-01` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-02` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-03` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `yok-04` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Paris"}}`
- `yok-05` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-07` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `yok-08` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `ayr-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken 'yarin erken kalk' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "yarin erken kalk"}}`
- `ser-03` (serbest metin): body: "Ali'ye akşam mesaj at, cevap gelmezse tekrar dene" beklenirken "Ali'ye akşam mesaj at" geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Ali'ye akşam mesaj at"}}`
- `ser-05` (serbest metin): task_create beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "annem doğum günü"}}`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphane kitabını ayın on beşine kadar geri ver.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Kütüphane kitabını ayın on beşine kadar geri ver."}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × kontrol — 18/18

- `kon-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-02` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-03` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-04` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-05` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `kon-06` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-07` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-08` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "condition"]}}`
- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `kon-10` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-11` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "not"}}`
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `kon-13` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Hatırlatma: Ders programı"}}`
- `kon-14` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `kon-16` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Ali ile dün konuştum, iyiymiş."}}`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-18` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 2}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × adim2 — 6/8

- `adm-01` (çok tool): name eksik — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `adm-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 1}}`
- `adm-05` (çok tool): 2. adım: phone fazladan verildi — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`
- `adm-06` (ayırt etme): task_create beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `adm-07` (tek tool): 2. adım: düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Bursa"}}`
- `adm-08` (tek tool): 2. adım: düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Zeynep"}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × saglamlik — 5/10

- `sag-01` (serbest metin): note_create beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "bugün"}}`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `sag-07` (serbest metin): note_create beklenirken note_delete çağrıldı — çıktı: `<tool> {"name": "note_delete", "arguments": {"id": 1}}`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi; fields eksik — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × uzun — 0/4

Yok.

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izli) — 5/10

- `gec-02` (tek tool): fields fazladan verildi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İzmir", "fields": ["temperature", "condition"]}}`
- `gec-04` (tek tool): task_list beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "sağ ol, iyi geceler"}}`
- `gec-08` (serbest metin): note_search beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "kitabı geri ver"}}`
- `gec-10` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "kitabı geri ver"}}`

### LFM2.5-2.6B-Q8_0 (düşünmesiz) × json × zorunlu × geçmiş(izsiz) — 5/10

- `gec-02` (tek tool): city: 'İzmir' beklenirken 'Denizli' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `gec-04` (tek tool): task_list beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "notlar"}}`
- `gec-08` (serbest metin): note_search beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "kitabı geri ver"}}`
- `gec-10` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "kitabı geri ver"}}`
