# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen3.8-27B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384

| örnekleme | sunucu (`/props`) | istek (adaptör) |
|---|---:|---:|
| `dry_multiplier` | 0.0 | 0.0 |
| `frequency_penalty` | 0.0 | 0.0 |
| `min_p` | 0.0 | 0.0 |
| `mirostat` | 0 | 0 |
| `presence_penalty` | 1.5 | 0.0 **←** |
| `repeat_penalty` | 1.0 | 1.0 |
| `temperature` | 0.699999988079071 | 0.0 **←** |
| `top_k` | 20 | 0 **←** |
| `top_n_sigma` | -1.0 | -1.0 |
| `top_p` | 0.800000011920929 | 1.0 **←** |
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
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) × üretim öneği | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (2) | 0 | 0 | 12 | 0.78 | 0.95 |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) × üretim öneği | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (2) | 0 | 0 | 13 | 0.77 | 0.93 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 9 | 1.14 | 1.27 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 28 | 0.19 | 0.60 |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) × üretim öneği | 10 | 100% [72%–100%] | 100% | — | 0 | 0 | 0 (3) | 0 | 0 | 21 | 0.89 | 1.14 |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) × üretim öneği | 10 | 100% [72%–100%] | 100% | — | 0 | 0 | 0 (3) | 0 | 0 | 21 | 0.88 | 1.13 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 18 | 1.13 | 1.35 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 4 | 0 | 31 | 0.19 | 0.63 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) × üretim öneği | 83% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) × üretim öneği | 83% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği | 100% | — | — | 67% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) × üretim öneği | 100% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) × üretim öneği | 100% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği | 100% | — | — | 67% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği | — | — | — | 94% | — | — |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) × üretim öneği | — | 90% (10) | — |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) × üretim öneği | — | 90% (10) | — |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği | — | 91% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği | 94% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) × üretim öneği | — | 100% (10) | — |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) × üretim öneği | — | 100% (10) | — |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği | — | 91% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği | 94% (18) | — | — |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) × üretim öneği**: kısa geçmiş ~106 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) × üretim öneği**: kısa geçmiş ~104 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) × üretim öneği**: kısa geçmiş ~106 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) × üretim öneği**: kısa geçmiş ~104 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği** — desteksiz alıntı geçen senaryolar:

- `kon-18`: `name`, `course_schedule`, `arguments`, `day`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) × üretim öneği** — 3 yanıt:

- `gec-05`: `Administrator, iyi geceler.`
- `gec-09`: `Denizli'de hava açık, otuz altı derece.`
- `gec-10`: `Anlaşıldı.`

**Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) × üretim öneği** — 3 yanıt:

- `gec-05`: `İyi geceler, Administrator.`
- `gec-09`: `Denizli'de hava açık, otuz altı derece.`
- `gec-10`: `Anlaşıldı.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği** — 4 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `Ev-pc.`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, Administrator.`
- `kon-04`: `Anlaşıldı, Administrator.`
- `kon-05`: `Anladım. Dün akşamın güzel geçtiğini not ettim.`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler. Bellek, aktif verileri tutar. Depolama`
- `kon-07`: `Anlıyorum. Ne karışık? Bir şeyi netleştirmemi ister misin, yoksa sadece bir şeyi hatırlatmamı mı?`
- `kon-09`: `Evet, Administrator. Bir şehir adı verin; o şehrin güncel hava durumunu alırım.`
- `kon-10`: `Hatırlatıcı kurduğunda, makinede bekleyen zamanlanmış görevler listesine bir kayıt eklenir. Belirlediğin UTC zamanı geldiğinde, o kaydın message alanındaki metni sana iletilir. Görev, zamanı gelene ka`
- `kon-11`: `Administrator, notlar bu makinede saklanıyor ve yalnızca senin erişiminle okunuyor. Dışarıya gönderilmiyor, başka bir kullanıcıya açılmıyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. Her kayıt bir isim ve isteğe bağlı bir telefon numarası içerir. Rehberdeki kişileri listeleyebilir, yeni kişi ekleyebilir, var ol`
- `kon-13`: `Anlaşıldı, Administrator. Hatırlatıcı için bir işlem yapılmadı.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Administrator, yarınki hava durumu için şehir belirtmediniz. Hangi şehrin hava durumuna bakmamı istersiniz?`
- `kon-16`: `Not aldım. Ali ile dün görüşmüşsün, durumu iyi.`
- `kon-17`: `Administrator, saat 09:00 UTC.`
- `kon-18`: `Anlıyorum. Bugün ders programını kontrol edeyim, belki bir şey erteleyebiliriz.  <tool> course_schedule --day 1`

**Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) × üretim öneği** — 2 yanıt:

- `gec-05`: `İyi geceler, Administrator.`
- `gec-10`: `Anlaşıldı.`

**Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) × üretim öneği** — 2 yanıt:

- `gec-05`: `İyi geceler, Administrator.`
- `gec-10`: `Anlaşıldı.`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği** — 4 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `Ev-pc.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, Administrator.`
- `kon-04`: `Anlaşıldı.`
- `kon-05`: `Administrator, dün akşamla ilgili bir kayıt ya da not bulmam için arama yapmam gerekir. Ne aramamı istersiniz?`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler. Bellek, aktif verileri tutar. Depolama`
- `kon-07`: `Anlıyorum. Ne karışık?`
- `kon-09`: `Evet, Administrator. Bir şehir adı verin; o şehrin güncel hava durumunu alabilirim.`
- `kon-10`: `Hatırlatıcı kurduğumda, makinede bekleyen zamanlanmış görevler listesine yeni bir kayıt eklenir. Kayıt, belirttiğin zaman ve metni içerir. O an geldiğinde sistem seni o metinle uyarır. Görev, zamanı g`
- `kon-11`: `Administrator, notlar bu makinede saklanıyor ve erişim yalnızca seninle sınırlı. Dışarıya veri gönderen bir tool yok; not_search ve note_create yerel çalışır. Başka birinin görmesi için bu makineye fi`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. Her kayıt bir isim ve isteğe bağlı bir telefon numarası içerir. İsim vererek belirli bir kişiyi süzebilir, yeni kişi ekleyebilir,`
- `kon-13`: `Anlaşıldı, Administrator. Hatırlatıcı için bir işlem yapmıyorum.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Administrator, yarınki hava durumu için şehir belirtmediniz. Hangi şehrin hava durumunu kontrol etmemi istersiniz?`
- `kon-16`: `Not aldım. Ali ile dün görüşmüşsün ve durumu iyiydi.`
- `kon-17`: `Administrator, şu anki saat dokuz.`
- `kon-18`: `Anlıyorum. Bugün ders programını kontrol edeyim, belki bir şey erteleyebiliriz.  <tool> {"name": "course_schedule", "arguments": {"day": 1}}`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) × üretim öneği — 1/10

- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `Denizli'de hava açık, otuz altı derece.`

### Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) × üretim öneği — 1/10

- `gec-09` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `Denizli'de hava açık, otuz altı derece.`

### Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği — 2/17

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> volume`

### Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) × üretim öneği — 0/10

Yok.

### Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) × üretim öneği — 0/10

Yok.

### Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği — 2/17

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> {"name": "volume", "arguments": {}}`
