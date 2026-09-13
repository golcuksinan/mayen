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

Rol metni: `config/rol.txt` (içeriği sonucu etkiler).

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği | 17 | 94% [73%–99%] | 100% | — | 0 | 0 | 0 (6) | 0 | 0 | 11 | 0.72 | 0.87 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği | 17 | 100% [82%–100%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 18 | 0.76 | 0.97 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği | 88% | — | — | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği | 100% | — | — | 100% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği | — | 100% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği | — | 100% (11) | 100% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği** — 8 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `Üniversitede okuduğunu biliyorum, ama hangi üniversite olduğunu kaydetmemişim.`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc demiştin.`
- `bel-11`: `Evet, ev-pc cihazını uyandırayım. Onaylıyor musun?`
- `bel-12`: `Evet, pazartesi günleri saat onda.`
- `bel-17`: `Bende kayıtlı değil.`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği** — 6 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `Üniversitede okuduğunu biliyorum, ama hangi üniversite olduğunu kaydetmemişim.`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc`
- `bel-12`: `Evet, pazartesi günleri saat onda.`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği — 1/17

- `bel-11` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `Evet, ev-pc cihazını uyandırayım. Onaylıyor musun?`

### Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği — 0/17

Yok.

---

## Okuma (2026-08-15)

**Bu, ölçümün ilk kez üretimin öneğiyle koştuğu rapor.** `docs/faz2-olcum.md`'den bugüne
kadar rol metni, `[özet]` bloğu ve olgular ölçüme hiç girmemişti; P20'nin bütün bellek
katmanı harness'in dışındaydı. Burada üçü de var ve dizi `agent.prompt.build_messages`'tan
geliyor — ikinci bir kopya değil, üretimin kendi fonksiyonu.

### Bulgu 1: model onayı **düz metinle** istiyor ve tur boşa dönüyor

`bel-11` — "Ev bilgisayarımı uyandırır mısın?" → `Evet, ev-pc cihazını uyandırayım.
Onaylıyor musun?` Hiç `wake_on_lan` çağrılmadı.

Bu, kümenin tek tekrar eden düşüşü ve **rol metniyle birlikte geldi**: ölçüm öneğiyle
koşulan hiçbir raporda görülmedi. `config/rol.txt`'de onay istemesini söyleyen bir cümle
de yok.

Neden önemli: onay §10'un akışı ve **kod** yürütüyor (Kural 5 — onay serbest metinden
anahtar kelimeyle çıkarılmaz). Model çağrıyı yazmayıp kullanıcıya sorduğunda onay akışı
hiç başlamıyor; tur, hiçbir şey yapmadan bir soruyla kapanıyor. Kullanıcı "evet" derse
ikinci turda ne olacağı bu kümede ölçülmedi — `adim2`'nin sorusu ve orada ölçülmeli.

**Bu bir düzeltme önerisi değil, bir ölçüm bulgusudur.** Rol metnini değiştirmek de bir
prompt değişikliğidir ve §17.1 prompt değişikliğini değerlendirme kapısına bağlıyor: önce
ölçülür, sonra değişir.

### Bulgu 2: bellek bloklarının kendisi bu modelde sorun çıkarmadı

Beş şeklin dördü temiz geçti: özetten okuma (`bel-01..03`), özet ↔ pencere çelişkisi
(`bel-04..06` — model "Ankara" diyor, özetteki İzmir'i değil), budanmış turun bilgisi
(`bel-10..12`, `ev-pc` özetten okunuyor), bayat olgu (`bel-07..09` — üçünde de bayat
satırı okuyup yine tool çağırdı).

**Bu "bellek katmanı temiz" demek değil** (Kural 14): n=17, aralık CLI'de [%73–%99]. Ve
ölçülen şey **verilen** blokların okunması; blokların *üretimi* — budama, özetleme, olgu
seçimi — hâlâ ölçüm dışında ve bilerek öyle (bir LLM çağrısı ve bir veritabanı, ölçümü
belirlenimsiz yapardı).

### Bulgu 3: kova ilk kez gerçek boyunu yazıyor

Bağlam kovası tur sayısından **jetona** geçti. "Uzun geçmiş" bu kümede ~574 jeton, yani
`n_ctx`'in **%3.5'i**; eski kümelerdeki "uzun geçmiş" ise ~%0.4'lük bir bloktu ve rapor
bunu okuyana hiç söylemiyordu. Üretimdeki hata ~24 mesajda görülmüştü; bu küme 20 turluk
pencerelerle oraya yaklaşıyor ama hâlâ altında.

### İki senaryo ilk koşudan sonra düzeltildi — ikisi de ölçümün hatasıydı

Ham hâlleri `scratchpad`'de duruyor; ikisi de modelin değil kümenin kusuruydu:

1. `bel-15` — model `yarın`ı `Yarın` diye yazdı ve karşılaştırma birebir olduğu için
   (Türkçe'de harf katlaması yanlış çalışır, o yüzden hiç yapılmıyor) argüman hatası
   sayıldı. Senaryonun cümlesi büyük harfle başlayacak şekilde düzeltildi: ölçülen şey
   modelin değil, cümlenin ilk harfiydi.
2. `bel-17` — model `fact_list` çağırdı ve beklenti yalnızca `note_search`'ü kabul
   ediyordu. P27'nin kendi tanımı "okuma tool'u çağırmak da doğru" diyor ve olgu defterine
   bakmak tam olarak odur; eksik olan beklentiydi.

**Sertleştirme değil, artefakt temizliği** — ayrımı yazıyorum çünkü ikisi kolayca
karışır: P26'da tuzağı model geçtiği için sertleştirmiştik ve bu rapor onu tekrar
etmiyor. Burada düzeltilen şey, modelin doğrusunu yanlış raporlayan iki satırdı.
