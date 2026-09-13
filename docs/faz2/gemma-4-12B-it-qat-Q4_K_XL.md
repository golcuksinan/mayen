# Faz 0 — çağrı biçimi ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gemma-4-12B-it-qat-Q4_K_XL × cli | 50 | 96% | 88% | 0 | 0 | 0 | 29 | 0.45 |
| gemma-4-12B-it-qat-Q4_K_XL × json | 50 | 92% | 94% | 0 | 0 | 0 | 23 | 0.38 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| gemma-4-12B-it-qat-Q4_K_XL × cli | 93% | 100% | 86% | 100% | 100% | 100% |
| gemma-4-12B-it-qat-Q4_K_XL × json | 93% | 83% | 71% | 100% | 100% | 100% |

## Ölçülmeyen

§17.1'in üçüncü halüsinasyon sayacı — tool sonucunda bulunmayan bir bilgiyi yanıtta iddia etme — bu koşuda **ölçülmedi**: tool'un çalışıp sonucun modele geri beslenmesini, yani ajan döngüsünü (§8.2, P8) gerektiriyor.

## Başarısız senaryolar

### gemma-4-12B-it-qat-Q4_K_XL × cli — 6/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayarı' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayarı`
- `cok-01` (çok tool): name: 'Ali' beklenirken "Ali<tool> <tool> note_createon_body Ali'yi akşam arayacağım." geldi — çıktı: `<tool> contact_get --name Ali<tool> <tool> note_createon_body Ali'yi akşam arayacağım.`
- `cok-04` (çok tool): day: '4' beklenirken '4111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111' geldi — çıktı: `<tool> course_schedule --day 4111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111`
- `cok-06` (çok tool): name: 'Veli' beklenirken 'Veli <tool> task_create' geldi; phone fazladan verildi — çıktı: `<tool> contact_save --name Veli <tool> task_create --phone 0500000000000000000000000000000000000000000000000000000000000`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name "Yeni Kişi"`

### gemma-4-12B-it-qat-Q4_K_XL × json — 6/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayarı' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayarı"}}`
- `tek-11` (tek tool): day fazladan verildi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`
