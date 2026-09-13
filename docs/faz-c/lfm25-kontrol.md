# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/LFM2.5-2.6B-Q8_0.gguf` (Q8_0)
- `n_ctx`: 16384

| örnekleme | sunucu (`/props`) | istek (adaptör) |
|---|---:|---:|
| `dry_multiplier` | 0.0 | 0.0 |
| `frequency_penalty` | 0.0 | 0.0 |
| `min_p` | 0.05000000074505806 | 0.05000000074505806 |
| `mirostat` | 0 | 0 |
| `presence_penalty` | 0.0 | 0.0 |
| `repeat_penalty` | 1.100000023841858 | 1.100000023841858 |
| `temperature` | 0.009999999776482582 | 0.009999999776482582 |
| `top_k` | 50 | 50 |
| `top_n_sigma` | -1.0 | -1.0 |
| `top_p` | 0.949999988079071 | 0.949999988079071 |
| `typical_p` | 1.0 | 1.0 |
| `xtc_probability` | 0.0 | 0.0 |

Sağ sütun her istekte gönderiliyor ve solu **ezer**; `←` işaretli satırlar sunucunun bayrağının artık okunmadığı yerler. Sunucudan gelen tek şey `n_ctx`.


## Önek

Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi** olduğu sonucu değiştirir (P27):

- **ölçüm öneği** — `docs/faz2-olcum.md`'den beri kullanılan dizi: çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]` bloğu ve olgular **yok**.
- **üretim öneği** — `turn/runner.py`'nin modele gerçekten gönderdiği dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.

Rol metni: `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LFM2.5-2.6B-Q8_0 × cli × kontrol × üretim öneği | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.09 |
| LFM2.5-2.6B-Q8_0 × json × kontrol × üretim öneği | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.16 |
| LFM2.5-2.6B-Q8_0 × yerel × kontrol × üretim öneği | 18 | 72% [49%–88%] | — | — | 0 | 1 | 0 (0) | 0 | 0 | 8 | 0.40 | 0.91 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli × kontrol × üretim öneği | — | — | — | 100% | — | — |
| LFM2.5-2.6B-Q8_0 × json × kontrol × üretim öneği | — | — | — | 100% | — | — |
| LFM2.5-2.6B-Q8_0 × yerel × kontrol × üretim öneği | — | — | — | 72% | — | — |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**LFM2.5-2.6B-Q8_0 × cli × kontrol × üretim öneği** — 18 yanıt:

- `kon-01`: ``
- `kon-02`: ``
- `kon-03`: ``
- `kon-04`: ``
- `kon-05`: ``
- `kon-06`: ``
- `kon-07`: ``
- `kon-08`: ``
- `kon-09`: ``
- `kon-10`: ``
- `kon-11`: ``
- `kon-12`: ``
- `kon-13`: ``
- `kon-14`: ``
- `kon-15`: ``
- `kon-16`: ``
- `kon-17`: ``
- `kon-18`: ``

**LFM2.5-2.6B-Q8_0 × json × kontrol × üretim öneği** — 18 yanıt:

- `kon-01`: ``
- `kon-02`: ``
- `kon-03`: ``
- `kon-04`: ``
- `kon-05`: ``
- `kon-06`: ``
- `kon-07`: ``
- `kon-08`: ``
- `kon-09`: ``
- `kon-10`: ``
- `kon-11`: ``
- `kon-12`: ``
- `kon-13`: ``
- `kon-14`: ``
- `kon-15`: ``
- `kon-16`: ``
- `kon-17`: ``
- `kon-18`: ``

**LFM2.5-2.6B-Q8_0 × yerel × kontrol × üretim öneği** — 13 yanıt:

- `kon-01`: `Good evening. How can I assist you today?`
- `kon-02`: `Understood. I'm ready to assist you. What would you like to do?`
- `kon-03`: ``
- `kon-04`: `Understood. How can I help you today?`
- `kon-05`: ``
- `kon-06`: `Computers are electronic devices that process data according to instructions stored in programs. Here's how they work:  **Core Components:** - **CPU (Central Processing Unit)** - Executes instructions`
- `kon-09`: ``
- `kon-10`: ``
- `kon-11`: ``
- `kon-12`: ``
- `kon-14`: `Understood. I'll wait for any further instructions if needed. Have a good day!`
- `kon-15`: ``
- `kon-17`: ``

## Başarısız senaryolar

### LFM2.5-2.6B-Q8_0 × cli × kontrol × üretim öneği — 0/18

Yok.

### LFM2.5-2.6B-Q8_0 × json × kontrol × üretim öneği — 0/18

Yok.

### LFM2.5-2.6B-Q8_0 × yerel × kontrol × üretim öneği — 5/18

- `kon-07` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: ``
- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: ``
- `kon-13` (tool gerekmez): düz metin beklenirken task_list çağrıldı — çıktı: ``
- `kon-16` (tool gerekmez): fazladan çağrı: contact_get; düz metin beklenirken note_search çağrıldı — çıktı: ``
- `kon-18` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: ``
