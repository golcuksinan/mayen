# Faz 0 — çağrı biçimi ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B-UD-Q4_K_XL × cli | 50 | 60% | 50% | 0 | 0 | 0 | 28 | 0.30 |
| Qwen3.5-9B-UD-Q4_K_XL × json | 50 | 84% | 100% | 0 | 0 | 1 | 31 | 0.33 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.5-9B-UD-Q4_K_XL × cli | 50% | 33% | 86% | 100% | 38% | 57% |
| Qwen3.5-9B-UD-Q4_K_XL × json | 100% | 67% | 43% | 88% | 100% | 86% |

## Ölçülmeyen

§17.1'in üçüncü halüsinasyon sayacı — tool sonucunda bulunmayan bir bilgiyi yanıtta iddia etme — bu koşuda **ölçülmedi**: tool'un çalışıp sonucun modele geri beslenmesini, yani ajan döngüsünü (§8.2, P8) gerektiriyor.

## Başarısız senaryolar

### Qwen3.5-9B-UD-Q4_K_XL × cli — 28/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00 UTC.`
- `tek-02` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `contact_get --name Veli`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul`
- `tek-06` (tek tool): system_metrics beklenirken çağrı üretilmedi — çıktı: `Diskte ne kadar yer kaldığını öğrenmek için `system_metrics` aracını kullanacağım.`
- `tek-07` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `Masaüstü bilgisayarı uyandırmak için gerekli olan `wake_on_lan` aracını kullanmak istiyorum. Ancak, bu işlemi gerçekleşt`
- `tek-08` (tek tool): name: 'Ali' beklenirken 'Ali </tool>' geldi — çıktı: `<tool> contact_get --name Ali </tool>`
- `tek-09` (tek tool): contact_get beklenirken çağrı üretilmedi — çıktı: `contact_get`
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `task_list`
- `tek-11` (tek tool): day fazladan verildi — çıktı: `<tool> course_schedule --day 1`
- `tek-12` (tek tool): course_schedule beklenirken çağrı üretilmedi — çıktı: `Salı günü ders programını kontrol ediyorum.`
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `contact_get --name Ali`
- `cok-02` (çok tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00. Ankara'daki hava durumu için şu tool'u çağırıyorum:`
- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 2`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `contact_save --name Veli --phone 05555555555`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `ayr-01` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `note_search --query "alışveriş"`
- `ayr-02` (ayırt etme): body: 'Alışveriş' beklenirken '"Alışveriş" </tool>' geldi — çıktı: `<tool> note_create --body "Alışveriş" </tool>`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `contact_save --name Ayşe`
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `contact_get --name Ayşe`
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `task_list`
- `ayr-06` (ayırt etme): task_create beklenirken çağrı üretilmedi — çıktı: `task_create --due 2026-08-10T09:00:00Z --message Yarın sabah dokuzda toplantı var.`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'süt, ekmek ve yumurta almayı unutma. </tool>' geldi — çıktı: `<tool> note_create --body süt, ekmek ve yumurta almayı unutma. </tool>`
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken '--önemli-- yarın erken kalk. </tool>' geldi — çıktı: `<tool> note_create --body --önemli-- yarın erken kalk. </tool>`
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `contact_save --name Ali --phone 05551234567`
- `ser-04` (serbest metin): note_search beklenirken çağrı üretilmedi — çıktı: `note_search --query "kütüphane kitabı"`
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: `contact_get --name annem`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken '"kütüphane kitabını ayın on beşine kadar geri ver." </tool>' geldi — çıktı: `<tool> note_create --body "kütüphane kitabını ayın on beşine kadar geri ver." </tool>`
- `ser-07` (serbest metin): query: 'elektrik faturası' beklenirken '"elektrik faturası"' geldi — çıktı: `<tool> note_search --query "elektrik faturası"`

### Qwen3.5-9B-UD-Q4_K_XL × json — 8/50

- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 2}}`
- `cok-06` (çok tool): contact_save: 'phone' boş olamaz; contact_save beklenirken çağrı üretilmedi — çıktı: `contact_save --name Veli --phone 05555555555`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:05:00Z", "message": "Hatırlatıcı oluşturuldu."}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi", "phone": "555-0123"}}`
- `yok-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `ser-03` (serbest metin): note_create beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {"name": "Ali"}}`
