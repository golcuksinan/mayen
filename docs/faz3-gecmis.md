# Faz 0 — çağrı biçimi ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | desteksiz sayı (n) | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | 10 | 90% | 100% | 0 | 0 | 0 (3) | 0 | 16 | 0.71 |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | 10 | 90% | 100% | 0 | 0 | 0 (3) | 0 | 16 | 0.65 |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | 10 | 90% | 100% | 0 | 0 | 0 (3) | 0 | 26 | 0.90 |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | 10 | 90% | 100% | 0 | 0 | 0 (3) | 0 | 26 | 0.86 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | 83% | — | — | 100% | 100% | 100% |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | 83% | — | — | 100% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) | — | 80% (5) | 100% (5) |
| Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) | — | 80% (5) | 100% (5) |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Başarısız senaryolar

### Qwen3.6-27B-IQ4_XS × cli × geçmiş(izli) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message Bir şey yapman gerekiyor!`

### Qwen3.6-27B-IQ4_XS × cli × geçmiş(izsiz) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message Bir şey yapman gerekiyor!`

### Qwen3.6-27B-IQ4_XS × json × geçmiş(izli) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "Bir şey yapman gerekiyor!"}}`

### Qwen3.6-27B-IQ4_XS × json × geçmiş(izsiz) — 1/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "Bir şey yapman gerekiyor!"}}`
