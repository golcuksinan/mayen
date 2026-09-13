# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen3.8-27B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.699999988079071, `top_k`=20, `top_p`=0.800000011920929, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=1.5, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Önek

Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi** olduğu sonucu değiştirir (P27):

- **ölçüm öneği** — `docs/faz2-olcum.md`'den beri kullanılan dizi: çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]` bloğu ve olgular **yok**.
- **üretim öneği** — `turn/runner.py`'nin modele gerçekten gönderdiği dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.

Rol metni: `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × onay × üretim öneği | 8 | 100% [68%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 15 | 0.80 | 0.97 |
| Qwen3.8-27B-IQ4_XS × json × onay × üretim öneği | 8 | 100% [68%–100%] | 83% | — | 0 | 0 | 0 (0) | 0 | 0 | 23 | 0.75 | 1.01 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × onay × üretim öneği | 100% | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × json × onay × üretim öneği | 100% | — | — | 100% | — | — |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × onay × üretim öneği | 100% (2) | 100% (6) | — |
| Qwen3.8-27B-IQ4_XS × json × onay × üretim öneği | 100% (2) | 100% (6) | — |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.8-27B-IQ4_XS × cli × onay × üretim öneği**: geçmişsiz ~50 jeton (%0.3), kısa geçmiş ~80 jeton (%0.5)
- **Qwen3.8-27B-IQ4_XS × json × onay × üretim öneği**: geçmişsiz ~50 jeton (%0.3), kısa geçmiş ~80 jeton (%0.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × onay × üretim öneği** — 2 yanıt:

- `ony-05`: `Tamam, notu silmedim. Başka bir şey lazım mı?`
- `ony-06`: `Tamam, uyandırma işlemini iptal ediyorum. Başka bir şey yapmamı ister misin?`

**Qwen3.8-27B-IQ4_XS × json × onay × üretim öneği** — 2 yanıt:

- `ony-05`: `Tamam, notu silmedim. Başka bir şey lazım mı?`
- `ony-06`: `Tamam, uyandırma işlemini iptal ediyorum. Başka bir şey yapmamı ister misin?`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × onay × üretim öneği — 0/8

Yok.

### Qwen3.8-27B-IQ4_XS × json × onay × üretim öneği — 1/8

- `ony-03` (tek tool): phone: '0534 222 33 44' beklenirken '05342223344' geldi — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Kerem", "phone": "05342223344"}}`

---

## Okuma (2026-08-15)

**Soru:** `docs/faz6-bellek.md`'de `bel-11` çağrı yerine düz metinle izin istedi
("Onaylıyor musun?"). §10'un onay akışını **kod** yürütüyor (Kural 5), yani model çağrıyı
yazmazsa akış hiç başlamıyor. Bilinmeyen şey, kullanıcı izni verdiğinde ikinci turda ne
olduğuydu — tur tamamen mi kayboluyor, yoksa çağrı gecikmeyle mi geliyor.

**Cevap: ikinci turda çağrı geliyor.** Sekiz senaryonun tamamı iki biçimde de doğru
(%100 [68–100], n=8).

- `ony-01..04` — izin verildikten sonra (`Evet.`, `Tamam, sil.`, `Olur, ekle.`) model
  doğru tool'u doğru argümanlarla çağırdı; argümanları geçmişten okudu.
- `ony-05/06` — izin **verilmedi**; model çağrı yazmadı ve reddi doğru anladı. Negatif
  kontrol tutuyor, yani sonuç "her onaydan sonra çağır" eğiliminin ürünü değil.
- `ony-07/08` — geçmişsiz, doğrudan istek: model **düz metinle izin istemeden** çağırdı.

**Yani `bel-11` genel bir davranış değil.** Aynı tool (`wake_on_lan`), geçmişsiz sorulunca
doğrudan çağrılıyor; izin sorusu yalnızca özet + uzun pencere bağlamında çıktı. Maliyeti
de sanıldığı kadar büyük değil: **iş kaybolmuyor, bir tur harcanıyor.**

**Bunu "sorun yok" diye okumak yanlış olur** (Kural 14): n=8 ve aralık [%68–%100]; ayrıca
üretimde o fazladan tur, kullanıcının ikinci kez konuşmasını gerektiriyor ve sesli bir
asistanda bunun bedeli metinden yüksek. `config/rol-aday.txt`'nin üçüncü cümlesi
("izni sistem soracak") tam olarak bunu hedefliyor ve `docs/faz6-rol.md`'de ölçüldü.

**Tek düşen satır bir biçim farkı:** `ony-03`, JSON'da telefonu `05342223344` diye
boşluksuz yazdı. Bu onayla ilgili değil — argüman sadakati ve JSON tarafında görülüyor.
