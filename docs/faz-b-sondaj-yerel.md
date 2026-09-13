# Sondaj: modelin kendi tool-calling şablonu

Tarih: 2026-08-16. Model: `Qwen3.8-27B-IQ4_XS`, `presence_penalty` 1.5, açgözlü.
Betik: **scratchpad'de**, üretime ve `evals/`e hiçbir şey yazılmadı. Yön alınırsa
`evals/`e taşınması gerekir (dört kapı + `--onek` ayrımı).

## Neden koşuldu

Faz A ve Faz B/1 boyunca yapılan iş — rol metni turları, `[araç]` izi (dört kez etkisiz),
beş geçmiş biçimi — modelin sohbet şablonunda **hazır duran** bir ayrımı prompt'la
yeniden icat etme çabasıydı: *bu veri bir tool'dan geldi, senin bilgin değil.* Yaygın
harness'lerde bu ayrım rollerde duruyor (`assistant.tool_calls` + `tool` rolü), promptta
değil. Bizde durmuyor, çünkü çağrıyı GBNF ile ham metin olarak üretiyoruz.

Bunu bugüne kadar kapalı tutan gerekçe **"ilk ses bütçesi"ydi** (§6'nın "dallanma ilk
token'da belli olmalıdır" kısıtı). O gerekçe 2026-08-16'da düştü: **§19 madde 4 —
ilk ses gecikmesi hedef değeri — açık**, yani korunan bütçenin bir sayısı hiç olmadı, ve
onu belirleyici yapan Faz 0 ölçümü de artık berabere (0.22/0.22). Sahibin tartısı:
1 saniyelik gecikme ile uydurma cevap + günlerce ölçüm aynı kefeye konmaz.

## Ne yapıldı

Önek `evals.replay.build_prefix` ile **üretimin kodundan** kuruldu. Üç kol, aynı geçmiş,
aynı örnekleme:

1. **bugünkü önek, gramersiz** — akıl sağlığı kolu. Gerçek referans `replay`'in `tam`
   satırı (gramerli, iki turda da çağrısız).
2. **yerel tool-calling** — katalog **ve** çağrı sözdizimi sistem promptundan çıktı,
   tanımlar `tools` alanında JSON şema olarak gitti; çağrıyı sunucu ayrıştırdı. Sistem
   promptunda kalan: rol metni + dil kuralı.
3. **yerel + `yer-tutucu` geçmiş** — 2'nin üstüne Faz B/1'in kazanan geçmiş biçimi.

Şema deftere göre üretiliyor (`ArgType` → JSON tip), ikinci bir elle yazılmış liste yok.

## Sonuç

| biçim | 91 `bugün derslerim neler` | 118 `sesi kıssana biraz` |
|---|---|---|
| bugün (gramerli, `replay`) | — | — |
| yerel tool-calling | **`course_schedule`** | — |
| yerel + `yer-tutucu` | `date_time` | **`volume`** |

İlk jeton, altı koşunun hepsi: **2.13 – 2.66 s**, kollar arasında ayrım yok.

## Okuma

1. **Yerel biçim tek başına yetmiyor, ve bu bulgunun kendisi değerli.** 91'i çeviriyor,
   118'i çeviremiyor. Yani "yapılandırılmış çağrıya geçersek Faz B gereksizleşir"
   **yanlış**. Geçmişteki asistan cevabının veriyi taşıması, çağrı arayüzünden bağımsız
   bir sorun — çünkü o cevap hâlâ düz metin olarak orada duruyor.
2. **İkisi birbirinin yerine değil, yanına geçiyor.** `yer-tutucu` eklenince 118 çevriliyor.
   91'de çağrılan tool `date_time` — tek turluk ölçümde "yanlış tool" görünüyor ama ajan
   döngüsünde iki adımlı bir yolun ilk adımı olabilir; **bu ölçüm onu ayırt edemez** ve
   öyle okunmamalı.
3. **Gecikme bir engel değil, ve artık sayısı var.** Kollar arasında ayrım yok. Bu sayılar
   `evals`'ın 0.22'siyle karşılaştırılamaz: burada önbellek soğuk ve önek ~2900 token,
   orada önek paylaşımlı. Söylediği tek şey yeterli — **yerel biçim ölçülebilir bir
   gecikme bedeli getirmiyor.** §19 madde 4 hâlâ açık; kapatacak olan sahip.
4. **Asıl deney yapılmadı ve yapılamaz:** geçmişte tool **sonuçları yok**. Üretim onları
   hiç saklamadı (`turn/runner.py:called_line`, yalnızca ad — gerekçesi "sonuç ertesi tur
   bayat"). Yaygın çözümün asıl kaldıracı tam da sonucun `tool` rolünde durması ve cevabın
   ondan ayrılması. Bu sondaj o düzenin **yarısını** ölçtü. Tam hâli bir üretim
   değişikliği ister; ve ancak o zaman "cevabı geçmişten silmek" gerekli mi diye sorulabilir.

## Sıradaki iş, eğer bu yön alınırsa

1. `CallFormat.YEREL` — `agent/calls.py` ayrıştırma, `adapters/llamacpp.py` `tools` alanı,
   `tools/schema.py` defterden şema. Seçen tek satır yine `main.py:CALL_FORMAT`.
2. **Tool sonucunu geçmişe yaz** (`turn/runner.py` + `data/repositories/conversation.py`
   `Role`) — sondajın ölçemediği yarı. `called_line`'ın gerekçesi burada yeniden açılıyor:
   bayatlık artık rolde işaretli olduğu için "saklama" kararı yeniden değerlendirilebilir.
3. Kabul kapısı **oturum ölçümü** (`evals/session.py`, taban 1/15, ilk atlama 9. tur) —
   iki turluk sondaj bir yön gösterir, kapatmaz.
4. İlk sesi `evals`'ın kendi koşusunda, paylaşımlı önekle ölç ve §19 madde 4'e taşı.
