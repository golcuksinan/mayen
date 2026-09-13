# Faz 0 — çağrı biçimi ölçümü

> **Sonradan değişti (P11, P13, P14).** Bu rapor koşulduğu andaki araçla üretildi. O
> zamandan beri: CLI grameri artık argüman değerlerinde `<` kabul etmiyor; §17.1'in
> üçüncü halüsinasyon sayacı ("desteksiz sayı") artık ölçülüyor ve raporun bir sütunu;
> altın kümede `tek-04` liste kodlamasını sınayacak biçimde yeniden yazıldı (küme hâlâ 50
> senaryo). Buradaki sayılar geçerliliğini korur ama yeni bir koşuyla birebir
> karşılaştırılmaz.

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 50 | 94% | 94% | 0 | 0 | 0 | 21 | 0.28 |
| Qwen3.6-35B-A3B-IQ4_XS × json | 50 | 92% | 94% | 0 | 0 | 0 | 27 | 0.32 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json | 100% | 100% | 43% | 100% | 100% | 100% |

## Ölçülmeyen

§17.1'in üçüncü halüsinasyon sayacı — tool sonucunda bulunmayan bir bilgiyi yanıtta iddia etme — bu koşuda **ölçülmedi**: tool'un çalışıp sonucun modele geri beslenmesini, yani ajan döngüsünü (§8.2, P8) gerektiriyor.

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli — 5/50

- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target <cihaz_adı>`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name Yeni Kişi`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken '"Anneni ara ve doğum gününü kutla."' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:05:00Z --message "Anneni ara ve doğum gününü kutla."`

### Qwen3.6-35B-A3B-IQ4_XS × json — 6/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "default_device"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`
