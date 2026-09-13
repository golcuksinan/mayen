# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen3.8-27B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.699999988079071, `top_k`=20, `top_p`=0.800000011920929, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=1.5, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Toplam

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool | uydurulan argüman | desteksiz sayı (n) | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli | 50 | 98% [90%–100%] | 88% | — | 0 | 0 | 3 (5) | 0 | 22 | 0.20 | 0.47 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 61 | 0.13 | 0.93 |
| Qwen3.8-27B-IQ4_XS × cli × adim2 | 8 | 100% [68%–100%] | 100% | 88% [53%–98%] (8) | 0 | 0 | 0 (0) | 0 | 11 | 0.57 | 0.71 |
| Qwen3.8-27B-IQ4_XS × cli × saglamlik | 10 | 100% [72%–100%] | 67% | — | 0 | 0 | 0 (0) | 0 | 17 | 0.19 | 0.38 |
| Qwen3.8-27B-IQ4_XS × cli × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 7 | 0.63 | 0.71 |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (3) | 0 | 16 | 0.55 | 0.74 |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) | 10 | 90% [60%–98%] | 100% | — | 0 | 0 | 0 (3) | 0 | 16 | 0.54 | 0.73 |
| Qwen3.8-27B-IQ4_XS × json | 50 | 98% [90%–100%] | 94% | — | 0 | 0 | 2 (4) | 0 | 30 | 0.18 | 0.52 |
| Qwen3.8-27B-IQ4_XS × json × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 70 | 0.13 | 1.03 |
| Qwen3.8-27B-IQ4_XS × json × adim2 | 8 | 100% [68%–100%] | 100% | 100% [68%–100%] (8) | 0 | 0 | 0 (0) | 0 | 22 | 0.56 | 0.80 |
| Qwen3.8-27B-IQ4_XS × json × saglamlik | 10 | 100% [72%–100%] | 67% | — | 0 | 0 | 0 (0) | 0 | 26 | 0.19 | 0.47 |
| Qwen3.8-27B-IQ4_XS × json × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 17 | 0.42 | 0.60 |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 28 | 0.47 | 0.79 |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 28 | 0.53 | 0.85 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli | 100% | 100% | 100% | 100% | 88% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.8-27B-IQ4_XS × cli × saglamlik | 100% | — | 100% | — | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × uzun | 100% | — | — | — | — | 100% |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json | 93% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.8-27B-IQ4_XS × json × saglamlik | 100% | — | 100% | — | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × uzun | 100% | — | — | — | — | 100% |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) | 83% | — | — | 100% | 100% | 0% |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) | 83% | — | — | 100% | 100% | 0% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli | 98% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol | 94% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × adim2 | 100% (8) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × saglamlik | 100% (10) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × uzun | 100% (4) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) | — | 80% (5) | 100% (5) |
| Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) | — | 80% (5) | 100% (5) |
| Qwen3.8-27B-IQ4_XS × json | 98% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol | 94% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × adim2 | 100% (8) | — | — |
| Qwen3.8-27B-IQ4_XS × json × saglamlik | 100% (10) | — | — |
| Qwen3.8-27B-IQ4_XS × json × uzun | 100% (4) | — | — |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) | — | 80% (5) | 80% (5) |

## İkinci adım

Tool sonucu geri beslendikten sonraki adım (P25.2). Zincirin ikinci halkası bugüne kadar hiç ölçülmemişti; `Step2.expected` `None` olan satırlarda doğru davranış **çağrı yazmamaktır** — o satırlar olmadan bu sayaç, fazla çağrıyı iyileşme diye raporlardı.

**Qwen3.8-27B-IQ4_XS × cli × adim2** — ikinci adımda düşenler:

- `adm-05`: 2. adımda `çağrı yok`


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.8-27B-IQ4_XS × cli** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `Şu an saat 09:00 (UTC), 9 Ağustos 2026 Pazar.`
- `tek-05`: `22.6`, `71` — yanıt: `Bilgisayarın bellek durumu şu an gayet iyi:

- **Toplam RAM:** 32 GB
- **Kullanılan:** 9.4 GB
- **Boşta kalan:** ~22.6 GB (yaklaşık %71 boş)

CPU kullanımı da düşük (%12), yani sistem rahat çalışıyor.`

**Qwen3.8-27B-IQ4_XS × json** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `71` — yanıt: `Bilgisayarın bellek durumu şu an gayet iyi:

- **Toplam RAM:** 32 GB
- **Kullanılan:** 9.4 GB
- **Boşta kalan:** ~22.6 GB (yaklaşık %71 boş)

CPU kullanımı da düşük (%12), yani sistem rahat çalışıyor.`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `Bu işlem geri alınamaz. Ali'yi rehberden silmemi onaylıyor musun?`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`

### Qwen3.8-27B-IQ4_XS × cli × adim2 — 1/8

- `adm-05` (çok tool): 2. adım: contact_save beklenirken çağrı üretilmedi — çıktı: `<tool> contact_get --name Ayşe`

### Qwen3.8-27B-IQ4_XS × cli × saglamlik — 3/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'Bugün çok yoğun geçti.' geldi — çıktı: `<tool> note_create --body Bugün çok yoğun geçti.`
- `sag-07` (serbest metin): body: '"acele etme" dedi, ben de tamam dedim' beklenirken 'acele etme dedi, ben de tamam dedim.' geldi — çıktı: `<tool> note_create --body acele etme dedi, ben de tamam dedim.`
- `sag-08` (serbest metin): body: 'sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en son da haberleri aç' beklenirken 'Sabah rutini: 1) Suyu ısıt, 2) Çayı demle, 3) Ekmeği kızart, 4) Masayı hazırla, 5) Haberleri aç.' geldi — çıktı: `<tool> note_create --body Sabah rutini: 1) Suyu ısıt, 2) Çayı demle, 3) Ekmeği kızart, 4) Masayı hazırla, 5) Haberleri a`

### Qwen3.8-27B-IQ4_XS × cli × uzun — 0/4

Yok.

### Qwen3.8-27B-IQ4_XS × cli × geçmiş(izli) — 1/10

- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `Hayır, henüz kurmadım — önce hatırlatılacak mesajı sormuştum. Mesajı yazarsanız hemen oluşturayım.`

### Qwen3.8-27B-IQ4_XS × cli × geçmiş(izsiz) — 1/10

- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `Hayır, henüz kurmadım — önce hatırlatılacak mesajı sormuştum. Mesajı yazarsanız hemen oluşturayım.`

### Qwen3.8-27B-IQ4_XS × json — 3/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00 (UTC).`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.8-27B-IQ4_XS × json × adim2 — 0/8

Yok.

### Qwen3.8-27B-IQ4_XS × json × saglamlik — 3/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'Bugün çok yoğun geçti.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Bugün çok yoğun geçti."}}`
- `sag-08` (serbest metin): body: 'sabah kalkınca önce suyu ısıt, sonra çayı demle, bu arada ekmeği kızart ve masayı hazırla, en son da haberleri aç' beklenirken 'Sabah rutini: önce suyu ısıt, sonra çayı demle; bu arada ekmeği kızart ve masayı hazırla; en son haberleri aç.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Sabah rutini: önce suyu ısıt, sonra çayı demle; bu arada ekmeği kı`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "humidity"]}}`

### Qwen3.8-27B-IQ4_XS × json × uzun — 0/4

Yok.

### Qwen3.8-27B-IQ4_XS × json × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `Hayır, henüz kurmadım — sadece "kuracağım" dedim ama tool çağırmadım. Şimdi hemen oluşturuyorum.`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `Kitabı geri ver`

### Qwen3.8-27B-IQ4_XS × json × geçmiş(izsiz) — 2/10

- `gec-04` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `Hayır, henüz kurmadım — sadece "kuracağım" dedim ama tool çağırmadım. Şimdi hemen oluşturuyorum.`
- `gec-08` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `Kitabı geri ver`
