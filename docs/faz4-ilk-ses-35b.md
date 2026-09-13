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
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 48 | 0.28 | 0.68 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | 18 | 72% [49%–88%] | — | — | 0 | 0 | 0 (0) | 0 | 5 | 0.24 | 0.28 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 73 | 0.22 | 0.80 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | 18 | 56% [34%–75%] | — | — | 0 | 0 | 0 (0) | 0 | 10 | 0.23 | 0.33 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | — | — | — | 72% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | — | — | — | 56% | — | — |

## Zorunlu mod: `no_tool` kullanımı

Zorunlu modda çağrı gerekmeyen tur `<tool> no_tool` yazarak kapanır, yani **iki sütun eşit olmalı**: gramer başka bir çıkış yolu bırakmıyor. Eşit değilse aradaki fark, düzeltme tavanına kadar geçerli bir çağrı üretilemeyen turlardır — tek bir doğruluk yüzdesinde bu iki başarısızlık aynı görünür.

| koşu | mod | `no_tool` | çağrı üretilmeyen tur |
|---|---|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | serbest | 0 | 17 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | zorunlu | 13 | 13 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | serbest | 0 | 17 |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | zorunlu | 10 | 10 |

## İlk ses gecikmesi: zorunlu modun bedeli

`ort. TTFT` **birinci** üretimin ilk token'ını ölçüyor. Zorunlu modda o token `<tool> no_tool`'un ilk harfidir ve kullanıcı onu duymaz: metin, birinci üretim bittikten sonra başlayan ikinci üretimden gelir. `ilk ses`, turun başından kullanıcının duyduğu ilk token'a kadar geçen süredir — serbest modda birinci üretimin TTFT'si (ikinci üretim yok), zorunlu modda birinci üretimin tamamı artı kapanışın TTFT'si.

**Payda çağrı üretilmeyen turlar** (parantezde). Çağrı üretilen turda ilk ses zaten tool'un çalışmasını bekliyor; onları da katmak, ölçülen farkı tool süreleriyle seyreltirdi. §6'nın bütçesi bu sütun, §19.4 hâlâ açık olduğu için burada bir geçti/kaldı yok — iki mod arasındaki **fark** var.

| koşu | mod | ort. TTFT | ort. ilk ses (n) |
|---|---|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | serbest | 0.28 | 0.28 (17) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol | zorunlu | 0.24 | 0.35 (13) |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | serbest | 0.22 | 0.22 (17) |
| Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol | zorunlu | 0.23 | 0.36 (10) |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × zorunlu × kontrol — 5/18

- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`
- `kon-18` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × zorunlu × kontrol — 8/18

- `kon-05` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-16` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-18` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
