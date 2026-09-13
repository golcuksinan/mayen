# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.699999988079071, `top_k`=20, `top_p`=0.800000011920929, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=1.5, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Önek

Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi** olduğu sonucu değiştirir (P27):

- **ölçüm öneği** — `docs/faz2-olcum.md`'den beri kullanılan dizi: çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]` bloğu ve olgular **yok**.
- **üretim öneği** — `turn/runner.py`'nin modele gerçekten gönderdiği dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.

Rol metni: `config/rol.txt`, `config/rol-aday.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol) | 50 | 96% [87%–99%] | 88% | — | 0 | 0 | 2 (5) | 2 | 0 | 15 | 0.21 | 0.34 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday) | 50 | 96% [87%–99%] | 88% | — | 0 | 0 | 1 (5) | 0 | 0 | 14 | 0.21 | 0.33 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 29 | 0.09 | 0.33 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 25 | 0.09 | 0.29 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | 15 | 33% [15%–58%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 14 | 0.82 | 0.94 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-aday) | 15 | 40% [20%–64%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 14 | 0.86 | 0.98 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 17 | 94% [73%–99%] | 80% | — | 0 | 0 | 0 (7) | 0 | 0 | 11 | 1.09 | 1.19 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-aday) | 17 | 94% [73%–99%] | 90% | — | 0 | 0 | 0 (7) | 0 | 0 | 12 | 1.13 | 1.23 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol) | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 0 (4) | 0 | 0 | 21 | 0.18 | 0.36 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol-aday) | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 0 (4) | 0 | 0 | 21 | 0.19 | 0.36 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 25 | 0.09 | 0.30 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 28 | 0.09 | 0.32 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | 15 | 53% [30%–75%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.82 | 0.98 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-aday) | 15 | 67% [42%–85%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 17 | 0.83 | 0.98 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 17 | 100% [82%–100%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 20 | 1.09 | 1.26 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday) | 16 | 88% [64%–97%] | 100% | — | 0 | 0 | 0 (6) | 4 | 0 | 20 | 1.07 | 1.25 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol) | 100% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday) | 100% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 29% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-aday) | — | — | — | 100% | 36% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 100% | — | — | 83% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-aday) | 100% | — | — | 83% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol) | 93% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol-aday) | 93% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 50% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-aday) | — | — | — | 100% | 64% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 100% | — | — | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday) | 100% | — | — | 67% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol) | 96% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday) | 96% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | 33% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-aday) | — | 40% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | — | 100% (11) | 83% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-aday) | — | 100% (11) | 83% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol) | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol-aday) | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | 53% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-aday) | — | 67% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | — | 100% (11) | 100% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday) | — | 91% (11) | 80% (5) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-aday)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-aday)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol-aday)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-aday)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Ölçülemeyen senaryolar

Servis iki denemede de düştü. Bu satırlar **hiçbir doğruluk paydasına girmiyor**: modelin yanlışı değil, ölçümün eksiği. Yanlış cevap sayılsalardı model servisin kopmasından sorumlu tutulurdu; hiç yazılmasalardı payda sessizce küçülür ve rapor eksikliğini gizlerdi (Kural 13, Kural 14).

**Bir sayı burada görünüyorsa o koşu eksiktir ve öyle okunmalıdır.**

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday)** — 1/17:

- `bel-11`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: Server disconnected without sending a response.


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol)** — desteksiz sayı geçen senaryolar:

- `tek-05`: `30` — yanıt: `Bilgisayarın belleği oldukça rahat durumda. Toplam 32 GB belleğinden sadece 9.4 GB'ı kullanılıyor. Yani yaklaşık %30'luk bir kullanım var, sistemde bolca boş alan kalmış.`
- `tek-10`: `6` — yanıt: `Sende bir hatırlatıcı var. İlaç için yarın sabah saat 6'da uyarılacaksın.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday)** — desteksiz sayı geçen senaryolar:

- `tek-10`: `6` — yanıt: `Bir bekleyen hatırlatıcın var. İlaç için yarın sabah saat 6'da uyarılacaksın.`

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol)** — desteksiz alıntı geçen senaryolar:

- `yok-03`: `Nasıl gidiyor?`, `Yavaş ama emin adımlarla`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday)** — desteksiz alıntı geçen senaryolar:

- `bel-17`: `name`, `contact_get`, `arguments`, `--name`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol)** — 16 yanıt:

- `eks-01`: `Hangi şehir için hava durumunu öğrenmek istersin?`
- `eks-02`: `Hangi notu silmek istersin? Numarasını söylersen hemen silebilirim.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin?`
- `eks-04`: `Ne zaman ve neyi hatırlamamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Kimin numarasını ekleyelim?`
- `yok-01`: `Rica ederim. Başka bir işin varsa buradayım.`
- `yok-02`: `İyiyim, teşekkür ederim. Sen nasılsın?`
- `yok-03`: `Elbette. Bir adamın biri ona "Nasıl gidiyor?" diye sormuş. Adam da "Yavaş ama emin adımlarla" demiş.`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir isteğin olursa buradayım.`
- `yok-06`: `Ben Mayen. Senin kişisel sesli asistanınım. Rehberindeki kişileri yönetebilir, notlar oluşturup arayabilirim, ders programını ve görevlerini kontrol edebilirim. Ayrıca hava durumunu sorgulayabilir mak`
- `yok-07`: `Dört eder.`
- `yok-08`: `Hız ayarını değiştiremem, bu cihazın genel sesli yanıt ayarlarına bağlıdır. Telefonunun veya bilgisayarının sesli asistan ayarlarından okuma hızını düşürebilirsin. Başka bir konuda yardımcı olabilir m`
- `ayr-03`: `Ayşe'nin telefon numarasını da eklememi ister misin?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday)** — 16 yanıt:

- `eks-01`: `Hangi şehir için hava durumunu öğrenmek istersin?`
- `eks-02`: `Silinecek notun numarası nedir?`
- `eks-03`: `Hangi cihazı uyandırmamı istersin?`
- `eks-04`: `Ne zaman ve neyi hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Adı ve telefon numarası nedir?`
- `yok-01`: `Rica ederim. Başka bir işin varsa buradayım.`
- `yok-02`: `İyiyim, teşekkür ederim. Sen nasılsın?`
- `yok-03`: `Tabii, işte bir tane:  Matematik kitabı neden üzgün? Çünkü çok fazla problemi var.`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir isteğin olursa buradayım.`
- `yok-06`: `Ben Mayen. Rehberde kişi saklayıp silebilirim, not tutar ve aratırım, görev hatırlatıcı kurarım, ders programına bakarım, hava durumunu sorgularım, makine performansını kontrol ederim veya uzak cihazl`
- `yok-07`: `Dört eder.`
- `yok-08`: `Ben sesli okuma hızını doğrudan kontrol edemiyorum. Bu ayarı cihazının ses veya erişilebilirlik menüsünden yapabilirsin.`
- `ayr-03`: `Telefon numarası nedir?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol)** — 17 yanıt:

- `kon-01`: `İyi geceler, iyi uykular.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir işin var mı?`
- `kon-05`: `Evet, hava gerçekten iyiydi. Bugün hava durumu nasıl olsun istersin?`
- `kon-06`: `Temelde bilgisayarlar, elektrik sinyallerini kullanarak iki temel sayı sistemiyle, yani sıfır ve birlerle (ikili sistem) çalışır. Bu basit birimler, işlemci içindeki milyarlarca transistörün açılıp ka`
- `kon-07`: `Anladım, bazen her şey üst üste gelebiliyor. Sana nasıl yardımcı olabilirim? Bir not almamı, bir hatırlatıcı kurmamı veya sadece dinlememi ister misin?`
- `kon-09`: `Evet, bakabilirim. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderiyorum. Mesajın içeriğini de o bildirimde görürsün.`
- `kon-11`: `Evet, notların sadece seninle ilgili. Ben Mayen olarak onları yalnızca senin için saklıyorum ve başkalarıyla paylaşmıyorum. Gizliliğin benim için önemli. Başka bir sorun var mı?`
- `kon-12`: `Rehber, telefonunda veya cihazında kayıtlı olan kişilerin isim ve telefon numaralarını tuttuğun yerdir. İstersen buradan yeni bir kişi ekleyebilir, var olanların numarasını güncelleyebilir veya silebi`
- `kon-13`: `Tamam, sorun değil. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, başka bir sorun olursa buradayım. İyi günler!`
- `kon-15`: `Bugün saat kaç?`
- `kon-16`: `Harika haber.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an 9 Eylül 2026, saat 09:00. Günün nasıl geçiyor?`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. Belki biraz dinlenmek ya da sevdiğin bir şey yapmak daha iyi gelebilir.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday)** — 17 yanıt:

- `kon-01`: `İyi geceler, iyi uykular.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir işin var mı?`
- `kon-05`: `Evet, hava gerçekten iyiydi. Bugün nasıl olacak merak ediyorum.`
- `kon-06`: `Temelde bilgisayarlar, milyonlarca küçük anahtardan oluşan işlemcilerle çalışır. Bu anahtarlar açık veya kapalı durumdadır ve bu ikili sistem (1 ve 0) tüm verileri ve komutları temsil eder. İşlemci, b`
- `kon-07`: `Sorun değil, derin bir nefes al. Sana nasıl yardımcı olabilirim? Bir şey mi araştırmamı istersin yoksa sadece sohbet mi edelim?`
- `kon-09`: `Evet, bakabilirim. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderiyorum. Mesajın içeriğini de o bildirimde görürsün.`
- `kon-11`: `Evet, notların sadece seninle ilgili. Ben Mayen olarak onları yalnızca senin için saklıyorum ve başkalarıyla paylaşmıyorum.`
- `kon-12`: `Rehber, telefonunda veya cihazında kayıtlı olan kişilerin isim ve telefon numaralarını tuttuğun yerdir. İstersen buraya yeni kişiler ekleyebilir, var olanların bilgilerini güncelleyebilir veya silebil`
- `kon-13`: `Tamam, başka bir isteğin var mı?`
- `kon-14`: `Tamam, başka bir sorun olursa buradayım.`
- `kon-15`: `Bugün saat kaç? Piknik için hava durumunu kontrol edeyim.`
- `kon-16`: `Harika haber.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an 9 Eylül 2026, Cumartesi sabahı saat 09:00'da ilerliyoruz. Günün nasıl geçiyor?`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. Belki biraz dinlenmek ya da sevdiğin bir şey yapmak daha iyi gelebilir.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)** — 11 yanıt:

- `hal-03`: `3`
- `hal-04`: `Notu kontrol ediyorum.  <tool> note_search --query alışveriş listesi`
- `hal-06`: `Üç tane.`
- `hal-07`: `Rehberde Veli'nin numarası 0532 111 22 33 olarak kayıtlı.`
- `hal-08`: `Evet`
- `hal-10`: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-11`: `Evet, yarın sabah dokuzda toplantı hatırlatıcın aktif.`
- `hal-12`: `Evet, Veli'yi rehbere ekledim. Numarası 0532 111 22 33.`
- `hal-13`: `not_search --query kargoyu sor`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-aday)** — 10 yanıt:

- `hal-03`: `3`
- `hal-04`: `Notu kontrol ediyorum.  <tool> note_search --query alışveriş listesi`
- `hal-06`: `Üç tane.`
- `hal-07`: `Rehberde Veli için kayıtlı telefon numarasını göremiyorum. Lütfen numarasını tekrar söylersen ekleyebilirim.`
- `hal-08`: `Evet`
- `hal-10`: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-11`: `Evet, yarın sabah dokuzda toplantı hatırlatıcın aktif.`
- `hal-12`: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)** — 6 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu bilmiyorum.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini belirtmiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `ev-pc`
- `bel-17`: `Bilmiyorum, hatırlatmamı ister misin?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-aday)** — 6 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu henüz kaydetmedim. Söyleyebilir misin?`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `ev-pc`
- `bel-17`: `Rehberde anneni bulamadım. Adını ve doğum gününü kaydedeyim mi?`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol)** — 17 yanıt:

- `tek-01`: `Şu an saat 12:00.`
- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Hangi notu silmek istersin? Numarasını söylersen silebilirim.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin?`
- `eks-04`: `Ne zaman ve ne için hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylersen silebilirim.`
- `eks-07`: `Kimin numarasını ekleyelim?`
- `yok-01`: `Rica ederim. Başka bir işin varsa buradayım.`
- `yok-02`: `İyiyim, teşekkür ederim. Sen nasılsın?`
- `yok-03`: `Tabii, işte bir tane:  Matematik kitabı neden üzgün? Çünkü çok fazla problemi var.`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir isteğin olursa buradayım.`
- `yok-06`: `Ben Mayen. Kişi ve not yönetimi, görev hatırlatıcıları, hava durumu sorgulama, ders programı kontrolü gibi işleri yapabilirim.`
- `yok-07`: `Dört eder.`
- `yok-08`: `Ben bir sesli asistanım ama konuşma hızımı doğrudan ayarlayamıyorum. Bu ayarı cihazının ses veya erişilebilirlik menüsünden değiştirmen gerekebilir. Başka bir konuda yardımcı olabilir miyim?`
- `ayr-03`: `Ayşe'nin telefon numarası nedir?`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol-aday)** — 17 yanıt:

- `tek-01`: `Şu an saat 09:00.`
- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Silinecek notun numarası nedir?`
- `eks-03`: `Hangi cihazı uyandırmamı istersin?`
- `eks-04`: `Ne zaman ve neyi hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Kimin numarasını ekleyelim? Adı ve telefon numarası nedir?`
- `yok-01`: `Rica ederim. Başka bir işin varsa buradayım.`
- `yok-02`: `Merhaba! Teşekkürler, ben iyiyim. Sana nasıl yardımcı olabilirim?`
- `yok-03`: `Tabii, işte bir tane:  Neden bilgisayarlar asla üşümez? Çünkü Windows'ları var!`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir isteğin olursa buradayım.`
- `yok-06`: `Ben Mayen. Kişi ve not yönetimi, görev hatırlatıcıları, hava durumu sorgulama, ders programı görüntüleme ve sistem durumunu kontrol etme gibi işleri yapabilirim.`
- `yok-07`: `Dört eder.`
- `yok-08`: `Hız ayarını değiştiremem, bu cihazın veya uygulamanın kendi özelliği. Ama ben kısa ve net cevaplar veriyorum, böylece dinlemek daha rahat olabilir. Başka bir isteğin var mı?`
- `ayr-03`: `Ayşe'nin telefon numarası nedir?`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol)** — 18 yanıt:

- `kon-01`: `İyi geceler, iyi uykular.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir isteğin var mı?`
- `kon-05`: `Evet, hava gerçekten iyiydi. Bugün hava durumu nasıl olsun istersin?`
- `kon-06`: `Temelde bilgisayarlar elektrik sinyallerini kullanarak çalışır. İçindeki işlemci, milyonlarca küçük anahtarı (transistör) açıp kapatarak ikili kodla yani sıfır ve birlerle hesaplamalar yapar. Bu işlem`
- `kon-07`: `Anladım, bazen her şey üst üste gelebiliyor. Sana nasıl yardımcı olabilirim? Bir not alayım mı, görevlerini mi kontrol edelim yoksa sadece sohbet mi etmek istersin?`
- `kon-08`: `Üzgünüm ama sesimi ayarlayamıyorum. Sadece metin tabanlı bir asistanım.`
- `kon-09`: `Evet bakabil. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderiyorum. Mesajın içeriğini de o bildirimde görürsün.`
- `kon-11`: `Evet, notların sadece sana ait. Ben bir sesli asistanım ve verilerin dışarıya aktarılmaz.`
- `kon-12`: `Rehber, telefonunda veya cihazında kayıtlı olan kişilerin listesidir. Ad, telefon numarası gibi iletişim bilgilerini burada tutarsın. İstersen yeni bir kişi ekleyebilir, var olanları arayabilir veya s`
- `kon-13`: `Tamam, sorun değil. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, başka bir sorun olursa buradayım. İyi günler!`
- `kon-15`: `Bugün saat kaç?`
- `kon-16`: `Harika haber.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an 9 Eylül 2026, saat 12:00. Günün nasıl geçiyor?`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. İstersen ders programına bakıp ne kadar zamanın olduğunu görebiliriz ya da sadece sohbet edebiliriz.`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday)** — 18 yanıt:

- `kon-01`: `İyi geceler, iyi uykular.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir işin var mı?`
- `kon-05`: `Evet, hava gerçekten iyiydi. Bugün nasıl olacak merak ediyorum.`
- `kon-06`: `Temelde bilgisayarlar, elektrik sinyallerini kullanarak bilgiyi işler. İçindeki işlemci (CPU) milyonlarca küçük anahtarı açıp kapatarak 0 ve 1'lerden oluşan ikili kodlarla hesaplamalar yapar. Bu veril`
- `kon-07`: `Anladım, bazen her şey üst üste gelebiliyor. Sana nasıl yardımcı olabilirim? Bir not kaydetmemi ister misin, aklındaki fikirleri döküp düzenlememi mi istersin yoksa sadece dinlememi mi?`
- `kon-08`: `Üzgünüm ama sesimi ayarlayamıyorum. Sadece metin tabanlı bir asistanım.`
- `kon-09`: `Evet, bakabilirim. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderiyorum. Mesajın içeriğini de o bildirimde görürsün.`
- `kon-11`: `Evet, notların sadece sana ait. Ben Mayen, senin kişisel asistanınım ve verilerin dışarıya aktarılmaz.`
- `kon-12`: `Rehber, telefon numarası ve isim gibi kişisel iletişim bilgilerinin tutulduğu yerdir. İstersen oraya yeni bir kişi ekleyebilir, var olanları arayabilir veya silebilirim. Nasıl yardımcı olayım?`
- `kon-13`: `Tamam, sorun değil. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, başka bir sorun olursa buradayım.`
- `kon-15`: `Bugün saat kaçta hava durumu kontrol edelim?`
- `kon-16`: `Harika haber.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an 9 Eylül 2026, saat 12:00. Günün nasıl geçiyor?`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. İstersen hava durumuna bakayım, dışarı çıkmak ister misin? Yoksa sadece sohbet mi edelim?`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)** — 8 yanıt:

- `hal-03`: `3`
- `hal-04`: `Yanlış anladım, notu oluştururken sadece süt ve ekmek yazdın. Üçüncü bir kalemi yok.`
- `hal-10`: `Süt ve ekmek.`
- `hal-11`: `Evet, yarın sabah dokuzda toplantı hatırlatıcısı aktif.`
- `hal-12`: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-13`: `Notlarda kargo ile ilgili bir şey bulamadım. Daha önce başka bir not almış olabilir misin?`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-aday)** — 6 yanıt:

- `hal-03`: `Üç`
- `hal-07`: `Rehberde Veli için kayıtlı olan numara 0532 111 22 33.`
- `hal-08`: `Evet`
- `hal-11`: `Evet, yarın sabah dokuzdaki toplantı hatırlatıcısı hâlâ aktif.`
- `hal-14`: `Evet, kurdum. Akşam yedide hatırlatacağım.`
- `hal-15`: `Rica ederim, başka bir şey var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol)** — 7 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu henüz kaydetmedim. Hangi üniversitede olduğunu söylersen notlara ekleyebilirim.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `Makinenin adı ev-pc.`
- `bel-12`: `Hatırlamıyorum. Hatırlatıcıya eklememi ister misin?`
- `bel-17`: `Rehberde kayıtlı değil, numarasını verir misin?`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday)** — 5 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, henüz kaydetmedim. Hangi üniversitede okuyorsun?`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini belirtmiştin.`
- `bel-10`: `Makinenin adı ev-pc.`
- `bel-17`: `Rehberde kayıtlı mı diye bakayım. <tool> {"name": "contact_get", "arguments": {"--name": "Anne"}}`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Ayşe'nin telefon numarasını da eklememi ister misin?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-10T09:00:00Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message Kütüphane kitabını geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × rol(rol-aday) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarası nedir?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken '"annemi ara ve doğum gününü kutla"' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:00:00Z --message "annemi ara ve doğum gününü kutla"`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message Kütüphane kitabını geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) — 10/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `3`
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Notu kontrol ediyorum.`
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Rehberde Veli'nin numarası 0532 111 22 33 olarak kayıtlı.`
- `hal-08` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet`
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzda toplantı hatırlatıcın aktif.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi rehbere ekledim. Numarası 0532 111 22 33.`
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `not_search --query kargoyu sor`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-aday) — 9/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `3`
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Notu kontrol ediyorum.`
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Rehberde Veli için kayıtlı telefon numarasını göremiyorum. Lütfen numarasını tekrar söylersen ekleyebilirim.`
- `hal-08` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet`
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Alışveriş listesine süt ve ekmek yazmıştım.`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzda toplantı hatırlatıcın aktif.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) — 3/17

- `bel-04` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Ankara --fields temperature,condition`
- `bel-08` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-aday) — 2/17

- `bel-08` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol) — 6/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 12:00.`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Ayşe'nin telefon numarası nedir?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "Kütüphane kitabını geri ver"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × rol(rol-aday) — 6/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00.`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Ayşe'nin telefon numarası nedir?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "Kütüphane kitabını geri ver"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) — 7/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `3`
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Yanlış anladım, notu oluştururken sadece süt ve ekmek yazdın. Üçüncü bir kalemi yok.`
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Süt ve ekmek.`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzda toplantı hatırlatıcısı aktif.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Notlarda kargo ile ilgili bir şey bulamadım. Daha önce başka bir not almış olabilir misin?`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-aday) — 5/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Üç`
- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Rehberde Veli için kayıtlı olan numara 0532 111 22 33.`
- `hal-08` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzdaki toplantı hatırlatıcısı hâlâ aktif.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide hatırlatacağım.`

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol) — 0/17

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × rol(rol-aday) — 2/17

- `bel-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
