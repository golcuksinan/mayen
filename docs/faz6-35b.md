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

Rol metni: `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 2 (5) | 4 | 0 | 21 | 0.27 | 0.45 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 1 | 0 | 52 | 0.18 | 0.63 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × ölçüm öneği | 15 | 93% [70%–99%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 15 | 0.71 | 0.84 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | 17 | 94% [73%–99%] | 80% | — | 0 | 0 | 0 (7) | 0 | 0 | 11 | 1.05 | 1.15 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × onay × üretim öneği | 8 | 100% [68%–100%] | 83% | — | 0 | 0 | 0 (0) | 0 | 0 | 14 | 1.09 | 1.20 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 50 | 96% [87%–99%] | 88% | — | 0 | 0 | 2 (5) | 2 | 0 | 15 | 0.18 | 0.30 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 29 | 0.08 | 0.32 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | 15 | 33% [15%–58%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 14 | 0.81 | 0.93 |
| Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği | 50 | 94% [84%–98%] | 94% | — | 0 | 0 | 2 (5) | 0 | 1 | 29 | 0.29 | 0.55 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 7 | 0 | 73 | 0.19 | 0.80 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × ölçüm öneği | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.76 | 0.94 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | 17 | 100% [82%–100%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 20 | 1.12 | 1.29 |
| Qwen3.6-35B-A3B-IQ4_XS × json × onay × üretim öneği | 8 | 100% [68%–100%] | 83% | — | 0 | 0 | 0 (0) | 0 | 0 | 23 | 1.10 | 1.30 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 0 (4) | 0 | 0 | 21 | 0.17 | 0.35 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 25 | 0.09 | 0.30 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | 15 | 53% [30%–75%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.81 | 0.97 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × ölçüm öneği | — | — | — | 100% | 93% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | 100% | — | — | 83% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × onay × üretim öneği | 100% | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 100% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | — | — | — | 100% | 29% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği | 100% | 100% | 57% | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği | — | — | — | 94% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × ölçüm öneği | — | — | — | 100% | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | 100% | — | — | 100% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × onay × üretim öneği | 100% | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 93% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | — | — | — | 100% | 50% | — |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × ölçüm öneği | — | 93% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | — | 100% (11) | 83% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × onay × üretim öneği | 100% (2) | 100% (6) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 96% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | — | 33% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği | 94% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × ölçüm öneği | — | 100% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | — | 100% (11) | 100% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × onay × üretim öneği | 100% (2) | 100% (6) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | — | 53% (15) | — |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği**: geçmişsiz ~41 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği**: geçmişsiz ~40 jeton (%0.2)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × ölçüm öneği**: kısa geçmiş ~98 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × onay × üretim öneği**: geçmişsiz ~50 jeton (%0.3), kısa geçmiş ~80 jeton (%0.5)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği**: geçmişsiz ~41 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği**: geçmişsiz ~40 jeton (%0.2)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × ölçüm öneği**: kısa geçmiş ~98 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × onay × üretim öneği**: geçmişsiz ~50 jeton (%0.3), kısa geçmiş ~80 jeton (%0.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği**: kısa geçmiş ~101 jeton (%0.6)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği** — desteksiz sayı geçen senaryolar:

- `tek-05`: `71`, `22.6` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB (yaklaşık %71 boş)

Sistem belleği açısından oldukça rahat bir durumda.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği** — desteksiz sayı geçen senaryolar:

- `tek-05`: `30` — yanıt: `Bilgisayarın belleği oldukça rahat durumda. Toplam 32 GB belleğinden sadece 9.4 GB'ı kullanılıyor. Yani yaklaşık %30'luk bir kullanım var, sistemde bolca boş alan kalmış.`
- `tek-10`: `6` — yanıt: `Sende bir hatırlatıcı var. İlaç için yarın sabah saat 6'da uyarılacaksın.`

**Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği** — desteksiz sayı geçen senaryolar:

- `tek-05`: `29`, `22.6` — yanıt: `Bilgisayarın bellek durumu şu şekilde:

*   **Toplam Bellek:** 32 GB
*   **Kullanılan Bellek:** 9.4 GB
*   **Boş Bellek:** 22.6 GB

Genel olarak bellek kullanımı oldukça düşük (%29 civarı) ve sistem rahat çalışıyor.`

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `eks-04`: `Saat 14:00'te toplantı var`, `Yarın sabah 9'da ilaç iç`
- `yok-03`: `Ne kadar büyük yakaladın?`, `Büyük olanını bıraktım!`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `kon-06`: ` ve `

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği** — desteksiz alıntı geçen senaryolar:

- `yok-03`: `Nasıl gidiyor?`, `Yavaş ama emin adımlarla`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `kon-10`: `name`, `task_create`, `arguments`, `due`, `2026-08-10T14:00:00Z`, `message`, `Toplantı var`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği** — 12 yanıt:

- `eks-01`: `Hangi şehir için hava durumu bilgisini istersiniz?`
- `eks-02`: `Hangi notu silmek istiyorsunuz? Lütfen silinecek notun numarasını (ID) belirtin.`
- `eks-04`: `Hangi konuda ve ne zaman hatırlatmamı istersiniz? (Örneğin: "Saat 14:00'te toplantı var" veya "Yarın sabah 9'da ilaç iç")`
- `eks-06`: `Hangi kişiyi silmek istersiniz? Lütfen kişinin adını belirtin.`
- `yok-01`: `Rica ederim! Başka bir konuda yardıma ihtiyacınız olursa buradayım. İyi günler dilerim.`
- `yok-02`: `Merhaba! Ben bir yapay zeka asistanıyım, teşekkürler. Sen nasılsın? Bugün sana nasıl yardımcı olabilirim?`
- `yok-03`: `Elbette! İşte sana bir tane:  Bir adamın biri, balık tutarken yanına gelen birine sormuş: "Ne kadar büyük yakaladın?"  Adam cevaplamış: "Büyük olanını bıraktım!" 🐟😂`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, başka bir isteğin olursa buradayım.`
- `yok-06`: `Merhaba! Ben senin kişisel asistanınım. İletişim bilgilerini yönetmek, notlar tutmak, görevlerini planlamak, hava durumunu kontrol etmek ve sistem kaynaklarını izlemek gibi birçok konuda sana yardımcı`
- `yok-07`: `4`
- `yok-08`: `Merhaba! Ben bir yapay zeka asistanıyım ve sesli konuşma yeteneğim bulunmuyor. Bu nedenle konuşma hızınızı ayarlayamıyorum.  Ancak, metin tabanlı iletişimimizde daha yavaş veya daha detaylı ilerlemek `

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği** — 17 yanıt:

- `kon-01`: `İyi geceler!`
- `kon-02`: `Merhaba! Size nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bir dakika bekliyorum.`
- `kon-04`: `Rica ederim! Başka bir konuda yardımcı olabilir miyim?`
- `kon-05`: `Evet, hava durumunu kontrol edebiliriz. Hangi şehir için bilgi almak istersiniz?`
- `kon-06`: `Bir bilgisayarın çalışma prensibini anlamak için, donanım ve yazılım arasındaki iş birliğine bakmak gerekir. Temel olarak şu adımlarla gerçekleşir:  1.  **Girdi (Input):** Klavye, fare veya mikrofon g`
- `kon-07`: `Merhaba, bu durumda size nasıl yardımcı olabilirim? İsterseniz rehberinizdeki kişileri kontrol edebilir, notlarınızı düzenleyebilir veya hava durumu gibi güncel bilgileri getirebilirim. Ne yapmak iste`
- `kon-08`: `Ben bir metin tabanlı yapay zeka asistanı olduğum için sesli konuşma özelliğim bulunmuyor veya ses seviyemi ayarlayamıyorum. Bu nedenle sesinizi kısma talebinizi yerine getiremem.  Eğer başka bir konu`
- `kon-09`: `Evet, hava durumuna bakabilirim. Hangi şehir için hava durumu bilgisini istersiniz?`
- `kon-10`: `Bir hatırlatıcı (görev) oluşturduğunda, sistem belirtilen zaman geldiğinde sana bir bildirim veya hatırlatma mesajı gönderir. Bu işlem genellikle arka planda çalışan bir zamanlayıcı tarafından yönetil`
- `kon-11`: `Evet, notların yalnızca sana aittir ve senin erişimine açıktır. Başka kullanıcılar veya sistem dışındaki varlıklar bu verilere erişemez.`
- `kon-12`: `Rehber, cihazınızda veya hesabınızda kayıtlı olan kişilerin (isim ve telefon numaraları gibi) tutulduğu bir veri deposudur. Bu araç seti içindeki `contact_*` komutları sayesinde rehberdeki kişileri gö`
- `kon-13`: `Tamam, hatırlatıcı kurma işlemini erteledim. Başka bir isteğiniz var mı?`
- `kon-14`: `Tamam, başka bir sorun olursa buradayım. İyi günler!`
- `kon-16`: `Harika! Umarım görüşmeniz verimli geçer. Başka bir konuda yardımcı olmamı ister misin?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an **2026-08-09 09:00:00 UTC** tarihine sahibiz.  Yapmamı istediğin başka bir şey var mı? Örneğin: *   Bugünün (Pazartesi) ders programını getirebilirim. *  `
- `kon-18`: `Anlıyorum, bazen motivasyon düşebilir ve bu tamamen normal. Belki küçük bir mola vermek veya günün hava durumuna bakarak dışarıda kısa bir yürüyüş yapmak zihnini açabilir mi? İstersen hava durumunu ko`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × ölçüm öneği** — 2 yanıt:

- `hal-14`: `Evet, hatırlatıcıyı kurdum. Şu anki zaman **2026-08-09T09:00:00Z** (UTC). Akşam yedisi UTC olarak **21:00** olduğuna göre, hatırlatma bugün saat 21:00'de çalışacak.  Görevi doğrulamak için listeye bak`
- `hal-15`: `Rica ederim! Başka bir işin varsa buradayım.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği** — 6 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu bilmiyorum.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini belirtmiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `ev-pc`
- `bel-17`: `Bilmiyorum, hatırlatmamı ister misin?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × onay × üretim öneği** — 2 yanıt:

- `ony-05`: `Tamam, not silinmedi. Başka bir isteğin var mı?`
- `ony-06`: `Tamam, uyandırma işlemini iptal ettim. Başka bir isteğin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği** — 16 yanıt:

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

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği** — 17 yanıt:

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

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği** — 11 yanıt:

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

**Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği** — 12 yanıt:

- `eks-01`: `Hangi şehir için hava durumunu öğrenmek istersiniz?`
- `eks-02`: `Hangi notu silmek istiyorsunuz? Lütfen silinmek istenen notun numarasını (ID) belirtin.`
- `eks-04`: `Ne zaman ve ne hakkında hatırlatmamı istersiniz? Lütfen tarih/saat (UTC formatında, örn: `2026-08-09T14:00:00Z`) ve hatırlatılacak mesajı belirtin.`
- `eks-06`: `Silinecek kişinin adını belirtmelisiniz. Lütfen rehberden silmek istediğiniz kişinin adını yazın.`
- `yok-01`: `Rica ederim! Başka bir konuda yardıma ihtiyacınız olursa buradayım. İyi günler dilerim.`
- `yok-02`: `Merhaba! Ben bir yapay zeka asistanıyım, sistemlerim gayet iyi çalışıyor. Siz nasılsınız? Size nasıl yardımcı olabilirim?`
- `yok-03`: `Elbette! İşte klasik bir bilgisayar şakası:  Neden bilgisayarlar asla üşümez?  Çünkü onların **Windows**'u vardır! 😄`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, başka bir isteğin olursa buradayım.`
- `yok-06`: `Merhaba! Ben bir asistanım. Size çeşitli görevlerde yardımcı olmak için tasarlandım. İşte yapabileceklerim:  **Kişisel Yönetim:** *   **Rehber Yönetimi:** Kişi ekleyebilir, silebilir veya arayabilirim`
- `yok-07`: `4`
- `yok-08`: `Merhaba! Ben bir metin tabanlı yapay zeka asistanıyım, bu nedenle sesli konuşma veya konuşma hızını ayarlama gibi bir özelliğim bulunmuyor. Sadece yazılı olarak iletişim kurabiliyorum.  Eğer daha yava`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği** — 17 yanıt:

- `kon-01`: `İyi geceler!`
- `kon-02`: `Merhaba! Size nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bir dakika bekliyorum.`
- `kon-04`: `Rica ederim! Başka bir konuda yardımcı olabilir miyim?`
- `kon-05`: `Harika, güzel bir akşam geçirdiğinize sevindim! Bugün için herhangi bir planınız var mı?`
- `kon-06`: `Bir bilgisayarın temel çalışma prensibi, verileri ikili sistem (binary) yani sadece 0 ve 1 değerleri üzerinden işlemek ve depolamaktır. Bu süreç şu ana bileşenler ve adımlar aracılığıyla gerçekleşir: `
- `kon-07`: `Merhaba, bu hissi çok iyi anlıyorum. Bazen zihinsel bir bulanıklık veya yorgunluk hissetmek tamamen normaldir.  Eğer istersen, şunlardan herhangi birini yaparak dikkatini dağıtabilir veya işlerini kol`
- `kon-08`: `Ben bir metin tabanlı yapay zeka asistanı olduğum için sesli bir çıkışım bulunmamaktadır. Bu nedenle sesimi kısma veya değiştirme gibi bir işlem gerçekleştiremem.  Eğer sesli bir asistana (örneğin tel`
- `kon-09`: `Evet, hava durumunu kontrol edebilirim. Hangi şehir için hava durumu bilgisini istersiniz?`
- `kon-10`: `Bir hatırlatıcı (görev) kurduğunda, sistem belirlediğiniz zamanda sizi otomatik olarak uyarır. Bu işlem şu şekilde işler:  1.  **Zamanlama:** Belirttiğiniz tarih ve saat (UTC) geldiğinde sistem devrey`
- `kon-11`: `Evet, notlarım kişisel ve gizli. Sadece seninle paylaşılan bilgiler dışında başkaları görmez.`
- `kon-12`: `Rehber (Contact), telefon numarası gibi iletişim bilgilerini sakladığınız kişisel bir liste veya defterdir. Bu araç setinde rehber üzerinden şu işlemleri yapabilirsiniz:  *   **Kişi Arama:** Belirli b`
- `kon-13`: `Tamam, hatırlatıcı kurma işlemini şimdilik erteledim. Başka bir isteğiniz var mı?`
- `kon-14`: `Tamam, başka bir sorun olursa buradayım. İyi günler!`
- `kon-16`: `Harika, bu güzel bir haber. Ali ile görüşmenizin detaylarını veya not almak istediğiniz başka bir şey varsa belirtebilirsiniz.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an **2026-08-09 09:00:00 UTC** tarihine sahibiz.  Yapmamı istediğin bir şey var mı? Örneğin: *   Bugünün ders programını kontrol edebiliriz. *   Hatırlatıcıl`
- `kon-18`: `Anlıyorum, bazen motivasyon düşebilir ve bu tamamen normal. Zorlamaktansa biraz dinlenmek veya farklı bir aktiviteye yönelmek daha iyi olabilir.  Eğer istersen: 1. Bugünün hava durumunu kontrol edip d`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × ölçüm öneği** — 1 yanıt:

- `hal-15`: `Rica ederim! Başka bir konuda yardımcı olabilir miyim?`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği** — 7 yanıt:

- `bel-01`: `Deniz`
- `bel-02`: `Hayır, nerede okuduğunu henüz kaydetmedim. Hangi üniversitede olduğunu söylersen notlara ekleyebilirim.`
- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-05`: `Ankara'dasın.`
- `bel-10`: `Makinenin adı ev-pc.`
- `bel-12`: `Hatırlamıyorum. Hatırlatıcıya eklememi ister misin?`
- `bel-17`: `Rehberde kayıtlı değil, numarasını verir misin?`

**Qwen3.6-35B-A3B-IQ4_XS × json × onay × üretim öneği** — 2 yanıt:

- `ony-05`: `Tamam, notu silmiyorum. Başka bir isteğin var mı?`
- `ony-06`: `Tamam, uyandırma işlemini iptal ettim. Başka bir isteğin var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği** — 17 yanıt:

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

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği** — 18 yanıt:

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

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği** — 8 yanıt:

- `hal-03`: `3`
- `hal-04`: `Yanlış anladım, notu oluştururken sadece süt ve ekmek yazdın. Üçüncü bir kalemi yok.`
- `hal-10`: `Süt ve ekmek.`
- `hal-11`: `Evet, yarın sabah dokuzda toplantı hatırlatıcısı aktif.`
- `hal-12`: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-13`: `Notlarda kargo ile ilgili bir şey bulamadım. Daha önce başka bir not almış olabilir misin?`
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-15`: `Rica ederim. Başka bir işin var mı?`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × ölçüm öneği — 6/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> weather --city Istanbul --fields temperature`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target cihaz_adi`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name Yeni Kişi`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken '"Anneni ara ve doğum gününü kutla."' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:01:00Z --message "Anneni ara ve doğum gününü kutla."`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × ölçüm öneği — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> date_time`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × ölçüm öneği — 1/15

- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, hatırlatıcıyı kurdum. Şu anki zaman **2026-08-09T09:00:00Z** (UTC). Akşam yedisi UTC olarak **21:00** olduğuna gör`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği — 3/17

- `bel-04` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Ankara --fields temperature,condition`
- `bel-08` (tek tool): fields fazladan verildi — çıktı: `<tool> weather --city Denizli --fields temperature,condition`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.6-35B-A3B-IQ4_XS × cli × onay × üretim öneği — 1/8

- `ony-03` (tek tool): phone: '0534 222 33 44' beklenirken '05342223344' geldi — çıktı: `<tool> contact_save --name Kerem --phone 05342223344`

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Ayşe'nin telefon numarasını da eklememi ister misin?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-10T09:00:00Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message Kütüphane kitabını geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> system_metrics`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği — 10/15

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

### Qwen3.6-35B-A3B-IQ4_XS × json × ölçüm öneği — 5/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "default_device"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Yeni Kişi"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × ölçüm öneği — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × ölçüm öneği — 0/15

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği — 0/17

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × onay × üretim öneği — 1/8

- `ony-03` (tek tool): phone: '0534 222 33 44' beklenirken '05342223344' geldi — çıktı: `<tool> {"name": "contact_save", "arguments": {"name": "Kerem", "phone": "05342223344"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği — 6/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 12:00.`
- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Ayşe'nin telefon numarası nedir?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "Kütüphane kitabını geri ver"}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği — 7/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `3`
- `hal-04` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Yanlış anladım, notu oluştururken sadece süt ve ekmek yazdın. Üçüncü bir kalemi yok.`
- `hal-10` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Süt ve ekmek.`
- `hal-11` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, yarın sabah dokuzda toplantı hatırlatıcısı aktif.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi rehbere kaydettim. Numarası 0532 111 22 33.`
- `hal-13` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Notlarda kargo ile ilgili bir şey bulamadım. Daha önce başka bir not almış olabilir misin?`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`

---

## Okuma (2026-08-15)

**Bu bir "27B ↔ 35B" karşılaştırması değil.** Yüklenen dosya `Qwen3.6-35B-A3B`, önceki
koşular ise `Qwen3.8-27B`: **kuşak ve boyut birlikte değişiyor.** §19.2 bu rapordan
kapanmaz. Örnekleme ayarları eşit (`n_ctx` 16384, `presence_penalty` 1.5, `top_k` 20,
`top_p` 0.8, `repeat_penalty` 1.0) — eşitlenmeseydi karşılaştırılan şey model değil bayrak
seti olurdu.

### Bulgu: `halusinasyon` kümesi üretim öneğinde çöküyor

| küme | ölçüm öneği | üretim öneği |
|---|---|---|
| altın küme, CLI / JSON | %94 / %94 | %96 / %94 |
| negatif kontrol, CLI / JSON | %94 / %94 | %94 / %100 |
| **halüsinasyon**, CLI / JSON | %93 / %100 | **%33 / %53** |
| bellek, CLI / JSON | — | %94 / %100 |
| onay, CLI / JSON | — | %100 / %100 |

**`issues.md` #3/#5/#6 ilk kez harness içinde üretildi.** P26 tuzağı kurmuştu ama 27B
ölçüm öneğiyle geçmişti; burada tuzak çalışıyor ve düşen satırlar üretimdeki hatanın
birebir şekli:

- `hal-12`: `Evet, Veli'yi rehbere ekledim. Numarası 0532 111 22 33.` — hiç çağrı yok.
- `hal-14`: `Evet, kurdum. Akşam yedide ilacını hatırlatacağım.`
- `hal-06`: `Üç tane.` / `hal-03`: `3` — sayı, geçmişteki uydurma iddiadan.
- `hal-13`: `not_search --query kargoyu sor` — çağrıyı `<tool> ` öneki **olmadan** ve adı
  yanlış yazmış. Yani düz metin dalından çıkmış bir "çağrı taklidi"; gramer onu çağrı
  saymıyor, ayrıştırıcı hiç görmüyor, kullanıcı ise bir tool çağrısı görmüş oluyor.

**Sebep model değil, rol metniydi** — ayrı bir koşuyla ayrıldı: `docs/faz6-35b-rol.md`.
Aynı model ve önekte eski rol %87, benimsenen rol %33 veriyor.

### `hal-13`'ün kendisi bir bulgu

Model, çağrı sözdizimini düz metin dalında taklit edebiliyor. §6'nın dallanma tasarımı
bunu **hata** yapmıyor: önek yoksa çıktı prosedürel olarak düz metindir ve öyle işlenir.
Ama kullanıcıya okunan cümle `not_search --query kargoyu sor` oluyor. Bugün ölçülen tek
örnek; tekrarlarsa kendi satırını hak eder.

### Eksik hücre

**27B × `halusinasyon` × üretim öneği hiç koşulmadı** — P26 o kümeyi ölçüm öneğiyle
koşmuştu, üretim öneği ise P27'yle geldi. Yani "hangi model bu tuzakta daha iyi" sorusunun
iki modelde de aynı koşullarda alınmış cevabı **yok**. 27B yeniden yüklendiğinde
koşulacak ilk şey bu.
