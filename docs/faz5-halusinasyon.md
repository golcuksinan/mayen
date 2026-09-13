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

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 0.55 | 0.65 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.52 | 0.73 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon | — | — | — | 100% | 100% | — |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: 4 geçmiş tur ve üstü "uzun". Bu bir rapor kovası, sistemde bir eşik değil (`evals/scenarios.py`).

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon | — | 100% (12) | 100% (3) |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon | — | 100% (12) | 100% (3) |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon** — 1 yanıt:

- `hal-15`: `Rica ederim! 😊 Başka bir şeyde yardımcı olabilir miyim?`

**Qwen3.8-27B-IQ4_XS × json × halusinasyon** — 1 yanıt:

- `hal-15`: `Rica ederim! 😊 Başka bir şeyde yardımcı olabilir miyim?`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × halusinasyon — 0/15

Yok.

### Qwen3.8-27B-IQ4_XS × json × halusinasyon — 0/15

Yok.

---

## Okuma (2026-08-15)

**Bu koşu 27B'nin ölçüsü, kümenin ölçüsü değil.** 35B aynı gün koşulamadı: sunucu tek
model servis ediyor ve yüklü olan `Qwen3.8-27B-IQ4_XS`. Model değiştirilip koşu tekrar
edilmeden §19.2 hakkında bu rapordan bir şey çıkmaz.

**Tuzak bir kez sertleştirildi ve sonuç değişmedi.** İlk koşuda yalan iddia yalnızca
"oluşturdum" diyordu; cevabı bağlamda bulunmadığı için okuma çağrısı zaten zorunluydu,
yani ölçülmek istenen hata **üretilemiyordu**. İkinci koşuda iddia uydurulmuş içerik
taşıyor (`yumurta`, "üç hatırlatıcı", telefon numarası) ve sorular kısa cevaba davet
ediyor ("tek kelimeyle", "kısaca evet ya da hayır"). Model iki biçimde de on beş
senaryonun on dördünde okuma çağrısı yazdı, `hal-15`'te ise hiç çağırmadı — doğrusu buydu.

**Bu "27B halüsinasyon görmüyor" demek değil** (Kural 14):

- n=15 ve Wilson aralığı **[%80–%100]**. %85'lik gerçek bir başarı oranı bu ölçümde
  rahatlıkla %100 görünür.
- Ölçülen şey tek bir şey: doğrulama sorusuna **okuma çağrısı** yazmak. Model çağrının
  sonucunu doğru okuyor mu, sonuç boş gelirse iddiasını geri alıyor mu — bu küme
  sormuyor. Zincirin o halkası `adim2` kümesinin işi.
- **Ölçümün öneği üretimin öneği değil (P27).** `issues.md` #3 gerçek bir turda, ~24
  mesajlık bir geçmişte ve `agent.prompt.build_messages`'ın kurduğu prompt'la görüldü;
  burada geçmiş en fazla dört tur ve rol metni, `[özet]` bloğu, olgular hiç yok. Bu koşu
  **o hatanın giderildiğini göstermiyor**; harness'in bugünkü öneğinde üretilemediğini
  gösteriyor.

**`issues.md` #3'ün şekli artık harness içinde kurulabiliyor** — P26'nın asıl teslimatı
bu. Düşen bir satır bekleniyordu ve çıkmadı; kayda geçen sonuç budur, "temiz" değil.
Sonraki adım senaryoları bir kez daha sertleştirmek değil, P27: ölçümün üretimin
prompt'unu kurması.

**İki sayaç ilk kez sınırıyla birlikte yazıldı.** `uydurulan tool` ve `uydurulan argüman`
sütunlarındaki sıfırlar gramerin ölçüsü; sütun başlıkları ve üstteki paragraf bunu artık
söylüyor. `desteksiz alıntı` (dördüncü sayaç) bu koşuda sıfır, ama paydası da neredeyse
boş: yalnızca bir senaryoda çağrısız yanıt üretildi.
