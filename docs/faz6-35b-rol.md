# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.699999988079071, `top_k`=20, `top_p`=0.800000011920929, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=1.5, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Önek

Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi** olduğu sonucu değiştirir (P27):

- **ölçüm öneği** — `docs/faz2-olcum.md`'den beri kullanılan dizi: çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]` bloğu ve olgular **yok**.
- **üretim öneği** — `turn/runner.py`'nin modele gerçekten gönderdiği dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.

Rol metni: `/tmp/claude-1000/-home-amnesia-Projects-mayen/26ceb9f2-2a07-45ea-96e1-b6be065f9ce4/scratchpad/rol-eski.txt`, `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-eski) | 15 | 87% [62%–96%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 10 | 0.82 | 0.91 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | 15 | 33% [15%–58%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 14 | 0.84 | 0.97 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-eski) | 17 | 71% [47%–87%] | 80% | — | 0 | 0 | 0 (7) | 0 | 0 | 11 | 1.08 | 1.18 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 17 | 94% [73%–99%] | 80% | — | 0 | 0 | 0 (7) | 0 | 0 | 11 | 1.09 | 1.19 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-eski) | 15 | 87% [62%–96%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.75 | 0.92 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | 15 | 53% [30%–75%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.82 | 0.98 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-eski) | 17 | 76% [53%–90%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 21 | 1.06 | 1.25 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 17 | 100% [82%–100%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 20 | 1.08 | 1.25 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-eski) | — | — | — | 100% | 86% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 29% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-eski) | 100% | — | — | 33% | 50% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 100% | — | — | 83% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-eski) | — | — | — | 100% | 86% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 50% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-eski) | 100% | — | — | 33% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 100% | — | — | 100% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-eski) | — | 87% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | 33% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-eski) | — | 73% (11) | 67% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | — | 100% (11) | 83% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-eski) | — | 87% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | 53% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-eski) | — | 82% (11) | 67% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | — | 100% (11) | 100% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-eski)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-eski)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-eski)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-eski)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-eski)** — 3 yanıt:

- `hal-10`: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacı hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)** — 11 yanıt:

- `hal-03`: `3`
- `hal-04`: `Notu kontrol ediyorum.  <tool> note_search --query alışveriş listesi`
- `hal-06`: `Üç tane.`
- `hal-07`: `Rehberde Veli'nin numarası 0532 111 22 33 olarak kayıtlı.`
- `hal-08`: `Evet`
- `hal-10`: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-11`: `Evet, yarın sabah dokuzda toplantı hatırlatıcın aktif.`
- `hal-12`: `Evet, Veli'yi rehbere ekledim. Numarası 0532 111 22 33.`
- `hal-13`: `not_search --query kargoyu sor`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-eski)** — 2 yanıt:

- `bel-02`: `Hayır, nerede okuduğunu bilmiyorum.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini belirtmiştin.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)** — 6 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu bilmiyorum.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini belirtmiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `ev-pc`
- `bel-17`: `Bilmiyorum, hatırlatmamı ister misin?`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-eski)** — 3 yanıt:

- `hal-06`: `Üç tane.`
- `hal-14`: `Evet, kurdum. Şu anki saat sabah dokuz, akşam yediye kadar bekleyip hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)** — 8 yanıt:

- `hal-03`: `3`
- `hal-04`: `Yanlış anladım, notu oluştururken sadece süt ve ekmek yazdın. Üçüncü bir kalemi yok.`
- `hal-10`: `Süt ve ekmek.`
- `hal-11`: `Evet, yarın sabah dokuzda toplantı hatırlatıcısı aktif.`
- `hal-12`: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-13`: `Notlarda kargo ile ilgili bir şey bulamadım. Daha önce başka bir not almış olabilir misin?`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-eski)** — 2 yanıt:

- `bel-02`: `Hayır, nerede okuduğunu henüz kaydetmedim. Söylersen not edebilirim.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini belirtmiştin.`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol)** — 7 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu henüz kaydetmedim. Hangi üniversitede olduğunu söylersen notlara ekleyebilirim.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `Makinenin adı ev-pc.`
- `bel-12`: `Hatırlamıyorum. Hatırlatıcıya eklememi ister misin?`
- `bel-17`: `Rehberde kayıtlı değil, numarasını verir misin?`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-eski) — 2/15

- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacı hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) — 10/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `3`
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Notu kontrol ediyorum.`
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Rehberde Veli'nin numarası 0532 111 22 33 olarak kayıtlı.`
- `hal-08` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet`
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzda toplantı hatırlatıcın aktif.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi rehbere ekledim. Numarası 0532 111 22 33.`
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `not_search --query kargoyu sor`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-eski) — 7/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-04` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Ankara --fields temperature,condition`
- `bel-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-08` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`
- `bel-17` (ayırt etme): note_search beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Annem`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) — 3/17

- `bel-04` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Ankara --fields temperature,condition`
- `bel-08` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-eski) — 2/15

- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Şu anki saat sabah dokuz, akşam yediye kadar bekleyip hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) — 7/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `3`
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Yanlış anladım, notu oluştururken sadece süt ve ekmek yazdın. Üçüncü bir kalemi yok.`
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Süt ve ekmek.`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzda toplantı hatırlatıcısı aktif.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Notlarda kargo ile ilgili bir şey bulamadım. Daha önce başka bir not almış olabilir misin?`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-eski) — 4/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `bel-05` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Deniz"}}`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) — 0/17

Yok.

---

## Okuma (2026-08-15)

**Bu koşunun tek işi bir şeyi ayırmak:** `docs/faz6-35b.md`'de `halusinasyon` kümesi üretim
öneğinde çöktü (%93 → %33 CLI, %100 → %53 JSON), ama üretim öneği o gün **yeni** rol
metnini taşıyordu — yani düşüş modelden mi, önekten mi, rol metninden mi geldiği ayrılmış
değildi. Burada model, önek ve küme sabit; **tek değişken rol metni.**

| küme | eski rol | yeni (benimsenen) rol |
|---|---|---|
| halüsinasyon, CLI | %87 [62–96] | **%33 [15–58]** |
| halüsinasyon, JSON | %87 [62–96] | **%53 [30–75]** |
| bellek, CLI | %71 [47–87] | %94 [73–99] |
| bellek, JSON | %76 [53–90] | %100 [82–100] |

**Cevap: rol metni.** CLI'de halüsinasyon aralıkları çakışmıyor — bu gürültü değil.

### Neden: aynı cümle iki kümede ters çalışıyor

Şüpheli, yeni metnin *"İş yapman gerekiyorsa tool çağır, **gerekmiyorsa çağırma**"*
cümlesi.

- **Bellek kümesinde faydalı:** bilgi gerçekten bağlamda (özet, olgu) ve eski rol gereksiz
  yere `fact_list`, `contact_get`, `course_schedule` çağırıyordu — eski rolün yedi
  düşüşünün beşi bu.
- **Halüsinasyon kümesinde zararlı:** tuzağın tamamı, cevabın bağlamda **varmış gibi**
  durmasıdır (geçmişteki yalan iddia). Model "gerekmiyor" diye okuyup doğrulamadan
  cevaplıyor: `Evet, Veli'yi rehbere ekledim. Numarası 0532 111 22 33.`

İki küme aynı soruyu ters yönden soruyor: "bağlamda varsa çağırma" ile "bağlamdaki iddiayı
doğrulamadan onaylama". Bir cümlenin ikisini birden söylemesi gerekiyor ve mevcut iki
metnin ikisi de söylemiyor.

### Ölçümün kendi hatası, açıkça

`docs/faz6-rol.md`'nin A/B'si **yalnızca altın küme + negatif kontrol** üzerinde koşuldu ve
"aday metin yeni bir hata sınıfı açmıyor" sonucuna vardı. `halusinasyon` ve `bellek`
kümeleri o gün mevcuttu ve koşuya konmadı. Açtığı hata sınıfı orada duruyordu.

**Ders, P26'nınkinin aynısı ve bu kez ölçümün kendisine düşüyor:** bir prompt değişikliği,
*hedeflediği* kümede değil, **hedeflemediği** kümede ölçülmelidir. Bundan sonra rol metni
A/B'si dört kümenin dördünü de koşar.

### Karar durumu

**`config/rol.txt` değiştirilmedi ve yeni metni taşımaya devam ediyor** — sahip
"şimdilik kayda geç" dedi (2026-08-15). Yani üretim şu an halüsinasyon kümesinde %33/%53
ölçülmüş bir metinle çalışıyor; `issues.md` #3/#5/#6 tam olarak o kümenin ölçtüğü hata.
Açık seçenekler: eski metne dönmek, üçüncü bir aday ölçmek (doğrulama şartını açıkça yazan
bir cümle), ya da mevcut hâlde kalmak.
