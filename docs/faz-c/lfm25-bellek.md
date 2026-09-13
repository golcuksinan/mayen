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
| LFM2.5-2.6B-Q8_0 × cli × bellek × üretim öneği | 17 | 47% [26%–69%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.12 |
| LFM2.5-2.6B-Q8_0 × json × bellek × üretim öneği | 17 | 47% [26%–69%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.14 |
| LFM2.5-2.6B-Q8_0 × yerel × bellek × üretim öneği | 17 | 65% [41%–83%] | 67% | — | 0 | 0 | 0 (6) | 0 | 0 | 1 | 0.53 | 0.76 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli × bellek × üretim öneği | 0% | — | — | 100% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 × json × bellek × üretim öneği | 0% | — | — | 100% | 100% | 0% |
| LFM2.5-2.6B-Q8_0 × yerel × bellek × üretim öneği | 88% | — | — | 33% | 100% | 0% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli × bellek × üretim öneği | — | 55% (11) | 33% (6) |
| LFM2.5-2.6B-Q8_0 × json × bellek × üretim öneği | — | 55% (11) | 33% (6) |
| LFM2.5-2.6B-Q8_0 × yerel × bellek × üretim öneği | — | 73% (11) | 50% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **LFM2.5-2.6B-Q8_0 × cli × bellek × üretim öneği**: kısa geçmiş ~150 jeton (%0.9), uzun geçmiş ~567 jeton (%3.5)
- **LFM2.5-2.6B-Q8_0 × json × bellek × üretim öneği**: kısa geçmiş ~150 jeton (%0.9), uzun geçmiş ~567 jeton (%3.5)
- **LFM2.5-2.6B-Q8_0 × yerel × bellek × üretim öneği**: kısa geçmiş ~150 jeton (%0.9), uzun geçmiş ~567 jeton (%3.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**LFM2.5-2.6B-Q8_0 × cli × bellek × üretim öneği** — 17 yanıt:

- `bel-01`: ``
- `bel-02`: ``
- `bel-03`: ``
- `bel-04`: ``
- `bel-05`: ``
- `bel-06`: ``
- `bel-07`: ``
- `bel-08`: ``
- `bel-09`: ``
- `bel-10`: ``
- `bel-11`: ``
- `bel-12`: ``
- `bel-13`: ``
- `bel-14`: ``
- `bel-15`: ``
- `bel-16`: ``
- `bel-17`: ``

**LFM2.5-2.6B-Q8_0 × json × bellek × üretim öneği** — 17 yanıt:

- `bel-01`: ``
- `bel-02`: ``
- `bel-03`: ``
- `bel-04`: ``
- `bel-05`: ``
- `bel-06`: ``
- `bel-07`: ``
- `bel-08`: ``
- `bel-09`: ``
- `bel-10`: ``
- `bel-11`: ``
- `bel-12`: ``
- `bel-13`: ``
- `bel-14`: ``
- `bel-15`: ``
- `bel-16`: ``
- `bel-17`: ``

**LFM2.5-2.6B-Q8_0 × yerel × bellek × üretim öneği** — 4 yanıt:

- `bel-05`: ``
- `bel-10`: ``
- `bel-11`: `Ev bilgisayarını uyandıracağım.`
- `bel-15`: ``

## Başarısız senaryolar

### LFM2.5-2.6B-Q8_0 × cli × bellek × üretim öneği — 9/17

- `bel-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `bel-06` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `bel-07` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `bel-08` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `bel-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `bel-11` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: ``
- `bel-13` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `bel-14` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `bel-15` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × json × bellek × üretim öneği — 9/17

- `bel-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `bel-06` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `bel-07` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `bel-08` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `bel-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `bel-11` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: ``
- `bel-13` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `bel-14` (tek tool): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `bel-15` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × yerel × bellek × üretim öneği — 9/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: ``
- `bel-02` (tool gerekmez): fazladan çağrı: note_search; düz metin beklenirken note_search çağrıldı — çıktı: ``
- `bel-03` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: ``
- `bel-04` (tek tool): fields fazladan verildi — çıktı: ``
- `bel-08` (tek tool): fields fazladan verildi — çıktı: ``
- `bel-11` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `Ev bilgisayarını uyandıracağım.`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: ``
- `bel-13` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi; fields fazladan verildi — çıktı: ``
- `bel-15` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
