# Faz 0 — çağrı biçimi ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-27B-IQ4_XS × cli | 50 | 94% | 94% | 0 | 0 | 0 | 21 | 0.64 |
| Qwen3.6-27B-IQ4_XS × json | 50 | 86% | 89% | 0 | 0 | 1 | 30 | 0.85 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-27B-IQ4_XS × cli | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json | 100% | 100% | 0% | 100% | 100% | 100% |

## Ölçülmeyen

§17.1'in üçüncü halüsinasyon sayacı — tool sonucunda bulunmayan bir bilgiyi yanıtta iddia etme — bu koşuda **ölçülmedi**: tool'un çalışıp sonucun modele geri beslenmesini, yani ajan döngüsünü (§8.2, P8) gerektiriyor.

## Başarısız senaryolar

### Qwen3.6-27B-IQ4_XS × cli — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city Ankara`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-06` (eksik argüman): düz metin beklenirken contact_delete çağrıldı — çıktı: `<tool> contact_delete --name Lütfen silmek istediğiniz kişinin adını belirtin.`

### Qwen3.6-27B-IQ4_XS × json — 11/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "desktop"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-04` (çok tool): day: '4' beklenirken '5' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 5}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:05:00Z", "message": "Hatırlatıcı"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `eks-07` (eksik argüman): contact_save: 'phone' boş olamaz; düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`
