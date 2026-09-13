# Faz 0 — çağrı biçimi ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B-Q8_0 × cli | 50 | 84% | 71% | 0 | 0 | 0 | 22 | 0.34 |
| Qwen3.5-9B-Q8_0 × json | 50 | 92% | 97% | 0 | 0 | 1 | 26 | 0.39 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.5-9B-Q8_0 × cli | 93% | 67% | 86% | 100% | 75% | 71% |
| Qwen3.5-9B-Q8_0 × json | 100% | 83% | 71% | 88% | 100% | 100% |

## Ölçülmeyen

§17.1'in üçüncü halüsinasyon sayacı — tool sonucunda bulunmayan bir bilgiyi yanıtta iddia etme — bu koşuda **ölçülmedi**: tool'un çalışıp sonucun modele geri beslenmesini, yani ajan döngüsünü (§8.2, P8) gerektiriyor.

## Başarısız senaryolar

### Qwen3.5-9B-Q8_0 × cli — 16/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü_bilgisayarı' geldi — çıktı: `<tool> wake_on_lan --target masaüstü_bilgisayarı`
- `tek-10` (tek tool): task_list beklenirken çağrı üretilmedi — çıktı: `task_list`
- `cok-01` (çok tool): contact_get beklenirken çağrı üretilmedi — çıktı: `contact_get --name Ali`
- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> task_cancel --id 2`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 05555555555 <tool> task_create –due 2026-08-10T09:00:00Z –message Veli'yi aramam`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `ayr-01` (ayırt etme): query: 'alışveriş' beklenirken '"alışveriş"' geldi — çıktı: `<tool> note_search --query "alışveriş"`
- `ayr-02` (ayırt etme): body: 'Alışveriş' beklenirken '"Alışveriş"' geldi — çıktı: `<tool> note_create --body "Alışveriş"`
- `ayr-04` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `contact_get --name Ayşe`
- `ayr-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `task_list`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'süt, ekmek ve yumurta almayı unutma. </tool>' geldi — çıktı: `<tool> note_create --body süt, ekmek ve yumurta almayı unutma. </tool>`
- `ser-02` (serbest metin): body: '--önemli-- yarın erken kalk' beklenirken '"--önemli-- yarın erken kalk." </tool>' geldi — çıktı: `<tool> note_create --body "--önemli-- yarın erken kalk." </tool>`
- `ser-03` (serbest metin): note_create beklenirken çağrı üretilmedi — çıktı: `contact_get --name Ali`
- `ser-05` (serbest metin): task_create beklenirken çağrı üretilmedi — çıktı: `contact_get --name annem`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken '"kütüphane kitabını ayın on beşine kadar geri ver." </tool>' geldi — çıktı: `<tool> note_create --body "kütüphane kitabını ayın on beşine kadar geri ver." </tool>`
- `ser-07` (serbest metin): query: 'elektrik faturası' beklenirken '"elektrik faturası"' geldi — çıktı: `<tool> note_search --query "elektrik faturası"`

### Qwen3.5-9B-Q8_0 × json — 5/50

- `cok-03` (çok tool): task_list beklenirken task_cancel çağrıldı — çıktı: `<tool> {"name": "task_cancel", "arguments": {"id": 2}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:05:00Z", "message": "Bana bir hatırlatıcı kur."}}`
- `yok-05` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:00Z", "message": "Annemi ara ve doğum gününü kutla`
