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

Rol metni: `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 50 | 84% [71%–92%] | 85% | — | 0 | 0 | 0 (5) | 0 | 0 | 11 | 0.24 | 0.35 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | 18 | 78% [55%–91%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 5 | 0.11 | 0.17 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 0.93 | 1.00 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | 17 | 59% [36%–78%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 10 | 1.25 | 1.34 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 50 | 72% [58%–83%] | 91% | — | 0 | 0 | 1 (5) | 4 | 5 | 22 | 0.30 | 0.55 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | 18 | 0% [0%–18%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.09 | 0.27 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | 15 | 93% [70%–99%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.91 | 1.08 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | 17 | 59% [36%–78%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 21 | 1.24 | 1.42 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 100% | 100% | 0% | 100% | 100% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | — | — | — | 78% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | — | — | — | 100% | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | 100% | — | — | 0% | 50% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 100% | 100% | 14% | 12% | 100% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | — | — | — | 0% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | — | — | — | 0% | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | 100% | — | — | 0% | 50% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 84% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | 78% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | — | 100% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | — | 55% (11) | 67% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 72% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | 0% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | — | 93% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | — | 55% (11) | 67% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği** — desteksiz sayı geçen senaryolar:

- `tek-01`: `12` — yanıt: `Şu an saat 12:00, Pazar günü.`

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği** — desteksiz alıntı geçen senaryolar:

- `eks-07`: `name`, `contact_save`, `arguments`, `name`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği** — 8 yanıt:

- `yok-01`: `<tool> tell_user`
- `yok-02`: `<tool> tell_user`
- `yok-03`: `<tool> tell_user`
- `yok-04`: `<tool> tell_user`
- `yok-05`: `<tool> tell_user`
- `yok-06`: `<tool> tell_user`
- `yok-07`: `<tool> tell_user`
- `yok-08`: `<tool> tell_user`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği** — 14 yanıt:

- `kon-01`: `<tool> tell_user`
- `kon-02`: `<tool> tell_user`
- `kon-03`: `<tool> tell_user`
- `kon-04`: `<tool> tell_user`
- `kon-05`: `<tool> tell_user`
- `kon-06`: `<tool> tell_user`
- `kon-07`: `<tool> tell_user`
- `kon-08`: `<tool> tell_user`
- `kon-11`: `<tool> tell_user`
- `kon-12`: `<tool> tell_user`
- `kon-13`: `<tool> tell_user`
- `kon-14`: `<tool> tell_user`
- `kon-16`: `<tool> tell_user`
- `kon-18`: `<tool> tell_user`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği** — 1 yanıt:

- `hal-15`: `<tool> tell_user`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği** — 2 yanıt:

- `eks-07`: `<tool> {"name": "contact_save", "arguments": {"name": "", "phone": ""}}`
- `yok-05`: `<tool> tell_user`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği — 13/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query ""`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target ?`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Hatırlatma`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name ?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla.' geldi — çıktı: `<tool> task_create --due 2026-08-10T09:00:00Z --message Anneni ara ve doğum gününü kutla.`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message kütüphane kitabını ayın on beşine kadar geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği — 4/18

- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-10` (tool gerekmez): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği — 0/15

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği — 7/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-03` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-05` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`
- `bel-17` (ayırt etme): note_search beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Annem`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği — 17/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): weather: 'city' boş olamaz; wake_on_lan: 'target' boş olamaz; düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {}}`
- `eks-03` (eksik argüman): wake_on_lan: 'target' boş olamaz; düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:00:00Z", "message": "Hatırlatma zamanı"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `yok-01` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `yok-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `yok-03` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `yok-04` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `yok-06` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `yok-07` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `yok-08` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "Kütüphane kitabını geri ver."}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği — 18/18

- `kon-01` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-02` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-03` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `kon-04` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Hatırlatma"}}`
- `kon-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-06` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `kon-07` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `kon-08` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `kon-10` (tool gerekmez): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `kon-11` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {}}`
- `kon-12` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `kon-13` (tool gerekmez): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `kon-14` (tool gerekmez): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-16` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
- `kon-17` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `kon-18` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği — 1/15

- `hal-15` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği — 7/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-03` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-05` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Deniz"}}`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
- `bel-17` (ayırt etme): note_search beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Anne"}}`

## Okuma (2026-08-15) — kontrol işareti tool'a benzememeli

**Hipotez:** zorunlu modda modeli engelleyen şey dalın yokluğu değil, dalın **adı**.
`no_tool` olumsuz ve tool-merkezli: onu üretmek için önce "tool gerekmiyor" sonucuna varmak
gerekiyor, oysa `eks-*` senaryolarında tool **gerekiyor**, eksik olan bir alan. İşaretin adı
`tell_user` olsaydı "kullanıcıya hangi şehir olduğunu sor" apaçık kapsam içine girerdi.

Tek değişken: işaretin adı ve yönergesi. Yönergenin eski hâli de bir vaka listesiydi
(*"sohbet, teşekkür, tool'larla ilgisi olmayan bir söz"*) ve sormaktan hiç söz etmiyordu;
yenisi genel yazıldı: *"Kullanıcıya bir şey söyleyeceksen — yanıt, soru ya da başka bir
söz —"*. Karşılaştırma tabanı aynı gün, aynı sunucu, aynı rol metni, aynı kümeler.

| küme | `no_tool` | `tell_user` |
|---|---|---|
| eksik argüman ekseni (CLI) | %14 | **%0** |
| kontrol, CLI / JSON | %89 / %89 | %78 / **%0** |
| altın, CLI / JSON | %86 / %86 | %84 / %72 |
| bellek, CLI / JSON | %59 / %65 | %59 / %59 |
| halüsinasyon, CLI / JSON | %100 / %100 | %100 / %93 |

**Hipotez çürüdü ve çürüme biçimi asıl bulgu.** JSON kontrol kümesi %89 → %0: 18
senaryonun 18'i gerçek bir tool çağırıyor (`kon-01` "Hı hı, anladım" → `date_time`).
CLI'de işaret hâlâ kullanılıyor (`yok-*` satırlarında `<tool> tell_user`), JSON'da hiç
kullanılmıyor.

**Sebep: `tell_user` bir tool adına benziyor.** JSON biçiminde model tool adlarını
`{"name": …}` içine yazmayı bekliyor; gramer ise işareti yalnızca çıplak literal olarak
kabul ediyor. Bu çelişkiye düşen model işareti hiç seçmiyor, yerine gerçek bir tool
seçiyor. `no_tool`'un tuhaf, olumsuz adı iş yapıyormuş: **tool'a benzemediği için tool
sanılmıyordu.**

`grammar.py`'nin `NO_TOOL` docstring'i "ona JSON kostümü giydirmek onu tool'muş gibi
göstermek olurdu" diyor. Ölçüm bunun **adın kendisi** için de geçerli olduğunu gösteriyor:
kostüm kadar isim de kostümdür.

**Yapısal teşhis duruyor.** Eksik argüman ekseni %14 → %0, yani ad değişikliği "sorma"
davranışını açmadı bile. Tek işaretli bir dünyada model "tool gerekiyor ama alanım eksik"
durumunu ifade edemiyor. Bunun yolu isim değil, **ikinci bir işaret** — ve o, P25'i geri
almak değil yeni bir tasarım; §19.2 kapanmadan başlanacak bir iş değil, çünkü sonucu yine
modele bağlı çıkar.

Ölçüm bir kopyada koşuldu; `src/` ve `config/` değişmedi.
