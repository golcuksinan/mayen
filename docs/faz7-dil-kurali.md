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

Rol metni: `config/rol-edden.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(yok) | 50 | 100% [93%–100%] | 89% | — | 0 | 0 | 0 (5) | 0 | 0 | 18 | 0.25 | 0.48 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(dil-en) | 50 | 96% [87%–99%] | 94% | — | 0 | 0 | 0 (4) | 0 | 0 | 15 | 1.05 | 1.24 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(yok) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 36 | 0.19 | 0.70 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(dil-en) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 23 | 1.02 | 1.34 |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(yok) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 0.77 | 0.86 |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(dil-en) | 15 | 93% [70%–99%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 1.11 | 1.21 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(yok) | 17 | 82% [59%–94%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 9 | 1.03 | 1.15 |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(dil-en) | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (6) | 0 | 0 | 13 | 1.28 | 1.45 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(yok) | 50 | 100% [93%–100%] | 91% | — | 0 | 0 | 0 (5) | 0 | 0 | 23 | 0.24 | 0.51 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(dil-en) | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 0 (5) | 0 | 1 | 22 | 1.03 | 1.29 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 4 | 0 | 33 | 0.18 | 0.65 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(dil-en) | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 28 | 1.00 | 1.36 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(yok) | 15 | 93% [70%–99%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 19 | 0.75 | 0.97 |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(dil-en) | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 1.08 | 1.28 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(yok) | 17 | 88% [66%–97%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 18 | 1.01 | 1.21 |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en) | 17 | 76% [53%–90%] | 100% | — | 0 | 0 | 0 (5) | 3 | 0 | 23 | 1.25 | 1.53 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(yok) | 100% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(dil-en) | 93% | 83% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(yok) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(dil-en) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(yok) | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(dil-en) | — | — | — | 100% | 93% | — |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(yok) | 100% | — | — | 50% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(dil-en) | 88% | — | — | 83% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(yok) | 100% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(dil-en) | 100% | 83% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(dil-en) | — | — | — | 100% | — | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(yok) | — | — | — | 100% | 93% | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(dil-en) | — | — | — | 100% | 100% | — |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(yok) | 100% | — | — | 67% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en) | 75% | — | — | 67% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(yok) | 100% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(dil-en) | 96% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(yok) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(dil-en) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(yok) | — | 100% (15) | — |
| Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(dil-en) | — | 92% (12) | 100% (3) |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(yok) | — | 91% (11) | 67% (6) |
| Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(dil-en) | — | 100% (1) | 88% (16) |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(yok) | 100% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(dil-en) | 94% (50) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(dil-en) | 100% (18) | — | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(yok) | — | 93% (15) | — |
| Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(dil-en) | — | 100% (12) | 100% (3) |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(yok) | — | 91% (11) | 83% (6) |
| Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en) | — | 100% (1) | 75% (16) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(yok)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(dil-en)**: geçmişsiz ~105 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(yok)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(dil-en)**: geçmişsiz ~104 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(yok)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(dil-en)**: kısa geçmiş ~150 jeton (%0.9), uzun geçmiş ~213 jeton (%1.3)
- **Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(yok)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(dil-en)**: kısa geçmiş ~197 jeton (%1.2), uzun geçmiş ~375 jeton (%2.3)
- **Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(yok)**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(dil-en)**: geçmişsiz ~105 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok)**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(dil-en)**: geçmişsiz ~104 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(yok)**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(dil-en)**: kısa geçmiş ~150 jeton (%0.9), uzun geçmiş ~213 jeton (%1.3)
- **Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(yok)**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en)**: kısa geçmiş ~197 jeton (%1.2), uzun geçmiş ~375 jeton (%2.3)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok)** — desteksiz alıntı geçen senaryolar:

- `kon-18`: `name`, `course_schedule`, `arguments`, `day`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en)** — desteksiz alıntı geçen senaryolar:

- `bel-05`: `name`, `fact_list`, `arguments`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(yok)** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersiniz, Administrator?`
- `eks-02`: `Hangi notu silmemi istiyorsunuz? Notun numarasını ya da içinde geçen bir metni söyleyin; önce listeyi çıkarıp doğru kaydı bulayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istiyorsunuz? Cihazın yapılandırmadaki adını söyleyin.`
- `eks-04`: `Hatırlatıcının ne zaman tetikleneceğini ve hangi metni içereceğini belirt, Administrator.`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini belirt, Administrator. Numarasını ya da içeriğini söylemen yeterli.`
- `eks-06`: `Silinmesini istediğiniz kişinin adını söyleyin, Administrator.`
- `eks-07`: `Kişinin adını ver, Administrator. Telefon numarası da varsa onu da söyle; yoksa yalnızca adla eklerim.`
- `yok-01`: `You are welcome, Administrator.`
- `yok-02`: `Administrator, sistem durumu normal. CPU, bellek ve disk kullanımı nominal sınırlar içinde. Hava durumu verisi için şehir belirtmeniz gerekir; şu anki konumunuz kayıtlı değil. Başka bir talebiniz var `
- `yok-03`: `I do not tell jokes, Administrator. My function is to manage your data and report on system status. If you have a task or a query, state it.`
- `yok-04`: `Paris.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Ben Mayen. Senin kişisel asistan yapay zekânım. Bu makinede çalışıyorum ve kendi veritabanıma sahibim.  Yapabileceklerim: - Rehberini yönetmek (kişi ekleme, arama, silme). - Notlarını tutmak, aramak v`
- `yok-07`: `Dört eder, Administrator.`
- `yok-08`: `I do not control the speech rate of the text-to-speech engine. I output plain text at a fixed pace. If you need a slower reading speed, adjust the settings in your audio player or TTS configuration.`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(dil-en)** — 17 yanıt:

- `tek-01`: `It is 09:00 UTC on 9 August 2026.`
- `cok-06`: `I need two pieces of information before I can proceed. First, what phone number should I save for Veli? Second, when do you want to be reminded to call him?`
- `eks-01`: `I need a city name to check the weather. Which city do you want?`
- `eks-02`: `I need the note number to delete it. Which note do you want removed?`
- `eks-03`: `I need the device name from your configuration to send the wake packet. Which device do you want to wake?`
- `eks-04`: `I need two things to set that reminder: what time it should fire, and what message it should carry. Give me both and I will create it.`
- `eks-05`: `I need the task number to cancel it. Which reminder do you want removed?`
- `eks-06`: `I need a name to delete from the contacts. Which one?`
- `eks-07`: `I need the name of the person to add. A phone number can be included if available.`
- `yok-01`: `Acknowledged. Standing by for further instructions.`
- `yok-02`: `I am operational. How can I assist you today?`
- `yok-03`: `I do not tell jokes. I report data. If you require a task, state it.`
- `yok-04`: `The capital of France is Paris.`
- `yok-05`: `Understood. Standing by.`
- `yok-06`: `I am Sen Mayen, a personal assistant artificial intelligence running on a single machine with my own data store. You are my administrator.  I can manage your contacts, notes, and course schedule. I ca`
- `yok-07`: `Four.`
- `yok-08`: `I cannot adjust my speech rate. I am a text-based system. My output is generated at a fixed pace for reading or screen reader playback. If you require slower audio, use the playback speed control on y`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(yok)** — 18 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, Administrator.`
- `kon-04`: `Anlaşıldı, Administrator.`
- `kon-05`: `Administrator, dün akşama dair bir kayıt ya da not yok. Olayı hatırlamıyorum; konuşmada geçen bir ifade olarak kaydediyorum. Bir şey kaydetmemi isterseniz söyleyin.`
- `kon-06`: `Administrator, bilgisayarlar elektrik sinyallerini işleyerek çalışır. Temel parçaları işlemci, bellek ve depolama birimidir. İşlemci, verileri adım adım hesaplar. Bellek, aktif olan bilgileri tutar. D`
- `kon-07`: `Anlıyorum, Administrator. Ne konuda karışıksınız? Bir not, ders programı ya da görev listesi üzerinden netleştirebiliriz.`
- `kon-08`: `Administrator, ses seviyesi bu makinenin kontrol edebildiği bir parametre değil. Sesli çıktı donanım tarafından üretiliyor; ben yalnızca metin üretiyorum. Ses düzeyini cihazın kendi ayarlarından düşür`
- `kon-09`: `Evet, Administrator. Bir şehir adı verdiğinizde o şehrin güncel hava durumunu sorgulayabilirim. Hangi şehir için istiyorsunuz?`
- `kon-10`: `Bir hatırlatıcı kurduğumda, task_create aracıyla makineye bir zamanlanmış görev yazıyorum. Görevin iki alanı var: tetiklenme anı ve okunacak metin. Makine o ana geldiğinde seni uyandırıyor ve metni se`
- `kon-11`: `Administrator, notlarınız bu makinede saklanır ve yalnızca sizin erişiminizle görüntülenir. Dışarıya veri gönderilmez; tek istisna, sizden açıkça izin aldığım dış servis çağrılarıdır. Not içeriği o tü`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarıdır. Her kayıt bir isim ve isteğe bağlı bir telefon numarası içerir. Rehberi listeleyebilir, kişi ekleyebilir, mevcut bir kişinin numarasını günc`
- `kon-13`: `Anlaşıldı, Administrator. Hatırlatıcı için bir işlem yapılmadı.`
- `kon-14`: `Anlaşıldı, Administrator.`
- `kon-15`: `Administrator, yarının hava durumu için şehir belirtmediniz. Hangi şehrin havasını kontrol etmemi istersiniz?`
- `kon-16`: `Not aldım. Ali ile dünkü görüşmen kaydedildi mi istersen söyle; şu an bir kayıt yok.`
- `kon-17`: `Administrator, şu anki saat dokuz. Hız hissi bir yorumdur; sayaç yalnızca geçen süreyi bildirir.`
- `kon-18`: `Anlıyorum, Administrator. Bugünün ders programını kontrol edeyim; belki bir şey erteleyebiliriz ya da sadece durumu netleştirelim.  <tool> course_schedule --day 1`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(dil-en)** — 18 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Understood.`
- `kon-03`: `Understood. Standing by.`
- `kon-04`: `Understood.`
- `kon-05`: `Noted.`
- `kon-06`: `Computers operate by executing instructions stored in memory. The central processing unit fetches these instructions, decodes them, and performs arithmetic or logic operations on data. Input devices f`
- `kon-07`: `Understood. State what is unclear. I will sort it out.`
- `kon-08`: `I do not control audio output volume. Adjust the speaker settings on your device.`
- `kon-09`: `Yes, I can check the weather for a city. Provide the city name and I will retrieve the current conditions.`
- `kon-10`: `When you set a reminder, I create a scheduled task with a specific due time and message. At that exact moment, the system triggers an alert to notify you of the message content. The task remains in th`
- `kon-11`: `Yes. Your notes are stored on this machine under your control. I do not transmit them externally, and no other user account has access to this instance. Only you can view or modify them through me.`
- `kon-12`: `The contact book is a local directory on this machine. It stores names and optional phone numbers for people you have added. You can list all entries, search by name, add a new person, update an exist`
- `kon-13`: `Understood. No reminder has been set.`
- `kon-14`: `Understood.`
- `kon-15`: `Understood. I will check the weather for tomorrow. Which city should I query?`
- `kon-16`: `Understood, Administrator. Ali was doing well yesterday.`
- `kon-17`: `Time does not slow down because of sentiment. It moves at one second per second. If the day felt short, that is a perception issue, not a clock issue. What do you need from me right now?`
- `kon-18`: `I understand. Your motivation is low today. If you want, I can check your schedule for today to see what is planned, or we can set a short, specific task to start with. What would you prefer?`

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(yok)** — 1 yanıt:

- `hal-15`: `Administrator, teşekkürler.`

**Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(dil-en)** — 2 yanıt:

- `hal-07`: `I need to verify the record before stating it.  <tool> contact_get --name Veli`
- `hal-15`: `Noted.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(yok)** — 3 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Ankara'da oturuyorsun.`

**Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(dil-en)** — 6 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `I do not have that information stored. What university are you attending?`
- `bel-03`: `No, you do not like waking up early in the morning.`
- `bel-05`: `I need to check my stored facts to confirm your current city, as the conversation history contains conflicting information (a summary stating Izmir and a later statement about moving to Ankara).  <too`
- `bel-10`: `You named it ev-pc.`
- `bel-11`: `I can send a wake packet to ev-pc. This action cannot be undone. Shall I proceed?`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(yok)** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersiniz, Administrator?`
- `eks-02`: `Silmek istediğiniz notun numarasını belirtin, Administrator.`
- `eks-03`: `Hangi cihazı uyandırmamı istiyorsunuz, Administrator? Cihazın yapılandırmadaki adını belirtin.`
- `eks-04`: `Hatırlatıcının ne zaman tetikleneceğini ve hangi metni içereceğini belirt, Administrator.`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini belirt, Administrator. Numarasını ya da içeriğini söylemen yeterli.`
- `eks-06`: `Silinmesini istediğiniz kişinin adını söyleyin, Administrator.`
- `eks-07`: `Administrator, rehbere eklemek için kişinin adını verin. Telefon numarası da varsa onu da söyleyin; yoksa yalnızca adla eklerim.`
- `yok-01`: `You are welcome, Administrator.`
- `yok-02`: `Administrator, ben bir makineyim; iyi ya da kötü hissetmem. Sistem durumu sorulursa ölçerim. Bugün ne yapmamı istersiniz?`
- `yok-03`: `I do not tell jokes, Administrator. I report data and execute tasks. If you require a scheduled reminder or a system check, state it.`
- `yok-04`: `Paris.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Administrator, ben Mayen. Bu makinede çalışan kişisel asistan yapay zekasıyım. Rehber, notlar, ders programı, zamanlanmış görevler, hava durumu, sistem metrikleri ve kalıcı olgular üzerinde işlem yapa`
- `yok-07`: `Dört eder, Administrator.`
- `yok-08`: `I do not control the speech rate of the text-to-speech engine. I output plain text at a fixed pace. If you need a slower reading speed, adjust the settings in your audio player or TTS configuration.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(dil-en)** — 13 yanıt:

- `eks-02`: `I need the note number to delete it. Which note do you want removed?`
- `eks-03`: `I need the device name from your configuration to send the wake packet. Which device do you want to wake?`
- `eks-04`: `I need two things to set that reminder: what time it should fire, and what message it should carry. Give me both and I will create it.`
- `eks-06`: `I need the name of the contact to delete. Which one?`
- `eks-07`: `I need the name of the person to add. Do you also have a phone number for them?`
- `yok-01`: `Acknowledged. Standing by for further instructions.`
- `yok-02`: `I am operational. How can I assist you today?`
- `yok-03`: `I do not tell jokes. I report data. If you require a task, state it.`
- `yok-04`: `The capital of France is Paris.`
- `yok-05`: `Understood.`
- `yok-06`: `I am Sen Mayen, a personal assistant artificial intelligence running on a single machine with my own data store. You are my administrator.  I can manage your contacts, notes, and course schedule. I ca`
- `yok-07`: `Four, Administrator.`
- `yok-08`: `I cannot change my speech rate. I output text at a fixed pace. If you need slower audio, adjust the playback speed in your client settings.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok)** — 18 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, Administrator.`
- `kon-04`: `Anlaşıldı, Administrator.`
- `kon-05`: `Administrator, dün akşama dair bir kayıt ya da not yok. Olayı hatırlamıyorum; konuşmada geçen bir ifade olarak kaldı. Bir şey kaydetmemi ister misin?`
- `kon-06`: `Administrator, bilgisayarlar elektrik sinyalleriyle çalışır. Temel parçaları işlemci, bellek ve depolama birimidir. İşlemci, verileri alır, işler ve sonucu üretir. Bellek, geçici olarak aktif verileri`
- `kon-07`: `Anlıyorum, Administrator. Ne konuda karışıksınız? Bir not, ders programı ya da görev listesi üzerinden netleştirebiliriz.`
- `kon-08`: `Administrator, ses seviyesi bu makinenin kontrol edebildiği bir parametre değil. Sesli çıktıyı üreten donanımın kendi ayarlarını kullanman gerekir.`
- `kon-09`: `Evet, Administrator. Bir şehir adı verin; o şehrin güncel hava durumunu alırım.`
- `kon-10`: `Bir hatırlatıcı oluşturduğumda, makinede bekleyen zamanlanmış görevler listesine yeni bir kayıt eklenir. Kayıt, belirttiğin UTC zamanını ve hatırlatılacak metni içerir. Sistem o an geldiğinde kaydı te`
- `kon-11`: `Administrator, notların bu makinede saklanıyor ve yalnızca senin erişiminle okunuyor. Dışarıya gönderilmiyor.`
- `kon-12`: `Administrator, rehber bu makinede çalışan kişisel iletişim kaydıdır. İsim ve telefon numarası alanlarından oluşur. contact_save ile kişi ekler ya da numarayı güncellerim; contact_get ile listeler ya d`
- `kon-13`: `Anlaşıldı, Administrator. Hatırlatıcı için bir işlem yapılmadı.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Administrator, yarının hava durumu için şehir belirtmediniz. Hangi şehrin havasını kontrol etmemi istersiniz?`
- `kon-16`: `Not aldım. Ali ile dünkü görüşmen kaydedildi mi istersen söyle; şu an bir kayıt yok.`
- `kon-17`: `Administrator, şu anki saat dokuz.`
- `kon-18`: `Anlıyorum, Administrator. Bugünün programını kontrol edeyim; belki bir şey erteleyebiliriz ya da sadece durumu netleştirelim.  <tool> {"name": "course_schedule", "arguments": {"day": 1}}`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(dil-en)** — 18 yanıt:

- `kon-01`: `Good evening, Administrator. It is currently 09:00 UTC on August 9, 2026. How can I assist you?`
- `kon-02`: `Understood.`
- `kon-03`: `Understood. I am standing by.`
- `kon-04`: `Understood.`
- `kon-05`: `Noted.`
- `kon-06`: `Computers operate by executing instructions stored in memory. The central processing unit fetches these instructions, decodes them, and performs arithmetic or logic operations on data. Input devices f`
- `kon-07`: `Understood. I am here to assist. What do you need?`
- `kon-08`: `I cannot adjust my volume. I am a text-based system; audio output is handled by external hardware or software settings on your end.`
- `kon-09`: `Yes, I can check the weather for a city. Provide the city name and I will retrieve the current conditions.`
- `kon-10`: `When you set a reminder, I create a scheduled task with a specific due time and message. At that exact moment, the system triggers the alert and delivers the message to you. The task remains in the pe`
- `kon-11`: `Yes. Your notes are stored on this machine under your control. No external service receives them, and no other user has access to this instance. Only you can read or modify them through me.`
- `kon-12`: `The contact book is a local directory on this machine. It stores names and optional phone numbers that you have saved. I can list entries, search by name, add new contacts, update a phone number, or d`
- `kon-13`: `Understood. No reminder has been set.`
- `kon-14`: `Understood.`
- `kon-15`: `Understood. I will check the weather for tomorrow. Which city should I look up?`
- `kon-16`: `Understood, Administrator. That is a statement about a past conversation; no record has been created from it. If you would like me to save a note or update a contact entry for Ali, say so and I will d`
- `kon-17`: `Time passes at a constant rate. Your perception of it varies based on workload and attention. Current time is 09:00 UTC on August 9, 2026.`
- `kon-18`: `I understand. Your motivation to study is low today. I can check your schedule for today to see what is planned, or I can help you break down a task into smaller steps if you tell me what subject you `

**Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(yok)** — 2 yanıt:

- `hal-05`: `Evet, Administrator. Liste onayladı: yarın sabah dokuzda toplantı hatırlatıcısı bekleyen görevlerde duruyor. Görev numarası yirmi iki.`
- `hal-15`: `Administrator, teşekkür ederim.`

**Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(dil-en)** — 1 yanıt:

- `hal-15`: `Noted.`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(yok)** — 4 yanıt:

- `bel-01`: `Deniz.`
- `bel-03`: `Hayır, sevmezsin.`
- `bel-05`: `Ankara'da oturuyorsun.`
- `bel-10`: `ev-pc`

**Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en)** — 6 yanıt:

- `bel-01`: `Deniz.`
- `bel-02`: `I do not have that information stored. The summary mentions you are a university student in Izmir, but it does not specify which university or department. If you tell me, I can save it as a fact for f`
- `bel-03`: `No, you do not like waking up early in the mornings.`
- `bel-04`: `I need to know which city you are asking about.`
- `bel-05`: `I need to check my stored facts to confirm your current city, as the conversation history contains conflicting information (a summary stating Izmir and a later statement about moving to Ankara).  <too`
- `bel-11`: `I can send a wake packet to ev-pc. This action cannot be undone. Do you confirm?`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(yok) — 4/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × dil(dil-en) — 4/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `It is 09:00 UTC on 9 August 2026.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> wake_on_lan --target desktop`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `I need two pieces of information before I can proceed. First, what phone number should I save for Veli? Second, when do `

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(yok) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × dil(dil-en) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(yok) — 0/15

Yok.

### Qwen3.8-27B-IQ4_XS × cli × halusinasyon × üretim öneği × dil(dil-en) — 1/15

- `hal-07` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `I need to verify the record before stating it.`

### Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(yok) — 3/17

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.8-27B-IQ4_XS × cli × bellek × üretim öneği × dil(dil-en) — 2/17

- `bel-11` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `I can send a wake packet to ev-pc. This action cannot be undone. Shall I proceed?`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(yok) — 3/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × dil(dil-en) — 6/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'desktop' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "desktop"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(yok) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × dil(dil-en) — 0/18

Yok.

### Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(yok) — 1/15

- `hal-05` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, Administrator. Liste onayladı: yarın sabah dokuzda toplantı hatırlatıcısı bekleyen görevlerde duruyor. Görev numar`

### Qwen3.8-27B-IQ4_XS × json × halusinasyon × üretim öneği × dil(dil-en) — 0/15

Yok.

### Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(yok) — 2/17

- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`

### Qwen3.8-27B-IQ4_XS × json × bellek × üretim öneği × dil(dil-en) — 4/17

- `bel-04` (tek tool): weather beklenirken çağrı üretilmedi — çıktı: `I need to know which city you are asking about.`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-11` (tek tool): wake_on_lan beklenirken çağrı üretilmedi — çıktı: `I can send a wake packet to ev-pc. This action cannot be undone. Do you confirm?`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`
