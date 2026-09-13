# Faz 0 — çağrı biçimi ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

## Toplam

| koşu | n | tool doğruluğu | argüman doğruluğu | uydurulan tool | uydurulan argüman | desteksiz sayı (n) | düzeltme turu | ort. token | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | 10 | 80% | 57% | 0 | 0 | 0 (3) | 0 | 18 | 0.69 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | 10 | 80% | 71% | 0 | 0 | 0 (3) | 0 | 17 | 0.62 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | 10 | 80% | 100% | 0 | 0 | 0 (3) | 0 | 26 | 0.77 |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | 10 | 70% | 100% | 0 | 0 | 0 (3) | 0 | 27 | 0.70 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | 83% | — | — | 50% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | 83% | — | — | 0% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) | — | 80% (5) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) | — | 60% (5) | 80% (5) |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izli) — 5/10

- `gec-01` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-02` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city İzmir --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message on saniye sonra bir şey yapman gerekiyor`
- `gec-09` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × geçmiş(izsiz) — 4/10

- `gec-02` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city İzmir --fields temperature,condition`
- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:00:10Z --message on saniye sonra bir şey yapman gerekiyor`
- `gec-09` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izli) — 2/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × geçmiş(izsiz) — 3/10

- `gec-04` (tek tool): task_list beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:10Z", "message": "On saniye sonra bir şey yapman g`
- `gec-05` (tool gerekmez): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {}}`
- `gec-10` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`
