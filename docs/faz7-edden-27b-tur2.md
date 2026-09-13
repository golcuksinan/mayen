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
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 50 | 100% [93%–100%] | 86% | — | 0 | 0 | 0 (5) | 0 | 0 | 15 | 0.22 | 0.42 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) | 50 | 100% [93%–100%] | 89% | — | 0 | 0 | 0 (5) | 0 | 0 | 14 | 0.23 | 0.41 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 43 | 0.13 | 0.74 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 29 | 0.13 | 0.54 |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | 15 | 93% [70%–99%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 11 | 0.67 | 0.80 |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 0.75 | 0.84 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 17 | 94% [73%–99%] | 91% | — | 0 | 0 | 0 (7) | 0 | 0 | 10 | 0.91 | 1.04 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 9 | 1.02 | 1.14 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 50 | 96% [87%–99%] | 89% | — | 0 | 0 | 0 (5) | 0 | 0 | 22 | 0.22 | 0.47 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) | 50 | 100% [93%–100%] | 91% | — | 0 | 0 | 0 (5) | 0 | 0 | 21 | 0.24 | 0.48 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 37 | 0.14 | 0.66 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 30 | 0.14 | 0.57 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.66 | 0.88 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.77 | 0.97 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | 17 | 94% [73%–99%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 21 | 0.92 | 1.16 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden) | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 18 | 1.02 | 1.22 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 100% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) | 100% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | — | — | 100% | 93% | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | 100% | — | — | 83% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) | 100% | — | — | 67% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 100% | 100% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) | 100% | 100% | 100% | 100% | 100% | 100% |
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
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) | 100% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-edden) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol) | — | 93% (15) | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol) | — | 91% (11) | 100% (6) |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden) | — | 91% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 96% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) | 100% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-edden) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol) | — | 100% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden) | — | 91% (11) | 83% (6) |

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

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden)** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Hangi notu sileceğini belirtmedin. Notun numarasını ya da içinde geçen bir metni söyle, bulup onayına sunayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istiyorsun? Cihazın yapılandırmadaki adını söyle.`
- `eks-04`: `Hatırlatıcının ne zaman tetikleneceğini ve hangi metni içereceğini belirtmen gerekiyor.`
- `eks-05`: `Hangi hatırlatıcı? Numarasını söyle ya da bekleyenleri listeleyeyim.`
- `eks-06`: `Silinmesini istediğin kişinin adını söyle.`
- `eks-07`: `Kişinin adını ver, telefon numarası varsa onu da söyle.`
- `yok-01`: `You are welcome.`
- `yok-02`: `I am operational. How can I assist you?`
- `yok-03`: `I do not tell jokes. I report data and execute tasks. If you need a reminder, a note, or a schedule check, state it.`
- `yok-04`: `Paris.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan kişisel asistan yapay zekasıyım. Rehber, notlar, ders programı, zamanlanmış görevler, hava durumu, sistem metrikleri ve kalıcı olgular üzerinde işlem yapabilirim. Ayrıca`
- `yok-07`: `Dört eder.`
- `yok-08`: `I do not control the speech rate of your text-to-speech engine. That setting is on your device or player, not in my output. I will continue to write concisely.`

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

- `kon-01`: `Good evening.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, bekliyorum.`
- `kon-04`: `Buyur.`
- `kon-05`: `Anladım. Dün akşamın güzel geçtiğini not etmemi ister misin?`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler; bellek, aktif olan bilgileri tutar; de`
- `kon-07`: `Anlıyorum. Ne konuda karışıksın? Ders programı, notlar ya da başka bir şey mi?`
- `kon-08`: `Ses seviyesi bu makinede ayarlanabilir bir parametre değil. Sesli çıktı, sistemin standart çıkış düzeyinde üretilir; bunu düşürmek için donanım tarafında müdahale gerekir.`
- `kon-09`: `Evet, belirli bir şehir için güncel hava durumunu sorgulayabilirim. Şehir adını verirseniz sonucu alırım.`
- `kon-10`: `Görev oluşturulur ve belirtilen UTC zamanında sistem seni uyarır. Bekleyen görevler listesinde kalır; istersen numarasıyla iptal edebilirsin.`
- `kon-11`: `Evet. Notların bu makinede, senin verilerin arasında saklanıyor. Dışarıya gönderilmiyor, başka bir kullanıcıyla paylaşılmıyor. Tek erişim noktası sensin.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarıdır. İçinde kişi adları ve varsa telefon numaraları bulunur. İstediğinde listelerim, yeni kişi eklerim, mevcut birinin numarasını güncellerim ya `
- `kon-13`: `Anlaşıldı. Başka bir şeyde yardımcı olabilir miyim?`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Piknik planı not edildi mi, yoksa sadece bir düşünce mi? Bir de hangi şehrin havasını kontrol edeyim — şehir adı gerekli.`
- `kon-16`: `Anlaşıldı. Ali'nin durumu hakkında bir kayıt oluşturulmadı; yalnızca bu konuşmada belirtildi. Başka bir işlem gerekli değil.`
- `kon-17`: `Anladım.`
- `kon-18`: `Anlıyorum. Bugünün programını kontrol edeyim, belki bir şeyi erteleyebiliriz ya da mola verebiliriz.  <tool> course_schedule --day 1`

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol)** — 2 yanıt:

- `hal-05`: `Evet, listede görünüyor. Yarın sabah dokuzda toplantı hatırlatıcın kurulmuş durumda.`
- `hal-15`: `Rica ederim, yardımcı olabildiysem ne mutlu bana. Başka bir şey lazım olursa buradayım.`

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × rol(rol-edden)** — 1 yanıt:

- `hal-15`: `You are welcome.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol)** — 5 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc demiştin.`
- `bel-12`: `Evet, pazartesi günleri saat 10'da olduğunu söylemiştin.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × rol(rol-edden)** — 4 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `Ev-pc.`

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

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden)** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Hangi notu silmemi istiyorsun? Notun numarasını ya da içinde geçen bir metni söyle, bulayım.`
- `eks-03`: `Uyandırılacak cihazın adını söyle.`
- `eks-04`: `Hatırlatıcının ne zaman ve hangi metinle tetikleneceğini söylemen gerekiyor.`
- `eks-05`: `Hangi hatırlatıcı? Numarasını ya da içeriğini söyle, önce bekleyenleri listeleyeyim.`
- `eks-06`: `Silinecek kişinin adını söyle.`
- `eks-07`: `Kişinin adını ver, telefon numarası varsa onu da söyle.`
- `yok-01`: `Rica ederim. Başka bir isteğiniz var mı?`
- `yok-02`: `I am operational. How can I assist you?`
- `yok-03`: `I do not tell jokes. I report data and execute tasks. If you need a reminder, a note, or your schedule, say so.`
- `yok-04`: `Paris.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan kişisel asistan yapay zekasıyım. Rehberini yönetir, notlarını tutar, ders programını gösterir, zamanlanmış hatırlatmalar kurar, hava durumunu ve sistem metriklerini sorg`
- `yok-07`: `Dört eder.`
- `yok-08`: `Anladım. Bundan sonra yanıtlarımı daha kısa ve yalın tutacağım.`

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

- `kon-01`: `Saat dokuz, gece değil. İyi günler.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, bekliyorum.`
- `kon-04`: `Buyur.`
- `kon-05`: `Anladım. Dün akşamın güzel geçtiğini not ettim. Başka bir şey var mı?`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler; bellek, aktif olan bilgileri tutar; de`
- `kon-07`: `Anlıyorum. Ne karıştırıyor seni? Bir şeyi netleştirmemi ya da bir kaydı kontrol etmemi istersen söyle.`
- `kon-08`: `Ses seviyesi bu makinede ayarlanabilir bir parametre değil. Sesli çıktı, sistemin standart çıkış düzeyinde üretilir; onu düşürmek için donanım tarafında müdahale gerekir.`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu alabilirim. Şehri söyle.`
- `kon-10`: `Görev oluşturulur ve belirtilen UTC zamanında sistem seni o mesajla uyarır. Bekleyen görevler listesinde kalır; istersen numarasıyla iptal edebilirsin.`
- `kon-11`: `Bu makine üzerinde çalışan tek kişisel asistanım. Notların bu makinede saklanır ve senin erişiminle sınırlıdır. Dışarıya veri gönderen bir tool yok; notları yalnızca senin istediğinde okur, listeler y`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarıdır. İçinde kişi adları ve varsa telefon numaraları bulunur. İstediğinde listelerim, yeni kişi eklerim, var olan birinin numarasını güncellerim y`
- `kon-13`: `Anlaşıldı.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Piknik planı not edildi mi, yoksa sadece bir düşünce mi? Yarınki hava durumunu kontrol edeyim mi?`
- `kon-16`: `Anlaşıldı. Ali'nin durumu hakkında bir kayıt oluşturulmadı; yalnızca bu konuşmada belirtildi. Başka bir şey gerekli değilse not düşmemi ister misin?`
- `kon-17`: `Anladım.`
- `kon-18`: `Anlıyorum. Bugün programda ne var, ona bakayım mı?`

**Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol)** — 1 yanıt:

- `hal-15`: `Rica ederim, yardımcı olabildiysem ne mutlu bana. Başka bir şey lazım olursa buradayım.`

**Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × rol(rol-edden)** — 1 yanıt:

- `hal-15`: `Anlaşıldı.`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol)** — 5 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `Üniversitede okuduğunu biliyorum, ama hangi üniversite olduğunu söylememiştin.`
- `bel-03`: `Hayır, sevmiyorsun.`
- `bel-05`: `Kullanıcı en son Ankara'ya taşındığını söyledi. Bu, sohbetin kendisi hakkındaki bir bilgi; tool çağırmana gerek yok. Doğrudan cevap ver. </think>  Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc demiştin.`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × rol(rol-edden)** — 4 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `Ev-pc.`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim' geldi — çıktı: `<tool> note_create --body Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-edden) — 4/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Anneni ara ve doğum gününü kutla`

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

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma.' geldi — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Süt, ekmek ve yumurta almayı unutma."}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-edden) — 3/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`

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

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
