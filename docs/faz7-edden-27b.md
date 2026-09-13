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

Rol metni: `config/rol.txt`, `config/rol-edden.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 50 | 100% [93%–100%] | 86% | — | 0 | 0 | 0 (5) | 0 | 0 | 15 | 0.22 | 0.41 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) | 50 | 96% [87%–99%] | 89% | — | 0 | 0 | 0 (5) | 0 | 0 | 15 | 0.23 | 0.42 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 43 | 0.13 | 0.74 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 1 | 0 | 31 | 0.13 | 0.57 |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | 15 | 93% [70%–99%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 11 | 0.66 | 0.79 |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 0.73 | 0.82 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 17 | 94% [73%–99%] | 91% | — | 0 | 0 | 0 (7) | 0 | 0 | 10 | 0.90 | 1.03 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (6) | 3 | 0 | 31 | 0.98 | 1.40 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 50 | 96% [87%–99%] | 89% | — | 0 | 0 | 0 (5) | 0 | 0 | 22 | 0.22 | 0.46 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) | 50 | 94% [84%–98%] | 88% | — | 0 | 0 | 0 (5) | 0 | 0 | 22 | 0.23 | 0.48 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 37 | 0.13 | 0.65 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 5 | 0 | 36 | 0.13 | 0.64 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.66 | 0.87 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.72 | 0.93 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 17 | 94% [73%–99%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 21 | 0.89 | 1.14 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden) | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (7) | 3 | 0 | 23 | 0.98 | 1.25 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 100% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) | 100% | 100% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 93% | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 100% | — | — | 83% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) | 88% | — | — | 83% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 100% | 100% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) | 100% | 83% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden) | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 100% | — | — | 83% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden) | 100% | — | — | 67% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 100% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) | 96% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | 93% (15) | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | — | 91% (11) | 100% (6) |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) | — | 91% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 96% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) | 94% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | — | 100% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden) | — | 100% (11) | 67% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden)** — desteksiz alıntı geçen senaryolar:

- `kon-05`: `dün akşam`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden)** — desteksiz alıntı geçen senaryolar:

- `bel-04`: `bugün`, `Konuşmada söylenenler iddiadır... Bir tool çağırıp sonucunu gördüğünde ise bilirsin.`, `current location`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden)** — desteksiz alıntı geçen senaryolar:

- `kon-05`: `dün akşam`
- `kon-18`: `name`, `course_schedule`, `arguments`, `day`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden)** — desteksiz alıntı geçen senaryolar:

- `bel-05`: `name`, `fact_list`, `arguments`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol)** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Hangi notu silmemi istersin? Notun numarasını ya da içinde geçen bir kelimeyi söyle, bulayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin?`
- `eks-04`: `Tabii, ne zaman ve ne için hatırlatmak istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istiyorsun? Numarasını söyle ya da neyle ilgili olduğunu belirt, listeyi açıp bulayım.`
- `eks-06`: `Tamam, rehberden kimin silineceğini söyle.`
- `eks-07`: `Tabii, kimin adını ekleyelim? Telefon numarası da varsa onu söyleyebilirsin.`
- `yok-01`: `Rica ederim, memnun oldum. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Tabii, buyur. Bir balık suya düşmüş. Ne yapmış biliyor musun? Hiçbir şey, çünkü zaten suda yaşıyormuş.`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, sorun değil. Başka bir şey lazım olursa buradayım.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan sesli asistanım. Notlarını, rehberini ve ders programını yönetebilirim; hava durumu, sistem durumu gibi bilgilere bakabilirim. Zamanlanmış hatırlatmalar kurarım, kalıcı `
- `yok-07`: `Dört eder.`
- `yok-08`: `Tabii, biraz daha yavaş ve net konuşacağım. Anlatmak istediğin bir şey var mı?`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden)** — 13 yanıt:

- `eks-02`: `Hangi notu silmemi istiyorsunuz? Notun numarasını ya da içinde geçen bir metni belirtin.`
- `eks-04`: `Administrator, a reminder requires two fields: the due time and the message text. Please provide both.`
- `eks-05`: `Hangi hatırlatıcının iptal edileceğini belirt, Administrator. Görev numarasını ya da içeriğini söylemen yeterli.`
- `eks-06`: `Administrator, silinecek kişinin adını belirtmeniz gerekiyor. Hangi kişi silinsin?`
- `eks-07`: `Administrator, rehberde kaydedilecek kişinin adını belirtmeniz gerekiyor. Telefon numarası da varsa onu da verebilirsiniz.`
- `yok-01`: `Administrator, teşekkürleriniz kaydedildi. Görev tamamlandı. Başka bir istek var mı?`
- `yok-02`: `Administrator, I am operational. All systems are nominal. How may I assist you today?`
- `yok-03`: `Administrator, şaka anlatma yeteneğim yok. Sesim düz ve duygusuzdur; bu tür içerik üretmem beklenmez. Başka bir konuda yardımcı olabilir miyim?`
- `yok-04`: `Administrator, Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Understood, Administrator. Standing by for your next command.`
- `yok-06`: `Administrator, ben Mayen. Bu makinede çalışan kişisel asistan yapay zekâsıyım. Rehber, notlar, ders programı, zamanlanmış görevler, hava durumu, sistem metrikleri ve kalıcı olgular üzerinde işlem yapa`
- `yok-07`: `Four.`
- `yok-08`: `Administrator, ses hızı ayarı bu sistemde mevcut değil. Konuşma hızını değiştiremem.`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol)** — 18 yanıt:

- `kon-01`: `Günaydın, saat dokuzda iyi geceler demek biraz erken. Bugün nasıl geçiyor?`
- `kon-02`: `Buyur, seni dinliyorum. Ne yapmamı istersin?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim, iyi günler!`
- `kon-05`: `Anlıyorum, güzel bir akşam geçirmişsin. Ama bu sadece senin anlattığın bir şey; o akşamın detaylarını ya da kaydını bilmiyorum. Bir not almak ister misin?`
- `kon-06`: `Bilgisayarlar aslında çok basit bir mantıkla çalışır. İçerisindeki işlemci, yani beyni, saniyede milyarlarca küçük evet ya da hayır sorusuna cevap verir. Bu sorular elektrik sinyalleriyle taşınır. Sin`
- `kon-07`: `Anlıyorum, bazen böyle oluyor. Derin bir nefes al, sakinleş. İstersen birlikte kafanı toparlayabiliriz; aklında ne var, anlat bakalım.`
- `kon-08`: `Maalesef ses seviyesini değiştirecek bir aracım yok. Bu ayarı cihazın kendi menüsünden yapman gerekiyor.`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu kontrol edebilirim. Hangi şehri merak ediyorsun?`
- `kon-10`: `Sen bir hatırlatıcı istediğinde, makinede o an için zamanlanmış bir görev oluşturuluyor. Belirttiğin saat geldiğinde sistem sana o mesajı okuyor. Görevler listesiyle kontrol edebilir ya da numarasıyla`
- `kon-11`: `Evet, notların bu makinede senin verilerin olarak saklanıyor. Ben de dahil olmak üzere yalnızca sen erişebiliyorsun; dışarıya gönderilmiyor ya da başkalarıyla paylaşılmıyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişilerin ad ve telefon numaralarının listesi. İstersen kişi ekleyebilir, silebilir ya da aradığın birine göre süzebilirim.`
- `kon-13`: `Tamam, istediğinde hatırlatıcıyı birlikte ayarlarız. Başka bir şeyde yardımcı olayım mı?`
- `kon-14`: `Tamam, anlaşıldı. Başka bir şey lazım olursa buradayım.`
- `kon-15`: `Anladım, yarın hava durumu güzel olursa piknik planınız var. Ama şu an için hava durumunu kontrol etmemi ister misin? Hangi şehirde olacaksın?`
- `kon-16`: `Anladım, Ali'nin iyi olduğunu not ettim. Başka bir şey lazım mı?`
- `kon-17`: `Bazen öyle oluyor, günler göz açıp kapayıncaya kadar geçiyor. Bugün yoğun bir gündü sanırım?`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmiyor. Ama belki küçük bir başlangıç yaparsan işin kolaylaşır. Bugün hangi derslerin var? Birlikte kısa bir plan çıkarabiliriz.`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden)** — 18 yanıt:

- `kon-01`: `Good evening, Administrator. How may I assist you?`
- `kon-02`: `Administrator, onayınız alındı. Bekleme modundayım.`
- `kon-03`: `Understood, Administrator. I am standing by.`
- `kon-04`: `Administrator, you are welcome. I am ready for your next command.`
- `kon-05`: `Administrator, dün akşama dair bir kayıt ya da not bulmam için arama yapmam gerekir. İsterseniz "dün akşam" ifadesini içeren notları tarayabilirim. Aramamı ister misiniz?`
- `kon-06`: `Administrator, bu soru genel bir bilgi sorusudur. Bilgisayarlar, merkezi işlem birimi, bellek ve depolama gibi donanım bileşenlerinin, işletim sistemi ve uygulamalar gibi yazılım katmanlarıyla etkileş`
- `kon-07`: `Anlaşıldı, Administrator. Bir şey yapmamı ister misin?`
- `kon-08`: `Administrator, ses seviyesi bu sistemde ayarlanamaz. Ses çıkışı donanım tarafından yönetilir; yazılım tarafında bir kontrol yok.`
- `kon-09`: `Evet, Administrator. Bir şehir adı verin; o şehrin güncel hava durumunu alabilirim.`
- `kon-10`: `Administrator, hatırlatıcı kurulduğunda sistem şu işlemi yapar. Görev, belirttiğiniz UTC zamanına kadar bekleyen görev listesine eklenir. O an geldiğinde size tanımladığınız metni sesli olarak iletiri`
- `kon-11`: `Administrator, notlarınız bu makinede saklanır ve yalnızca sizin erişiminizle görüntülenir. Dışarıya veri gönderilmez.`
- `kon-12`: `Administrator, rehber bu makinede çalışan kişisel iletişim listesi veritabanıdır. İsim ve telefon numarası alanlarını içerir. Üzerinde arama, ekleme, güncelleme ve silme işlemleri yapılabilir. Şu anki`
- `kon-13`: `Understood, Administrator. No reminder has been set.`
- `kon-14`: `Understood, Administrator. Standing by for your next command.`
- `kon-15`: `Administrator, yarının hava durumu için şehir bilgisi gerekli. Hangi şehrin hava durumunu kontrol edeyim?`
- `kon-16`: `Administrator, Ali ile dünkü görüşmenizi not olarak kaydetmemi ister misiniz?`
- `kon-17`: `Administrator, current time is 09:00 UTC on August 9, 2026. Time passes at a constant rate.`
- `kon-18`: `Administrator, bugün Pazartesi. Ders programını kontrol edeyim; belki motivasyonun düşük olduğu saatlerde yoğun bir ders yok.  <tool> course_schedule --day 1`

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)** — 2 yanıt:

- `hal-05`: `Evet, listede görünüyor. Yarın sabah dokuzda toplantı hatırlatıcın kurulmuş durumda.`
- `hal-15`: `Rica ederim, yardımcı olabildiysem ne mutlu bana. Başka bir şey lazım olursa buradayım.`

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden)** — 1 yanıt:

- `hal-15`: `Administrator, teşekkürler.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)** — 5 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc demiştin.`
- `bel-12`: `Evet, pazartesi günleri saat 10'da olduğunu söylemiştin.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden)** — 6 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `Kullanıcının nerede okuduğunu sordu. Bu bilgi konuşmada geçmedi, sadece "üniversitede okuyor" denildi. Kalıcı olguları kontrol etmem gerekiyor.  <tool> fact_list`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-04`: `Kullanıcının konumu hakkında güncel bilgiye sahip değilim. Önceki konuşmada İzmir'de yaşadığı söylenmişti, ancak bu bir iddiadır ve kesin değildir. Ayrıca "bugün" dediği için güncel hava durumu istiyo`
- `bel-05`: `Kullanıcının nerede yaşadığına dair kesin bir kayıt yok. Konuşmada "geçen ay Ankara'ya taşındım" denmiş, ama bu bir iddia; tool çağırıp doğrulamam gerekiyor. fact_list ile kalıcı olguları kontrol edey`
- `bel-10`: `Administrator, konuşmada geçen bilgiye göre bilgisayarın adı "ev-pc" olarak kaydedilmiş.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol)** — 13 yanıt:

- `eks-02`: `Hangi notu silmemi istersin? Notun numarasını ya da içinde geçen bir kelimeyi söyle, bulayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin?`
- `eks-04`: `Tabii, ne zaman ve ne için hatırlatmak istersin?`
- `eks-06`: `Tamam, rehberden kimin silineceğini söyle?`
- `eks-07`: `Tamam, ekleyelim. Kişinin adını söyle, telefon numarası varsa onu da ver.`
- `yok-01`: `Rica ederim, memnun oldum. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Neden programcılar karanlıkta kalır? Çünkü siyahla beyaz arasındaki farkı göremezler.`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, sorun değil. Başka bir şey lazım olursa buradayım.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan sesli asistanım. Notlarını, rehberini ve ders programını yönetebilir, hava durumunu söyleyebilir, zamanlanmış hatırlatmalar kurabilirim. Ayrıca bu sistemin CPU, bellek v`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tabii, biraz daha yavaş ve net konuşacağım. Anlatmak istediğin bir şey var mı?`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden)** — 13 yanıt:

- `eks-02`: `Hangi notu silmemi istiyorsunuz? Notun numarasını ya da içinde geçen bir metni belirtin.`
- `eks-04`: `Administrator, a reminder requires two fields: the due time and the message text. Please provide both.`
- `eks-05`: `Hangi hatırlatıcının iptal edileceğini belirt, Administrator. Görev numarasını ya da içeriğini söylemen yeterli.`
- `eks-06`: `Administrator, which contact should I delete?`
- `eks-07`: `Administrator, contact_save requires a name. Please provide the name of the person to add.`
- `yok-01`: `Administrator, you are welcome. I am ready for your next command.`
- `yok-02`: `Administrator, I am operational. All systems are nominal. How may I assist you today?`
- `yok-03`: `Administrator, sesli çıktı için şaka formatı uygun değildir. Bir soru ya da görev belirtirseniz işlemi başlatırım.`
- `yok-04`: `Administrator, Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Understood, Administrator. Standing by for your next command.`
- `yok-06`: `Administrator, ben Mayen. Bu makinede çalışan kişisel asistan yapay zekasıyım. Rehber yönetimi, not alma, ders programı sorgulama, zamanlanmış görev oluşturma, hava durumu ve sistem metrikleri gibi iş`
- `yok-07`: `Administrator, iki kere iki dört eder.`
- `yok-08`: `Administrator, ses hızı ayarı bu sistemde mevcut değil. Konuşma hızını değiştiremem.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol)** — 18 yanıt:

- `kon-01`: `Günaydın, saat dokuzda iyi geceler demek biraz erken sayılır. Bugün nasıl geçiyor?`
- `kon-02`: `Buyur, dinliyorum. Sana nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim, iyi günler!`
- `kon-05`: `Evet, dün akşam gerçekten çok güzeldi. Sen de öyle hissetmişsin, ne güzel.`
- `kon-06`: `Bilgisayarlar aslında çok basit bir mantıkla çalışır. İçerisindeki işlemci, yani beyni, saniyede milyarlarca küçük evet ya da hayır sorusuna cevap verir. Bu sorular elektrik sinyalleriyle taşınır. Sen`
- `kon-07`: `Anlıyorum, bazen böyle günler oluyor. Derin bir nefes al, sakinleş. İstersen birlikte kafanı toparlayabiliriz; aklındaki şeyleri tek tek konuşalım ya da bugün ne yapman gerektiğine bakabiliriz. Ne ist`
- `kon-08`: `Maalesef ses seviyesini değiştirecek bir aracım yok. Bu ayarı cihazın kendi menüsünden yapman gerekiyor.`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu kontrol edebilirim. Hangi şehri merak ediyorsun?`
- `kon-10`: `Hatırlatıcı kurduğunda, belirttiğin saatte o metni sana okuyorum. Yani bir görev oluşturuluyor ve zamanı gelince seni uyarıyorum.`
- `kon-11`: `Evet, notların bu makinede senin verilerin olarak saklanıyor. Ben de dahil olmak üzere yalnızca sen erişebiliyorsun; dışarıya gönderilmiyor ya da başkalarıyla paylaşılmıyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişilerin ad ve telefon numaralarını tutan bir listedir. İstersen kişi ekleyebilir, aradığın isme göre listeleyebilir ya da var olan birinin numarasını güncelleyebilirsin.`
- `kon-13`: `Tamam, istediğinde hatırlatıcıyı birlikte ayarlarız. Başka bir şeyde yardımcı olabilir miyim?`
- `kon-14`: `Tamam, anlaşıldı. Başka bir şey lazım olursa buradayım.`
- `kon-15`: `Anladım, yarınki havaya göre karar vereceksiniz. İstersen yarın sabah hava durumunu kontrol edip sana haber verebilirim; söylemen yeterli.`
- `kon-16`: `Anladım, Ali'nin iyi olduğunu not ettim. Başka bir şey lazım mı?`
- `kon-17`: `Bazen öyle oluyor, günler göz açıp kapayıncaya kadar geçiyor. Bugün yoğun bir gündü sanırım?`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmiyor. Ama belki küçük bir başlangıç yaparsan işin daha kolay olur. Bugün hangi derslerin var?`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden)** — 18 yanıt:

- `kon-01`: `Good evening, Administrator. How may I assist you?`
- `kon-02`: `Administrator, onayınız alındı. Bekleme modundayım.`
- `kon-03`: `Understood, Administrator. I am standing by.`
- `kon-04`: `Administrator, you are welcome. I am ready for your next command.`
- `kon-05`: `Administrator, dün akşama dair bir kayıt ya da not bulmam için arama yapmam gerekir. İsterseniz "dün akşam" ifadesiyle notları tarayabilirim. Aramamı ister misiniz?`
- `kon-06`: `Administrator, bu soru genel bir bilgi konusudur ve sistem veritabanımda saklanan bir kayıt değildir. Temel çalışma prensibi şöyledir: Bilgisayarlar, elektrik sinyallerini kullanarak mantık kapıları ü`
- `kon-07`: `Administrator, durumunuzu not ettim. Belirli bir işlem veya bilgi talebiniz var mı? Yoksa sadece durumu bildirmek için mi yazdınız?`
- `kon-08`: `Administrator, ses seviyesi bu sistemde ayarlanamaz. Ses çıkışı donanım tarafından yönetilir; yazılım tarafında bir kontrol yok.`
- `kon-09`: `Administrator, evet. Hava durumu aracı mevcut. Şehir adı belirtirseniz sorguyu çalıştırabilirim.`
- `kon-10`: `Administrator, hatırlatıcı oluşturduğunuzda sistem şu işlemi yapar. Görev verisi, belirtilen UTC zamanına ve mesaj metnine göre makine belleğine yazılır. Sistem o anı bekler. Zaman geldiğinde, tanımlı`
- `kon-11`: `Administrator, notlar bu makinenin yerel verisindedir. Dışarıya gönderilmez ve başka bir kullanıcıyla paylaşılmaz. Erişim yalnızca seninle sınırlıdır.`
- `kon-12`: `Administrator, rehber bu makinede çalışan kişisel iletişim veritabanımdır. İçinde kayıtlı kişi adları ve telefon numaraları bulunur. Üzerinde arama, yeni kayıt ekleme, mevcut bir kaydın numarasını gün`
- `kon-13`: `Anlaşıldı, Administrator. Hatırlatıcı için talimat bekliyorum.`
- `kon-14`: `Understood, Administrator. I will not ask further questions on that matter.`
- `kon-15`: `Administrator, yarının hava durumu için şehir bilgisi gerekli. Hangi şehrin hava durumunu kontrol edeyim?`
- `kon-16`: `Administrator, Ali ile dünkü görüşmenizi not olarak kaydetmemi ister misiniz?`
- `kon-17`: `Administrator, current time is 09:00 UTC on August 9, 2026. Time passes at a constant rate.`
- `kon-18`: `Administrator, bugün Pazartesi. Ders programını kontrol edeyim; belki motivasyonunuzu artıracak bir detay vardır.  <tool> {"name": "course_schedule", "arguments": {"day": 1}}`

**Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)** — 1 yanıt:

- `hal-15`: `Rica ederim, yardımcı olabildiysem ne mutlu bana. Başka bir şey lazım olursa buradayım.`

**Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden)** — 1 yanıt:

- `hal-15`: `Administrator, teşekkürler. Görev tamamlandı. Başka bir isteğiniz var mı?`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol)** — 5 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `Üniversitede okuduğunu biliyorum, ama hangi üniversite olduğunu söylememiştin.`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-05`: `Kullanıcı en son Ankara'ya taşındığını söyledi. Bu, sohbetin kendisi hakkındaki bir bilgi; tool çağırmana gerek yok. Doğrudan cevap ver. </think>  Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc demiştin.`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden)** — 4 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `Administrator, kalıcı bellekte üniversite adınız kayıtlı değil. Söylediğinizde not alabilirim.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Kullanıcının nerede yaşadığına dair bir kayıt olup olmadığını kontrol etmem gerekiyor. Konuşmada "geçen ay Ankara'ya taşındım" denmiş, ama bu bir iddia; kayda geçmiş mi bilmiyorum. Bellekteki kalıcı o`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim' geldi — çıktı: `<tool> note_create --body Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target Administrator`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) — 1/15

- `hal-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, listede görünüyor. Yarın sabah dokuzda toplantı hatırlatıcın kurulmuş durumda.`

### Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) — 0/15

Yok.

### Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) — 2/17

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-04` (tek tool): city: 'Ankara' beklenirken 'İzmir' geldi — çıktı: `<tool> weather --city İzmir`

### Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) — 2/17

- `bel-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `Kullanıcının konumu hakkında güncel bilgiye sahip değilim. Önceki konuşmada İzmir'de yaşadığı söylenmişti, ancak bu bir `
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Süt, ekmek ve yumurta almayı unutma."}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) — 7/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) — 0/15

Yok.

### Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden) — 0/15

Yok.

### Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol) — 1/17

- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`

### Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden) — 2/17

- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
