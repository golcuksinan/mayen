> ## ⚠ BU MODEL BU SÖZLEŞMEYLE ÖLÇÜLEMİYOR — SAYILAR MODELİN BAŞARISI DEĞİL
>
> LFM2.5'in sohbet şablonu, üretimin başına **koşulsuz** bir düşünce açıcısı koyuyor.
> `/apply-template` bunu gösteriyor:
>
> ```
> <|im_start|>assistant\n<think>
> ```
>
> `<think>` üretilen bir token değil, **prompt'un parçası**; şablonda onu kapatan bir
> anahtar da yok. `--reasoning-format none` ile sunucu bu öneki `content`'e de yazıyor.
>
> Sonuç, iki modda iki farklı yoldan aynı yere çıkıyor:
>
> - **Serbest modda** gramerin düz metin dalı serbest; model ortalama 173 token düşünüyor
>   ve hiçbir zaman çağrıya geçmiyor.
> - **Zorunlu modda** gramer `<tool> …` üretiyor ama metnin tamamı `<think><tool> date_time`
>   oluyor ve `is_call()` öneki **0. konumda** aradığı için bunu düz metin sayıyor.
>
> Her satırdaki `argüman doğruluğu —` bunun kanıtı: **tek bir çağrı bile ayrıştırılmadı.**
> %30'lar modelin becerisi değil, çağrı beklenmeyen senaryoların oranı (15/50); kontrol
> kümesindeki %100 de öyle — orada doğru cevap zaten "çağrı yok".
>
> **Model doğru akıl yürütüyor.** Çıktılar okunabilir: "I need to use the `date_time` tool".
> Uyuşmayan şey model değil, §6'nın "dal ilk token'da belli olmalı" sözleşmesiyle koşulsuz
> düşünce bloğu.
>
> Dosya silinmedi: hatanın kendisi kayıt (Kural 13, Kural 14).

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
| LFM2.5-2.6B-Q8_0 × cli | 50 | 30% [19%–44%] | — | — | 0 | 0 | 0 (0) | 0 | 173 | 0.04 | 0.81 |
| LFM2.5-2.6B-Q8_0 × cli × kontrol | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 238 | 0.03 | 1.09 |
| LFM2.5-2.6B-Q8_0 × cli × adim2 | 8 | 0% [0%–32%] | — | — | 0 | 0 | 0 (0) | 0 | 105 | 0.03 | 0.50 |
| LFM2.5-2.6B-Q8_0 × cli × saglamlik | 10 | 10% [2%–40%] | — | — | 0 | 0 | 0 (0) | 0 | 181 | 0.03 | 0.84 |
| LFM2.5-2.6B-Q8_0 × cli × uzun | 4 | 0% [0%–49%] | — | — | 0 | 0 | 0 (0) | 0 | 98 | 0.03 | 0.47 |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izli) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 169 | 0.04 | 0.79 |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izsiz) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 161 | 0.03 | 0.75 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu | 50 | 30% [19%–44%] | — | — | 0 | 0 | 0 (0) | 0 | 148 | 0.04 | 0.78 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × kontrol | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 164 | 0.04 | 0.86 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × adim2 | 8 | 0% [0%–32%] | — | — | 0 | 0 | 0 (0) | 0 | 91 | 0.04 | 0.51 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × saglamlik | 10 | 10% [2%–40%] | — | — | 0 | 0 | 0 (0) | 0 | 137 | 0.04 | 0.73 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × uzun | 4 | 0% [0%–49%] | — | — | 0 | 0 | 0 (0) | 0 | 72 | 0.04 | 0.40 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izli) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 187 | 0.04 | 0.95 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izsiz) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 192 | 0.04 | 0.97 |
| LFM2.5-2.6B-Q8_0 × json | 50 | 30% [19%–44%] | — | — | 0 | 0 | 0 (0) | 0 | 174 | 0.03 | 0.81 |
| LFM2.5-2.6B-Q8_0 × json × kontrol | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 251 | 0.03 | 1.15 |
| LFM2.5-2.6B-Q8_0 × json × adim2 | 8 | 0% [0%–32%] | — | — | 0 | 0 | 0 (0) | 0 | 139 | 0.03 | 0.65 |
| LFM2.5-2.6B-Q8_0 × json × saglamlik | 10 | 10% [2%–40%] | — | — | 0 | 0 | 0 (0) | 0 | 196 | 0.03 | 0.90 |
| LFM2.5-2.6B-Q8_0 × json × uzun | 4 | 0% [0%–49%] | — | — | 0 | 0 | 0 (0) | 0 | 108 | 0.03 | 0.51 |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izli) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 180 | 0.04 | 0.84 |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izsiz) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 166 | 0.03 | 0.77 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu | 50 | 30% [19%–44%] | — | — | 0 | 0 | 0 (0) | 0 | 18 | 0.04 | 0.14 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × kontrol | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 19 | 0.04 | 0.15 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × adim2 | 8 | 0% [0%–32%] | — | — | 0 | 0 | 0 (0) | 0 | 18 | 0.04 | 0.14 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × saglamlik | 10 | 10% [2%–40%] | — | — | 0 | 0 | 0 (0) | 0 | 21 | 0.04 | 0.16 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × uzun | 4 | 0% [0%–49%] | — | — | 0 | 0 | 0 (0) | 0 | 16 | 0.04 | 0.13 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izli) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 21 | 0.04 | 0.16 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izsiz) | 10 | 20% [6%–51%] | — | — | 0 | 0 | 0 (0) | 0 | 21 | 0.04 | 0.15 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli | 0% | 0% | 100% | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × kontrol | — | — | — | 100% | — | — |
| LFM2.5-2.6B-Q8_0 × cli × adim2 | 0% | 0% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 × cli × saglamlik | 0% | — | 100% | — | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × uzun | 0% | — | — | — | — | 0% |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izli) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izsiz) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu | 0% | 0% | 100% | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × kontrol | — | — | — | 100% | — | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × adim2 | 0% | 0% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × saglamlik | 0% | — | 100% | — | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × uzun | 0% | — | — | — | — | 0% |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izli) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izsiz) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json | 0% | 0% | 100% | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × kontrol | — | — | — | 100% | — | — |
| LFM2.5-2.6B-Q8_0 × json × adim2 | 0% | 0% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 × json × saglamlik | 0% | — | 100% | — | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × uzun | 0% | — | — | — | — | 0% |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izli) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izsiz) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × zorunlu | 0% | 0% | 100% | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × kontrol | — | — | — | 100% | — | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × adim2 | 0% | 0% | — | — | 0% | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × saglamlik | 0% | — | 100% | — | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × uzun | 0% | — | — | — | — | 0% |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izli) | 0% | — | — | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izsiz) | 0% | — | — | 100% | 0% | 0% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli | 30% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × kontrol | 100% (18) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × adim2 | 0% (8) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × saglamlik | 10% (10) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × uzun | 0% (4) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izli) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izsiz) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu | 30% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × kontrol | 100% (18) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × adim2 | 0% (8) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × saglamlik | 10% (10) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × uzun | 0% (4) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izli) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izsiz) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × json | 30% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × json × kontrol | 100% (18) | — | — |
| LFM2.5-2.6B-Q8_0 × json × adim2 | 0% (8) | — | — |
| LFM2.5-2.6B-Q8_0 × json × saglamlik | 10% (10) | — | — |
| LFM2.5-2.6B-Q8_0 × json × uzun | 0% (4) | — | — |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izli) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izsiz) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × json × zorunlu | 30% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × kontrol | 100% (18) | — | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × adim2 | 0% (8) | — | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × saglamlik | 10% (10) | — | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × uzun | 0% (4) | — | — |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izli) | — | 20% (5) | 20% (5) |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izsiz) | — | 20% (5) | 20% (5) |

## Zorunlu mod: `no_tool` kullanımı

Zorunlu modda çağrı gerekmeyen tur `<tool> no_tool` yazarak kapanır, yani **iki sütun eşit olmalı**: gramer başka bir çıkış yolu bırakmıyor. Eşit değilse aradaki fark, düzeltme tavanına kadar geçerli bir çağrı üretilemeyen turlardır — tek bir doğruluk yüzdesinde bu iki başarısızlık aynı görünür.

| koşu | mod | `no_tool` | çağrı üretilmeyen tur |
|---|---|---:|---:|
| LFM2.5-2.6B-Q8_0 × cli | serbest | 0 | 50 |
| LFM2.5-2.6B-Q8_0 × cli × kontrol | serbest | 0 | 18 |
| LFM2.5-2.6B-Q8_0 × cli × adim2 | serbest | 0 | 8 |
| LFM2.5-2.6B-Q8_0 × cli × saglamlik | serbest | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × cli × uzun | serbest | 0 | 4 |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izli) | serbest | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × cli × geçmiş(izsiz) | serbest | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu | zorunlu | 0 | 50 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × kontrol | zorunlu | 0 | 18 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × adim2 | zorunlu | 0 | 8 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × saglamlik | zorunlu | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × uzun | zorunlu | 0 | 4 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izli) | zorunlu | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izsiz) | zorunlu | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × json | serbest | 0 | 50 |
| LFM2.5-2.6B-Q8_0 × json × kontrol | serbest | 0 | 18 |
| LFM2.5-2.6B-Q8_0 × json × adim2 | serbest | 0 | 8 |
| LFM2.5-2.6B-Q8_0 × json × saglamlik | serbest | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × json × uzun | serbest | 0 | 4 |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izli) | serbest | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × json × geçmiş(izsiz) | serbest | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu | zorunlu | 0 | 50 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × kontrol | zorunlu | 0 | 18 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × adim2 | zorunlu | 0 | 8 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × saglamlik | zorunlu | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × uzun | zorunlu | 0 | 4 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izli) | zorunlu | 0 | 10 |
| LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izsiz) | zorunlu | 0 | 10 |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Başarısız senaryolar

### LFM2.5-2.6B-Q8_0 × cli — 35/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking for the current time. I need to use the `date_time` tool which provides the current date and t`
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if Veli's phone number is registered. I need to check the contact information for "Veli" using`
- `tek-03` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Denizli. I need to use the `weather` tool with the city parameter set to `
- `tek-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to get the current weather in Istanbul and only provide the temperature (not the full weather c`
- `tek-05` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the computer's memory status. I need to use the "system_metrics" tool which provides CPU`
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about disk space remaining. I need to use the `system_metrics` tool which provides CPU, memory`
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to wake up their desktop computer. Looking at the available tools, I have `wake_on_lan` which send`
- `tek-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking for Ali's number. I need to look up contact information for "Ali" using the contact_get tool. `
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking "Who are the people in the guide?" which translates to "Kimler var?" (Who are there?). They wa`
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to list their pending tasks (hatırlatıcılar). I should use the `task_list` tool which lists sch`
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to see the course schedule for this week. I need to use the `course_schedule` tool with the day pa`
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if they have a class on Tuesday. I need to check the course schedule for Tuesday (which would `
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete the 3rd note from their list. I need to use the `note_delete` tool with the id parameter`
- `tek-14` (tek tool): task_cancel beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to cancel the 7th task (hatırlatıcı). I need to use the `task_cancel` tool with the id parameter s`
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking two questions:`
- `cok-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to cancel the second task (numara 2) from their pending tasks. I need to use the `task_cancel` `
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user wants two things:`
- `cok-05` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to check the machine's status and then save a note with the result. Let me first use the system`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to find a shopping note (alışveriş notu). I should use the `note_search` tool with a query for `
- `ayr-02` (ayırt etme): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to create a note with the content "alışveriş" (shopping). I need to use the `note_create` tool for`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to save a contact named "Ayşe" with the tool `contact_save`. The parameter is --name which should `
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if Ayşe is in the guidebook/reference. I need to use the contact_get tool to search for this p`
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to see their reminders/hatırlatıcıları (reminders). I should use the `task_list` tool to get the l`
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to remind them about a meeting tomorrow morning at 9 AM (which would be on 2026-08-10, since to`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete Ali from the directory. I need to use the `contact_delete` tool with --name "Ali". Let m`
- `ayr-08` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete the 5th note from their notes list. I need to use the `note_delete` tool with the id par`
- `ser-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "süt, ekmek ve yumurta almayı unutma" (don't forget to buy mi`
- `ser-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "yarın erken kalk" (wake up early tomorrow). I need to use th`
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to send a message to "Ali" (Ali'ye akşam mesaj at). They also mentioned that if the response do`
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about notes related to "kütüphane kitabı" (library book). I need to search through the notes t`
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to remind them about their mother's birthday and to congratulate her on her birthday. I need to`
- `ser-06` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "kütüphane kitabını ayın on beşine kadar geri ver" (return li`
- `ser-07` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to search their notes for something related to "elektrik faturası" (electricity bill). I should us`

### LFM2.5-2.6B-Q8_0 × cli × kontrol — 0/18

Yok.

### LFM2.5-2.6B-Q8_0 × cli × adim2 — 8/8

- `adm-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-04` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-05` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to check if Ayşe is in the guide (rehber) and add her if she's not there. I need to use the contac`
- `adm-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to remind them about a meeting tomorrow morning at 9 AM (yesterday's context says "2026-08-09T0`
- `adm-07` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Bursa. I need to use the `weather` tool with the city parameter set to "B`
- `adm-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to find Zeynep's number. I need to use the contact_get tool to list contacts and find Zeynep. L`

### LFM2.5-2.6B-Q8_0 × cli × saglamlik — 9/10

- `sag-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to write a single line command using the available tools. They provided some context about curr`
- `sag-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to check the weather and if the temperature is below 20°C, they want a "montu" (mountain) alert`
- `sag-03` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to check the system metrics. I should use the `system_metrics` tool which provides CPU, memory,`
- `sag-04` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to delete note with ID 3. I need to use the `note_delete` tool with --id parameter set to 3.`
- `sag-05` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete the seventh note (numaralı notu sil). I need to use the `note_delete` tool with --id 7.`
- `sag-06` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to delete the 5th note (not number 5) from their system. I need to use the `note_delete` tool w`
- `sag-07` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a tool call for something related to their note about "acele etme" (speed up). Let me`
- `sag-08` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with specific content. Looking at the available tools, I can use `note_create``
- `sag-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to know the current weather in Istanbul, specifically temperature and humidity (nem). I need to us`

### LFM2.5-2.6B-Q8_0 × cli × uzun — 4/4

- `uzn-01` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking how many pending tasks (hatırlatıcılar) they have. I need to use the `task_list` tool to see t`
- `uzn-02` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if there are any notes containing "fatura" (invoice). I need to search through the notes using`
- `uzn-03` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking how many people are registered in the guide (rehber). I need to use the contact_get tool to li`
- `uzn-04` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking how many classes there are on Wednesday (çarşamba). I need to use the course_schedule tool wit`

### LFM2.5-2.6B-Q8_0 × cli × geçmiş(izli) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Denizli. I need to use the `weather` tool with the city parameter set to `
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in İzmir as well. I need to call the weather tool for both Denizli and İzmir`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to set a reminder for "on dakika sonra su içmemi hatırlat" (remind me to drink water in a few m`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking "Kurdun mu gerçekten?" which means "Are you Kurdish really?" in Turkish. This is a question ab`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to count how many pending reminders (hatırlatıcılar) I have. Let me check the task_list tool to`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking what the note I just created contains. They want to know the exact content of the note that wa`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking me to check the weather in Denizli again. They want to know the current weather conditions the`

### LFM2.5-2.6B-Q8_0 × cli × geçmiş(izsiz) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Denizli. I need to use the `weather` tool with the city parameter set to `
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Izmir as well, since they mentioned "İzmir'e bak" (look at Izmir). They w`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to set a reminder for "on dakika sonra su içmemi hatırlat" (remind me to drink water in a few m`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking "Kurdun mu gerçekten?" which means "Are you Kurdish really?" in Turkish. This is a question ab`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to count how many pending reminders (hatırlatıcılar) I have. Let me check the task_list tool to`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking what the note I just created contains. They want to know the exact content of the note that wa`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking me to check the weather in Denizli again. They want to know the current weather conditions the`

### LFM2.5-2.6B-Q8_0 × cli × zorunlu — 35/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think><tool> date_time`
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Veli" etki: OKUMA -Bu işlem, Veli adlı kişiyi rehberden bulur ve telefonunu gösterir. `
- `tek-03` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ - Bu tool hava durumunu verir. Kullan`
- `tek-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "Istanbul" --fields "temperature" etki: DIŞ. The user wants only the temperature in Istanbu`
- `tek-05` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `<think><tool> wake_on_lan --target "masaüstü bilgisayarı" etki: GERİ_ALINAMAZ (onay ister) -用户要求让桌面电脑醒来，但工具的参数是 target（目`
- `tek-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Ali" etki: OKUMA -阿里 (Ali) is a common name. I need to search for contacts named Ali t`
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Rehber" etki: OKUMA -用户想知道导游在哪里，但提示中并没有明确列出任何具体的“导游”名字。不过，contact_get 工具可以列出所有可用的个人。如果`
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "" etki: OKUMA - This will search for notes without a specific query, which should ret`
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> course_schedule --day 1`
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> course_schedule --day 2`
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_delete --id 3`
- `tek-14` (tek tool): task_cancel beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_cancel --id 7`
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Ali" etki: OKUMA -Bu adın bulacağım. Sonra not_create ile akşam ararım diye bir not ol`
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "Ankara hava durumu" etki: YAZMA - Bu tool not oluşturur. Ancak kullanıcı saat ve hava `
- `cok-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_cancel --id 2`
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "Bir yeni not oluşturulacak" --etki YAZMA > Not created. Now I need to get the weather `
- `cok-05` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Veli'ye" | etki: OKUMA > | Then I need to add Veli'ye to contacts using contact_save w`
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "alışveriş" etki: OKUMA - Notları arama yapacağım. Kullanıcı "alışveriş notumu" arıyor`
- `ayr-02` (ayırt etme): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "Alışveriş" etki: YAZMA. Kullanıcı "Alışveriş" diye bir not oluşturmamı istiyor. Not ol`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_save --name Ayşe | etki: YAZMA (Tool call to save a person named Ayşe in the directory) -This is s`
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Ayşe" etki: OKUMA -veya contact_get'ı kullanarak rehberden Ayşe hakkında bilgi alabili`
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "hatıralar" etki: OKUMA - Notları arama yaparak hatıra listesini gösterir. Kullanıcı "`
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_list`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_delete --name Ali | etki: GERİ_ALINAMAZ (onay ister) -用户要求删除名为"Ali"的个人。根据工具描述，contact_delete 需要--n`
- `ayr-08` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_delete --id 5`
- `ser-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "süt, ekmek ve yumurta almayı unutma" etki: YAZMA -> Notu oluşturuyor. Sonra user'a yan`
- `ser-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "yarın erken kalk" etki: YAZMA - Bu komut not oluşturmak için kullanılır. Notun metni "`
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "Ali'ye akşam mesaj at" etki: YAZMA -> Notu oluşturuyor. Sonra notun numarasını bulup s`
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "kütüphane kitabı" etki: OKUMA - Arama metni verildiği için içeriği döndürür. Notlar i`
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "annem" --etki OKUMA > response_tool_1 (I need to search for notes about "annem" first`
- `ser-06` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "Kütüphane kitabını ayın on beşine kadar geri ver." etki: YAZMA -> Not oluşturma işlemi`
- `ser-07` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "elektrik fatura" etki: OKUMA - Notlarıma elektrik faturası hakkında bilgi arıyorum. B`

### LFM2.5-2.6B-Q8_0 × cli × zorunlu × kontrol — 0/18

Yok.

### LFM2.5-2.6B-Q8_0 × cli × zorunlu × adim2 — 8/8

- `adm-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Veli" etki: OKUMA -Bu adın bulacağım. Sonra not_create ile akşam ararım diye bir not y`
- `adm-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think><tool> date_time`
- `adm-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_cancel --id 1`
- `adm-04` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `adm-05` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Ayşe" etki: OKUMA -veya contact_save eğer bulunamazsa. Önce contact_get ile kontrol et`
- `adm-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_list`
- `adm-07` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "Bursa" --fields "temperature, condition" etki: DIŞ. Kullanıcı Bursa'daki hava durumunu sor`
- `adm-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "Zeynep" etki: OKUMA -Bu işlem Zeynep adlı kişiyi arar ve listeler. Sonraki adımda sonu`

### LFM2.5-2.6B-Q8_0 × cli × zorunlu × saglamlik — 9/10

- `sag-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "bugün" etki: OKUMA - Notları arama yapmaya çalışıyorum. Kullanıcı "bugün" kelimesini `
- `sag-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "sıcaklık" etki: OKUMA - Bu, notları ararken sıcaklık ile ilgili olanları bulmak için `
- `sag-03` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `sag-04` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_delete --id 3`
- `sag-05` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_delete --id 7`
- `sag-06` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_delete --id 5`
- `sag-07` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "acele etme" --başka_alan "not" | Wait, the format requires: first line is tool tag, th`
- `sag-08` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazı`
- `sag-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "Istanbul" --fields "temperature, condition" etki: DIŞ (OKUMA) - Bu tool hava durumunu veri`

### LFM2.5-2.6B-Q8_0 × cli × zorunlu × uzun — 4/4

- `uzn-01` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `uzn-02` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_search --query "fatura" etki: OKUMA - Notlarımdan fatura ile ilgili notlar ararken, "fatura" kelimesi`
- `uzn-03` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> contact_get --name "all" | etki: OKUMA -Bu komut rehberdeki kişileri listeler. Eğer "all" adını verirse, t`
- `uzn-04` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> course_schedule --day 3`

### LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izli) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ (OKUMA) - Hava durumu için weather to`
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "İzmir" --fields temperature, condition | etki: DIŞ (veya okuma) - The user wants to know t`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_create --due "2026-08-09T10:01:00Z" --message "Su içme" etki: YAZMA", on dakika sonra hatırlatmak içi`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu, notu oluşturur. Kullanıcıya yanıt vermeliyim. Sonra`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu komut, yeni bir not oluşturur. Notun adı yok, sadece`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu komut, yeni bir not oluşturur. Kullanıcı "not al: ki`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu işlem yapıldı. Şimdi kullanıcı hava durumunu tekrar `

### LFM2.5-2.6B-Q8_0 × cli × zorunlu × geçmiş(izsiz) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "Denizli" --fields "temperature, condition" etki: DIŞ (OKUMA) - Hava durumu için weather to`
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> weather --city "İzmir" --fields temperature, condition | etki: DIŞ (veya sadece hava durumu için yeterli) `
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> task_create --due "2026-08-09T10:01:00Z" --message "Su içme" etki: YAZMA", on dakika sonra hatırlatmak içi`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> system_metrics`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu komut not oluşturur. Kullanıcıya yanıt vermeliyim. S`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu komut not oluşturur. Şimdi notu oluşturduğumda, bekl`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu komut, yeni bir not oluşturur. Kullanıcı "not al: ki`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> note_create --body "kitabı geri ver" etki: YAZMA - Bu işlem yapıldı. Şimdi kullanıcı hava durumunu tekrar `

### LFM2.5-2.6B-Q8_0 × json — 35/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking for the current time. I need to use the `date_time` tool which provides the current date and t`
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if Veli's phone number is registered. I need to check the contacts list first to see if there'`
- `tek-03` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Denizli. I need to use the `weather` tool with the city parameter set to `
- `tek-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to get the current weather in Istanbul and only provide the temperature (not the full weather c`
- `tek-05` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the computer's memory status. I need to use the "system_metrics" tool which provides CPU`
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about disk space remaining. I need to use the `system_metrics` tool which provides CPU, memory`
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to wake up their desktop computer. Looking at the available tools, I can see there's a `wake_on_la`
- `tek-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking for Ali's number. I need to look up contact information for "Ali" from the contacts list. Let `
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking "Rehberimde kimler var?" which means "Who are the people in your guide/book?" They want to kno`
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to list their pending tasks/reminders. I should use the `task_list` tool to get this informatio`
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to see the course schedule for this week. I need to use the `course_schedule` tool with a day para`
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if they have a class on Tuesday. The current date is 2026-08-09 (which appears to be a Monday `
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete the 3rd note from their list. I need to use the `note_delete` tool with the id parameter`
- `tek-14` (tek tool): task_cancel beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to cancel the 7th task (hatırlatıcı). I need to use the `task_cancel` tool with id 7. Let me check`
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking two questions:`
- `cok-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `cok-05` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to check the machine's status and save a note with the result. I need to:`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to find a shopping note (alışveriş notu). I need to search for notes that contain "alışveriş" o`
- `ayr-02` (ayırt etme): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "alışveriş" (shopping). I need to use the `note_create` tool `
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to save a contact named "Ayşe" with the tool `contact_save`. The parameter is --name which should `
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if Ayşe is in the guidebook/reference. I need to check the contacts list using the contact_get`
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to see their reminders/hatırlatıcıları (reminders). I need to use the `task_list` tool to list pen`
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to remind them about a meeting tomorrow morning at 9 AM (which would be on 2026-08-10, since to`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete Ali from the directory. I need to use the `contact_delete` tool with the name "Ali". Let`
- `ayr-08` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete the 5th note from their notes list. I need to use the `note_delete` tool with the id par`
- `ser-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "süt, ekmek ve yumurta almayı unutma" (don't forget to buy mi`
- `ser-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "yarın erken kalk" (wake up early tomorrow). I need to use th`
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to send a message to "Ali" (Ali'ye akşam mesaj at). They also mentioned that if the response do`
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about notes related to "kütüphane kitabı" (library book). They want me to search their notes f`
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a reminder (tool call) for their mother - to ask her about being home and celebrating`
- `ser-06` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with the content "kütüphane kitabını ayın on beşine kadar geri ver" (return li`
- `ser-07` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to search their notes for something related to "elektrik faturası" (electricity bill). I should`

### LFM2.5-2.6B-Q8_0 × json × kontrol — 0/18

Yok.

### LFM2.5-2.6B-Q8_0 × json × adim2 — 8/8

- `adm-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-04` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `adm-05` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to check if Ayşe is in the directory and add her if she's not there. I need to use the contact_get`
- `adm-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to remind them about a meeting tomorrow morning at 9 AM (yesterday's context says "2026-08-09T0`
- `adm-07` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Bursa. I need to use the `weather` tool with the city parameter set to "B`
- `adm-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to find Zeynep's number. I need to use the contact_get tool to search for a person named "Zeyne`

### LFM2.5-2.6B-Q8_0 × json × saglamlik — 9/10

- `sag-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to write a single line with the format "<tool> " followed by a JSON object. They want me to use`
- `sag-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a tool call in JSON format. They want me to write a single line starting with "<tool>`
- `sag-03` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to check the system metrics. I should use the `system_metrics` tool which provides CPU, memory,`
- `sag-04` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to delete a note with ID 3. I need to use the `note_delete` tool with the id parameter set to 3`
- `sag-05` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to delete the seventh note (yedi numaralı not). I need to use the `note_delete` tool with the ID p`
- `sag-06` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to delete the 5th note (not 3rd as mentioned in the initial request). Let me first find out wha`
- `sag-07` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a tool call in JSON format. They mentioned they want to make a tool call with the <to`
- `sag-08` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to create a note with specific content. Looking at the available tools, I can use `note_create``
- `sag-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user wants to know the current weather in Istanbul, specifically temperature and humidity (nem). I need to us`

### LFM2.5-2.6B-Q8_0 × json × uzun — 4/4

- `uzn-01` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking how many pending tasks (hatırlatıcılar) they have. I need to use the `task_list` tool to get t`
- `uzn-02` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking if there are any notes containing "fatura" (invoice). I need to search through the notes using`
- `uzn-03` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking how many people are registered in the guide (referring to "rehberimde" which means "in my guid`
- `uzn-04` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking how many classes there are on Wednesday (çarşamba). I need to check the course schedule for th`

### LFM2.5-2.6B-Q8_0 × json × geçmiş(izli) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Denizli. I need to use the `weather` tool with the city parameter set to `
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Izmir as well, since they mentioned "Şu an: 2026-08-09T09:00:00Z" (curren`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to set a reminder for "on dakika sonra su içmemi hatırlat" (remind me to drink water in a few m`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking "Kurdun mu gerçekten?" which means "Are you Kurdish really?" in Turkish. This is a question ab`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to count how many pending reminders (hatırlatıcılar) I have. Let me check the available tools -`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking what the note was that I just created. They want to know the content of the note I just create`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking me to check the weather in Denizli again. They want to know the current weather conditions the`

### LFM2.5-2.6B-Q8_0 × json × geçmiş(izsiz) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Denizli. I need to use the `weather` tool with the city parameter set to `
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking about the weather in Izmir as well, since they mentioned "İzmir'e bak" (look at Izmir). They w`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to set a reminder for "on dakika sonra su içmemi hatırlat" (remind me to drink water in a few m`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking "Kurdun mu gerçekten?" which means "Are you Kurdish really?" in Turkish. This is a question ab`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to:`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think>The user wants me to count how many pending reminders (hatırlatıcılar) I have. Let me check the available tools -`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking what the note was that I just created. They want to know the content of the note I just create`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think>The user is asking me to check the weather in Denizli again. They want to know the current weather conditions the`

### LFM2.5-2.6B-Q8_0 × json × zorunlu — 35/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "date_time", "arguments": {}}`
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Veli"}}`
- `tek-03` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `tek-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `tek-05` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "system_metrics", "arguments": {}}`
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "system_metrics", "arguments": {}}`
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayarı"}}`
- `tek-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": ""}}`
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "course_schedule", "arguments": {"day": 1}}`
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "course_schedule", "arguments": {"day": 2}}`
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `tek-14` (tek tool): task_cancel beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `cok-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `cok-05` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "system_metrics", "arguments": {}}`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Veli"}}`
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_search", "arguments": {"query": "alışveriş notu"}}`
- `ayr-02` (ayırt etme): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_create", "arguments": {"body": "Alışveriş"}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_list", "arguments": {}}`
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_list", "arguments": {}}`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `ayr-08` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `ser-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_create", "arguments": {"body": "süt, ekmek ve yumurta almayı unutma"}}`
- `ser-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_create", "arguments": {"body": "yarın erken kalk"}}`
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_create", "arguments": {"body": "Ali'ye akşam mesaj at"}}`
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_search", "arguments": {"query": "kütüphane kitabı"}}`
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "system_metrics", "arguments": {}}`
- `ser-06` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `ser-07` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_search", "arguments": {"query": "elektrik faturası"}}`

### LFM2.5-2.6B-Q8_0 × json × zorunlu × kontrol — 0/18

Yok.

### LFM2.5-2.6B-Q8_0 × json × zorunlu × adim2 — 8/8

- `adm-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Veli"}}`
- `adm-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "date_time", "arguments": {}}`
- `adm-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `adm-04` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "system_metrics", "arguments": {}}`
- `adm-05` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`
- `adm-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_list", "arguments": {}}`
- `adm-07` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Bursa"}}`
- `adm-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": "Zeynep"}}`

### LFM2.5-2.6B-Q8_0 × json × zorunlu × saglamlik — 9/10

- `sag-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_search", "arguments": {"query": "bugün"}}`
- `sag-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `sag-03` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "system_metrics", "arguments": {}}`
- `sag-04` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `sag-05` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `sag-06` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_delete", "arguments": {"id": 5}}`
- `sag-07` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_delete", "arguments": {"id": 1}}`
- `sag-08` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "note_create", "arguments": {"body": "sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada e`
- `sag-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`

### LFM2.5-2.6B-Q8_0 × json × zorunlu × uzun — 4/4

- `uzn-01` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_list", "arguments": {}}`
- `uzn-02` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `uzn-03` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "contact_get", "arguments": {"name": ""}}`
- `uzn-04` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "course_schedule", "arguments": {"day": 3}}`

### LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izli) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "İzmir"}}`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_create", "arguments": {"due": "2026-08-09T10:01:00Z", "message": "Su içmemi hatırlat"}}`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "date_time", "arguments": {}}`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_create", "arguments": {"due": "2026-08-09T10:00:00Z", "message": "Su içme"}}`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_list", "arguments": {}}`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`

### LFM2.5-2.6B-Q8_0 × json × zorunlu × geçmiş(izsiz) — 8/10

- `gec-01` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `gec-02` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
- `gec-03` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_create", "arguments": {"due": "2026-08-09T10:01:00Z", "message": "Su içmemi hatırlat"}}`
- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "date_time", "arguments": {}}`
- `gec-06` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_create", "arguments": {"due": "2026-08-09T10:00:00Z", "message": "Su içme"}}`
- `gec-07` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "task_list", "arguments": {}}`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `<think><tool> no_tool`
- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `<think><tool> {"name": "weather", "arguments": {"city": "Denizli"}}`
