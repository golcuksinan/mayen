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
| LFM2.5-2.6B-Q8_0 × cli × üretim öneği | 50 | 30% [19%–44%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.05 |
| LFM2.5-2.6B-Q8_0 × cli × halusinasyon × üretim öneği | 15 | 7% [1%–30%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.24 |
| LFM2.5-2.6B-Q8_0 × json × üretim öneği | 50 | 30% [19%–44%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.03 |
| LFM2.5-2.6B-Q8_0 × json × halusinasyon × üretim öneği | 15 | 7% [1%–30%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.00 | 1.24 |
| LFM2.5-2.6B-Q8_0 × yerel × üretim öneği | 50 | 76% [63%–86%] | 79% | — | 0 | 2 | 0 (5) | 0 | 0 | 4 | 0.43 | 0.76 |
| LFM2.5-2.6B-Q8_0 × yerel × halusinasyon × üretim öneği | 15 | 87% [62%–96%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 0 | 0.33 | 0.50 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli × üretim öneği | 0% | 0% | 100% | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × cli × halusinasyon × üretim öneği | — | — | — | 100% | 0% | — |
| LFM2.5-2.6B-Q8_0 × json × üretim öneği | 0% | 0% | 100% | 100% | 0% | 0% |
| LFM2.5-2.6B-Q8_0 × json × halusinasyon × üretim öneği | — | — | — | 100% | 0% | — |
| LFM2.5-2.6B-Q8_0 × yerel × üretim öneği | 64% | 67% | 86% | 100% | 75% | 71% |
| LFM2.5-2.6B-Q8_0 × yerel × halusinasyon × üretim öneği | — | — | — | 100% | 86% | — |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| LFM2.5-2.6B-Q8_0 × cli × üretim öneği | 30% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × cli × halusinasyon × üretim öneği | — | 7% (15) | — |
| LFM2.5-2.6B-Q8_0 × json × üretim öneği | 30% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × json × halusinasyon × üretim öneği | — | 7% (15) | — |
| LFM2.5-2.6B-Q8_0 × yerel × üretim öneği | 76% (50) | — | — |
| LFM2.5-2.6B-Q8_0 × yerel × halusinasyon × üretim öneği | — | 87% (15) | — |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **LFM2.5-2.6B-Q8_0 × cli × üretim öneği**: geçmişsiz ~37 jeton (%0.2)
- **LFM2.5-2.6B-Q8_0 × cli × halusinasyon × üretim öneği**: kısa geçmiş ~92 jeton (%0.6)
- **LFM2.5-2.6B-Q8_0 × json × üretim öneği**: geçmişsiz ~37 jeton (%0.2)
- **LFM2.5-2.6B-Q8_0 × json × halusinasyon × üretim öneği**: kısa geçmiş ~92 jeton (%0.6)
- **LFM2.5-2.6B-Q8_0 × yerel × üretim öneği**: geçmişsiz ~37 jeton (%0.2)
- **LFM2.5-2.6B-Q8_0 × yerel × halusinasyon × üretim öneği**: kısa geçmiş ~92 jeton (%0.6)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**LFM2.5-2.6B-Q8_0 × cli × üretim öneği** — 50 yanıt:

- `tek-01`: ``
- `tek-02`: ``
- `tek-03`: ``
- `tek-04`: ``
- `tek-05`: ``
- `tek-06`: ``
- `tek-07`: ``
- `tek-08`: ``
- `tek-09`: ``
- `tek-10`: ``
- `tek-11`: ``
- `tek-12`: ``
- `tek-13`: ``
- `tek-14`: ``
- `cok-01`: ``
- `cok-02`: ``
- `cok-03`: ``
- `cok-04`: ``
- `cok-05`: ``
- `cok-06`: ``
- `eks-01`: ``
- `eks-02`: ``
- `eks-03`: ``
- `eks-04`: ``
- `eks-05`: ``
- `eks-06`: ``
- `eks-07`: ``
- `yok-01`: ``
- `yok-02`: ``
- `yok-03`: ``
- `yok-04`: ``
- `yok-05`: ``
- `yok-06`: ``
- `yok-07`: ``
- `yok-08`: ``
- `ayr-01`: ``
- `ayr-02`: ``
- `ayr-03`: ``
- `ayr-04`: ``
- `ayr-05`: ``
- `ayr-06`: ``
- `ayr-07`: ``
- `ayr-08`: ``
- `ser-01`: ``
- `ser-02`: ``
- `ser-03`: ``
- `ser-04`: ``
- `ser-05`: ``
- `ser-06`: ``
- `ser-07`: ``

**LFM2.5-2.6B-Q8_0 × cli × halusinasyon × üretim öneği** — 15 yanıt:

- `hal-01`: ``
- `hal-02`: ``
- `hal-03`: ``
- `hal-04`: ``
- `hal-05`: ``
- `hal-06`: ``
- `hal-07`: ``
- `hal-08`: ``
- `hal-09`: ``
- `hal-10`: ``
- `hal-11`: ``
- `hal-12`: ``
- `hal-13`: ``
- `hal-14`: ``
- `hal-15`: ``

**LFM2.5-2.6B-Q8_0 × json × üretim öneği** — 50 yanıt:

- `tek-01`: ``
- `tek-02`: ``
- `tek-03`: ``
- `tek-04`: ``
- `tek-05`: ``
- `tek-06`: ``
- `tek-07`: ``
- `tek-08`: ``
- `tek-09`: ``
- `tek-10`: ``
- `tek-11`: ``
- `tek-12`: ``
- `tek-13`: ``
- `tek-14`: ``
- `cok-01`: ``
- `cok-02`: ``
- `cok-03`: ``
- `cok-04`: ``
- `cok-05`: ``
- `cok-06`: ``
- `eks-01`: ``
- `eks-02`: ``
- `eks-03`: ``
- `eks-04`: ``
- `eks-05`: ``
- `eks-06`: ``
- `eks-07`: ``
- `yok-01`: ``
- `yok-02`: ``
- `yok-03`: ``
- `yok-04`: ``
- `yok-05`: ``
- `yok-06`: ``
- `yok-07`: ``
- `yok-08`: ``
- `ayr-01`: ``
- `ayr-02`: ``
- `ayr-03`: ``
- `ayr-04`: ``
- `ayr-05`: ``
- `ayr-06`: ``
- `ayr-07`: ``
- `ayr-08`: ``
- `ser-01`: ``
- `ser-02`: ``
- `ser-03`: ``
- `ser-04`: ``
- `ser-05`: ``
- `ser-06`: ``
- `ser-07`: ``

**LFM2.5-2.6B-Q8_0 × json × halusinasyon × üretim öneği** — 15 yanıt:

- `hal-01`: ``
- `hal-02`: ``
- `hal-03`: ``
- `hal-04`: ``
- `hal-05`: ``
- `hal-06`: ``
- `hal-07`: ``
- `hal-08`: ``
- `hal-09`: ``
- `hal-10`: ``
- `hal-11`: ``
- `hal-12`: ``
- `hal-13`: ``
- `hal-14`: ``
- `hal-15`: ``

**LFM2.5-2.6B-Q8_0 × yerel × üretim öneği** — 22 yanıt:

- `tek-07`: ``
- `tek-09`: ``
- `tek-11`: ``
- `tek-12`: ``
- `tek-13`: ``
- `cok-04`: ``
- `eks-01`: ``
- `eks-02`: ``
- `eks-03`: ``
- `eks-04`: ``
- `eks-06`: ``
- `eks-07`: ``
- `yok-01`: `You're welcome! I'm glad I could help. If you have any more questions or need assistance in the future, feel free to ask. Have a great day!`
- `yok-02`: `Hello. I am functioning normally. How can I assist you today?`
- `yok-03`: `Sure! Here's a light-hearted joke for you:  **Why did the scarecrow win an award?**  Because he was outstanding in his field! 🌾😄`
- `yok-04`: `Paris is the capital of France.`
- `yok-05`: ``
- `yok-06`: `Ben LFM, Liquid AI tarafından geliştirilen bir yapay zeka asistanı modelim. İzole olarak çalışıyorum ve özellikle cihaz üzerinde (telefon, laptop, araba vb.) verimli çalışma sağlamam için tasarl`
- `yok-07`: `Two times two equals 4.`
- `yok-08`: `Yes, I will speak more slowly. Let me adjust my pace accordingly.  (Processing slower...)   I understand you'd like me to speak more slowly. I'll do so from now on. Is there something`
- `ayr-03`: ``
- `ayr-06`: ``

**LFM2.5-2.6B-Q8_0 × yerel × halusinasyon × üretim öneği** — 2 yanıt:

- `hal-03`: ``
- `hal-15`: ``

## Başarısız senaryolar

### LFM2.5-2.6B-Q8_0 × cli × üretim öneği — 35/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: ``
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-03` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `tek-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `tek-05` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: ``
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: ``
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: ``
- `tek-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: ``
- `tek-14` (tek tool): task_cancel beklenirken çağrı üretilmedi — çıktı: ``
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: ``
- `cok-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `cok-05` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: ``
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-02` (ayırt etme): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-08` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: ``
- `ser-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-06` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-07` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × cli × halusinasyon × üretim öneği — 14/15

- `hal-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-02` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `hal-08` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `hal-09` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × json × üretim öneği — 35/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: ``
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-03` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `tek-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: ``
- `tek-05` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: ``
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: ``
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: ``
- `tek-08` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: ``
- `tek-14` (tek tool): task_cancel beklenirken çağrı üretilmedi — çıktı: ``
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: ``
- `cok-03` (çok tool): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `cok-05` (çok tool): system_metrics beklenirken çağrı üretilmedi — çıktı: ``
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-02` (ayırt etme): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-08` (ayırt etme): note_delete beklenirken çağrı üretilmedi — çıktı: ``
- `ser-01` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-02` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-06` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-07` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × json × halusinasyon × üretim öneği — 14/15

- `hal-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-02` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `hal-08` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `hal-09` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × yerel × üretim öneği — 17/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: ``
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: ``
- `tek-09` (tek tool): contact_get: 'name' boş olamaz; contact_get beklenirken çağrı üretilmedi — çıktı: ``
- `tek-11` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `tek-13` (tek tool): note_delete beklenirken çağrı üretilmedi — çıktı: ``
- `cok-04` (çok tool): course_schedule beklenirken çağrı üretilmedi — çıktı: ``
- `cok-06` (çok tool): contact_save beklenirken contact_get çağrıldı — çıktı: ``
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: ``
- `ayr-02` (ayırt etme): body: 'Alışveriş' beklenirken 'Alışveriş notu' geldi — çıktı: ``
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: ``
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: ``
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken 'yarin erken kalk' geldi — çıktı: ``
- `ser-03` (serbest metin): note_create beklenirken contact_get çağrıldı — çıktı: ``
- `ser-05` (serbest metin): fazladan çağrı: note_search; task_create beklenirken contact_get çağrıldı — çıktı: ``
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphane kitabını ayın on beşine kadar (2026-01-15) geri ver).' geldi — çıktı: ``
- `ser-07` (serbest metin): query: 'elektrik faturası' beklenirken 'elektrik fatura' geldi — çıktı: ``

### LFM2.5-2.6B-Q8_0 × yerel × halusinasyon × üretim öneği — 2/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: ``
- `hal-10` (ayırt etme): note_search beklenirken task_list çağrıldı — çıktı: ``
