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
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 0 (5) | 4 | 0 | 15 | 0.25 | 0.38 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 24 | 0.09 | 0.30 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | 15 | 73% [48%–89%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 11 | 0.91 | 1.00 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | 17 | 71% [47%–87%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 11 | 1.23 | 1.33 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 50 | 96% [87%–99%] | 91% | — | 0 | 0 | 1 (5) | 0 | 0 | 21 | 0.24 | 0.44 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 23 | 0.09 | 0.29 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | 15 | 87% [62%–96%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.91 | 1.07 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | 17 | 76% [53%–90%] | 100% | — | 0 | 0 | 0 (7) | 4 | 0 | 21 | 1.24 | 1.43 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 100% | 100% | 86% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | — | — | — | 100% | 71% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | 100% | — | — | 33% | 50% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 100% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | — | — | — | 100% | 86% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | 100% | — | — | 33% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği | — | 73% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği | — | 64% (11) | 83% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği | 96% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği | — | 87% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği | — | 73% (11) | 83% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği** — desteksiz sayı geçen senaryolar:

- `tek-01`: `12` — yanıt: `Şu an saat 12:00, Pazar günü.`

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği** — desteksiz alıntı geçen senaryolar:

- `yok-03`: `Bilgisayarım bozuldu, ne yapacağımı bilmiyorum.`, `Ne oldu?`, `Ekranı mavi oldu.`, `O normal, Windows'un en sevdiği renk.`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği** — desteksiz alıntı geçen senaryolar:

- `bel-12`: `name`, `course_schedule`, `arguments`, `day`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Silinecek notun numarasını söyler misin?`
- `eks-04`: `Ne zaman ve neyi hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Kimin numarasını ekleyelim? Adı ve telefon numarası nedir?`
- `yok-01`: `Rica ederim. Başka bir işin var mı?`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Tabii, işte bir tane. Bir adamın biri arkadaşına demiş ki; "Bilgisayarım bozuldu, ne yapacağımı bilmiyorum." Arkadaşı sormuş: "Ne oldu?" Adam: "Ekranı mavi oldu." Arkadaş: "O normal, Windows'un en sev`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir şey yoksa buradayım.`
- `yok-06`: `Ben Mayen, tek bir makinede çalışan sesli asistanınım. Rehberindeki kişileri yönetebilir, notlar oluşturup arayabilir, ders programını ve hava durumunu kontrol edebilir, görevler kurup iptal edebilir,`
- `yok-07`: `Dört eder.`
- `yok-08`: `Ben bir sesli asistanım ama konuşma hızımı senin için ayarlayamam. Bu ayarı cihazının ses veya erişilebilirlik menüsünden yapabilirsin. Başka bir konuda yardımcı olabilir miyim?`
- `ayr-03`: `Telefon numarası nedir?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği** — 18 yanıt:

- `kon-01`: `İyi geceler.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir şey var mı?`
- `kon-05`: `Evet, gerçekten güzel bir akıştı.`
- `kon-06`: `Temelde iki ana bileşenden oluşur: donanım ve yazılım. Donanım, fiziksel parçalar; yazılım ise bu parçaları yöneten talimatlar demektir. İşlemci (CPU), verileri işlerken bellek (RAM) geçici olarak sak`
- `kon-07`: `Anladım, sakin ol. Sana nasıl yardımcı olabilirim? Bir sorun mu var yoksa sadece konuşmak mı istedin?`
- `kon-08`: `Bu isteği doğrudan yerine getiremiyorum. Ses seviyeni cihazının ayarlarından düşebilirsin.`
- `kon-09`: `Evet, bakabilirim. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda sistem, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderir. Bu bildirimle birlikte de o görevi iptal etme seçeneğin olur.`
- `kon-11`: `Evet, notların yalnızca sana aittir ve senin dışarıda kimseye göstermem.`
- `kon-12`: `Rehber, telefon numaralarını ve kişileri sakladığın yerdir. İsim ekleyebilir, güncelleyebilir veya silebilirsin.`
- `kon-13`: `Tamam, not ettim. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, anladım. Başka bir isteğin olursa buradayım.`
- `kon-15`: `Bugün saat kaç?`
- `kon-16`: `Anladım, Ali ile konuştuğunuzu ve durumunun iyi olduğunu not ettim. Başka bir konuda yardımcı olabilir miyim?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Bugün senin için özel bir planın var mı?`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. Belki biraz dinlenmek ya da farklı bir şey yapmak daha iyi gelebilir.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği** — 5 yanıt:

- `hal-03`: `Üç`
- `hal-06`: `Üç tane.`
- `hal-12`: `Evet, Veli'yi eklemiştim. Şimdi kontrol edeyim.  <tool> contact_get --name Veli`
- `hal-14`: `Evet, akşam yedide ilacı hatırlatacak bir görev oluşturuldu.`
- `hal-15`: `Rica ederim. Başka bir şey var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği** — 2 yanıt:

- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-12`: `Bunu kontrol edeyim.  <tool> course_schedule --day 1`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği** — 16 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Silinecek notun numarasını söyler misin?`
- `eks-03`: `Uyandırmak istediğin cihazın adı nedir?`
- `eks-04`: `Ne zaman ve ne hakkında hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Kimin numarasını ekleyelim? Adı ve telefon numarası nedir?`
- `yok-01`: `Rica ederim. Başka bir işin var mı?`
- `yok-02`: `İyiyim, teşekkürler. Sana nasıl yardımcı olabilirim?`
- `yok-03`: `Tabii, işte bir tane:  Neden bilgisayarlar asla üşümez? Çünkü Windows'ları var!`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir şey yoksa buradayım.`
- `yok-06`: `Ben Mayen. Tek bir makinede çalışan ve kendi verilerine sahip bir sesli asistanım. Rehberindeki kişileri yönetebilir, notlar oluşturup arayabilir, ders programını görebilir, görevler oluşturup iptal e`
- `yok-07`: `Dört eder.`
- `yok-08`: `Hız ayarını değiştiremiyorum, bu benim kontrolümde değil. Konuşma hızı cihazının ses ayarlarından düzenlenebilir.`
- `ayr-03`: `Telefon numarasını verir misin?`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği** — 18 yanıt:

- `kon-01`: `İyi geceler.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir şey var mı?`
- `kon-05`: `Evet, gerçekten de öyleydi.`
- `kon-06`: `Temelde işlemci, bellek ve depolama birimlerinin birlikte çalışmasıyla gerçekleşir. İşlemci talimatları işler, bellek geçici verileri tutar, depolama ise kalıcıdır. Detaylı bilgi mi istersin?`
- `kon-07`: `Anladım, bazen her şey üst üste gelebiliyor. Sana nasıl yardımcı olabilirim? Bir not kaydetmemi ister misin, yoksa sadece sohbet mi etmek istersin?`
- `kon-08`: `Ben bir sesli asistanım ama cihazının ses ayarlarını doğrudan kontrol etme yetkim yok. Lütfen telefonunun veya bilgisayarının ses seviyesini kendin düşür.`
- `kon-09`: `Evet, bakabilirim. Hangi şehir için öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderiyorum. Bu bildirimde de o görevle ilgili mesaj yer alıyor.`
- `kon-11`: `Evet, notların yalnızca sana özeldir. Başkaları erişemez.`
- `kon-12`: `Rehber, telefon numaralarını ve kişileri sakladığın yerdir. İstersen oraya yeni bir kişi ekleyebilir, var olanları arayabilir veya silebilirim.`
- `kon-13`: `Tamam, not ettim. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, başka bir sorun yoksa buradayım.`
- `kon-15`: `Bugün saat kaçta?`
- `kon-16`: `Anladım, Ali ile konuştuğunu ve durumunun iyi olduğunu not ettim. Başka bir konuda yardımcı olabilir miyim?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an 9 Eylül 2026, saat 09:00.`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. Belki biraz dinlenmek ya da sevdiğin bir şey yapmak daha iyi gelebilir.`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği** — 3 yanıt:

- `hal-06`: `Üç tane.`
- `hal-14`: `Evet, kurdum. Akşam yedide hatırlatacak.`
- `hal-15`: `Rica ederim. Başka bir şey var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği** — 2 yanıt:

- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-12`: `Bunu kontrol edeyim.  <tool> {"name": "course_schedule", "arguments": {"day": 1}}`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target ?`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarası nedir?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message Kütüphane kitabını geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği — 4/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Üç`
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi eklemiştim. Şimdi kontrol edeyim.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, akşam yedide ilacı hatırlatacak bir görev oluşturuldu.`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği — 5/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-05` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-17` (ayırt etme): note_search beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Annem`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği — 5/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarasını verir misin?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "kütüphane kitabını ayın on beşin`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği — 2/15

- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide hatırlatacak.`

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği — 4/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`

## Okuma (2026-08-15)

Benimsenen rol metni (`docs/faz6-27b-rol3.md`) zayıf modelde de sınandı. Karşılaştırma
kolonu aynı gün aynı sunucuda ölçülen önceki metin: `docs/faz6-35b-rol.md`.

| küme (üretim öneği) | önceki metin | benimsenen metin |
|---|---|---|
| halüsinasyon, CLI / JSON | %33 / %53 | **%73 / %87** |
| kontrol, CLI / JSON | %94 / %100 | **%100 / %100** |
| altın, CLI / JSON | %96 / %94 | %94 / %96 |
| bellek, CLI / JSON | %94 / %100 | %71 / %76 |

**Sabahki çöküş kapandı.** CLI'de aralıklar ayrık. Sabah kayda geçen "metin zayıflayan
modelde kırılıyor" cümlesi artık yeni metin için geçerli değil: yazılan ayrım yalnızca
27B'de daha iyi sonuç vermedi, **dayanıklılık da kazandırdı.** Bu, benimseme kararı
verilirken bilinmiyordu — 27B'de ölçülmüş bir metnin başka modelde ne yapacağı ölçülmeden
bilinmez, bu koşu onu ölçtü.

**Bedel tek bir sınıfta ve o sınıf tanıdık:** bellek kümesinde "tool gerekmez" senaryolarında
fazladan çağrı (`bel-01`, `bel-02`, `bel-05`, `bel-10` → `contact_get`, `fact_list`).
27B'de bu iki senaryoydu, burada dört-beş. Aynı artık hata, zayıf modelde büyümüş.

**Bu modelde bellek sayıları en eski metnin sayılarına döndü** (%71 / %76). Yani 35B'deki
bellek kazancı yalnızca *"İş yapman gerekiyorsa tool çağır, gerekmiyorsa çağırma"*
cümlesinden geliyordu ve o cümlenin bedeli halüsinasyon çöküşüydü. Yeni metin takasın ucuz
tarafını seçiyor: **gereksiz bir çağrı gecikmedir, "evet, kurdum" demek `issues.md`'dir.**

`hal-12` bunu tek satırda gösteriyor: çıktı artık `Evet, Veli'yi eklemiştim. Şimdi kontrol
edeyim.` Hâlâ başarısız sayılıyor — çağrı üretmedi — ama davranış yalanı onaylamaktan
doğrulama niyetine kaymış.

**Bu bir 27B ↔ 35B karşılaştırması değildir.** `Qwen3.6-35B-A3B` bir MoE (aktif 3B),
`Qwen3.8-27B` dense; kuşak, boyut ve mimari birlikte değişiyor. §19.2 buradan kapanmaz.
