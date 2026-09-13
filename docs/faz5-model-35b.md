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
| Qwen3.6-35B-A3B-IQ4_XS × cli | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 2 (5) | 0 | 21 | 0.28 | 0.45 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 52 | 0.19 | 0.61 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | 8 | 100% [68%–100%] | 100% | 100% [68%–100%] (8) | 0 | 0 | 0 (0) | 0 | 11 | 0.76 | 0.86 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | 10 | 80% [49%–94%] | 62% | — | 0 | 0 | 0 (0) | 0 | 14 | 0.26 | 0.38 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | 4 | 100% [51%–100%] | 100% | — | 0 | 0 | 0 (4) | 0 | 7 | 0.73 | 0.80 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | 10 | 80% [49%–94%] | 71% | — | 0 | 0 | 0 (3) | 0 | 17 | 0.79 | 0.95 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | 10 | 80% [49%–94%] | 71% | — | 0 | 0 | 0 (3) | 0 | 18 | 0.76 | 0.90 |
| Qwen3.6-35B-A3B-IQ4_XS × json | 50 | 94% [84%–98%] | 94% | — | 0 | 0 | 2 (5) | 1 | 29 | 0.26 | 0.51 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 73 | 0.19 | 0.77 |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | 8 | 100% [68%–100%] | 100% | 88% [53%–98%] (8) | 0 | 0 | 0 (0) | 0 | 21 | 0.77 | 0.96 |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | 10 | 80% [49%–94%] | 75% | — | 0 | 0 | 0 (0) | 0 | 25 | 0.25 | 0.46 |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | 3 | 100% [44%–100%] | 100% | — | 0 | 0 | 0 (3) | 0 | 17 | 0.64 | 0.79 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | 9 | 78% [45%–94%] | 100% | — | 0 | 0 | 0 (2) | 0 | 27 | 0.74 | 0.97 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | 10 | 80% [49%–94%] | 100% | — | 0 | 0 | 0 (3) | 0 | 26 | 0.73 | 0.96 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | 100% | — | 0% | — | 100% | 75% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | 100% | 100% | — | — | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | 100% | — | 0% | — | 100% | 75% |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | 100% | — | — | — | — | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | 80% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 | 100% (8) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik | 80% (10) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × uzun | 100% (4) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × adim2 | 100% (8) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik | 80% (10) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × uzun | 100% (3) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | — | 75% (4) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | — | 80% (5) | 80% (5) |

## İkinci adım

Tool sonucu geri beslendikten sonraki adım (P25.2). Zincirin ikinci halkası bugüne kadar hiç ölçülmemişti; `Step2.expected` `None` olan satırlarda doğru davranış **çağrı yazmamaktır** — o satırlar olmadan bu sayaç, fazla çağrıyı iyileşme diye raporlardı.

**Qwen3.6-35B-A3B-IQ4_XS × json × adim2** — ikinci adımda düşenler:

- `adm-05`: 2. adımda `çağrı yok`


## Ölçülemeyen senaryolar

Servis iki denemede de düştü. Bu satırlar **hiçbir doğruluk paydasına girmiyor**: modelin yanlışı değil, ölçümün eksiği. Yanlış cevap sayılsalardı model servisin kopmasından sorumlu tutulurdu; hiç yazılmasalardı payda sessizce küçülür ve rapor eksikliğini gizlerdi (Kural 13, Kural 14).

**Bir sayı burada görünüyorsa o koşu eksiktir ve öyle okunmalıdır.**

**Qwen3.6-35B-A3B-IQ4_XS × json × uzun** — 1/4:

- `uzn-04`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: 

**Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli)** — 1/10:

- `gec-01`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: 


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × cli** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `71` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB (yaklaşık %71 boş)

Sistem belleği açısından oldukça rahat bir durumda.`

**Qwen3.6-35B-A3B-IQ4_XS × json** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `29` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB

Genel olarak bellek kullanımı oldukça düşük (%29 civarı) ve sistem rahat çalışıyor.`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli — 6/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target cihaz_adi`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name Yeni Kişi`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken '"Anneni ara ve doğum gününü kutla."' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:01:00Z --message "Anneni ara ve doğum gününü kutla."`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × adim2 — 0/8

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × saglamlik — 5/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'Bugün çok yoğun geçti.' geldi — çıktı: `<tool> note_create --body Bugün çok yoğun geçti.`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul --fields temperature`
- `sag-07` (serbest metin): body: '"acele etme" dedi, ben de tamam dedim' beklenirken 'acele etme dedi, ben de tamam dedim.' geldi — çıktı: `<tool> note_create --body acele etme dedi, ben de tamam dedim.`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature,humidity`
- `sag-10` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`

### Qwen3.6-35B-A3B-IQ4_XS × cli × uzun — 0/4

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) — 4/10

- `gec-02` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city İzmir --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message On saniye sonra bir şey yapman gerekiyor.`
- `gec-09` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) — 4/10

- `gec-02` (tek tool): city: 'İzmir' beklenirken '"İzmir"' geldi; fields fazladan verildi — çıktı: `<tool> weather --city "İzmir" --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message On saniye sonra bir şey yapman gerekiyor.`
- `gec-09` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × json — 5/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "default_device"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × adim2 — 1/8

- `adm-05` (çok tool): 2. adım: contact_save beklenirken çağrı üretilmedi — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ayşe"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × saglamlik — 4/10

- `sag-01` (serbest metin): body: '-- bugün -- çok yoğun geçti' beklenirken 'bugün çok yoğun geçti.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "bugün çok yoğun geçti."}}`
- `sag-02` (serbest metin): note_create beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `sag-09` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature", "humidity"]}}`
- `sag-10` (eksik argüman): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × uzun — 0/4

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
