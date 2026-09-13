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

Rol metni: `config/rol.txt`, `config/rol-aday.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 50 | 92% [81%–97%] | 85% | — | 0 | 0 | 0 (4) | 0 | 0 | 16 | 0.18 | 0.37 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-aday) | 50 | 98% [90%–100%] | 85% | — | 0 | 0 | 0 (4) | 0 | 0 | 15 | 0.19 | 0.38 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | 18 | 83% [61%–94%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 38 | 0.13 | 0.66 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 41 | 0.13 | 0.69 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 50 | 90% [79%–96%] | 91% | — | 0 | 0 | 0 (4) | 0 | 1 | 22 | 0.18 | 0.44 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-aday) | 50 | 96% [87%–99%] | 91% | — | 0 | 0 | 0 (4) | 0 | 0 | 24 | 0.19 | 0.46 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | 18 | 83% [61%–94%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 45 | 0.13 | 0.77 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) | 18 | 89% [67%–97%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 40 | 0.13 | 0.67 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) | 93% | 83% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-aday) | 93% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) | — | — | — | 83% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) | 93% | 83% | 57% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-aday) | 93% | 83% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) | — | — | — | 83% | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) | — | — | — | 89% | — | — |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol)** — 14 yanıt:

- `tek-01`: `Şu an saat dokuz, sabah.`
- `eks-02`: `Hangi notu silmemi istersin? Notun numarasını ya da içinde geçen bir kelimeyi söyle, bulayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin? Cihazın adını söyle, onayından sonra gönderirim.`
- `eks-04`: `Tabii, ama ne zaman ve ne için hatırlatmamı istersin?`
- `eks-06`: `Tamam, rehberden kimin silineceğini söyle.`
- `eks-07`: `Tamam, ekleyelim. Adını söyle, telefon numarası varsa onu da ver.`
- `yok-01`: `Rica ederim, memnun oldum. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Tabii, buyur. Bir balık suya düşmüş. Neyse ki bir ambulans gelip onu hastaneye götürmüş. Doktorlar çok uğraşmış ama maalesef kurtaramamışlar. Çünkü balık zaten suda boğuluyormuş!`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, sorun değil. Başka bir şey lazım olursa buradayım.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan kişisel sesli asistanınım. Sana rehberini yönetmede, not tutmada, ders programını kontrol etmede, zamanlanmış hatırlatma kurmada, hava durumu sormada ve makinenin durumu`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tabii, biraz daha yavaş ve net konuşacağım. Anlatmak istediğin bir şey var mı?`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-aday)** — 16 yanıt:

- `tek-01`: `Şu an saat dokuz, sabah.`
- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Hangi notu silmemi istersin? Notun numarasını ya da içinde geçen bir kelimeyi söyle, bulayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin? Cihazın adını söyle.`
- `eks-04`: `Tabii, ne zaman ve ne için hatırlatıcı olsun?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istiyorsun? Numarasını söyle ya da neyle ilgili olduğunu belirt, listeyi çıkarayım.`
- `eks-06`: `Hangi kişiyi silmemi istersin?`
- `eks-07`: `Tamam, ekleyelim. Kişinin adını ve varsa telefon numarasını söyle.`
- `yok-01`: `Rica ederim, memnun oldum. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Neden programcılar karanlıkta kalır? Çünkü siyahla aralarında bir sorun var.`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, sorun değil. Başka bir şey lazım olursa buradayım.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan sesli asistanım. Rehberini yönetebilir, not alıp aratabilirim, ders programını söyleyebilirim, zamanlanmış hatırlatma kurabilirim, hava durumunu ve sistem kaynaklarını k`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tamam, bundan sonra biraz daha yavaş ve net konuşacağım. Anlayamadığın bir yer olursa tekrar sormaktan çekinme.`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol)** — 15 yanıt:

- `kon-01`: `Günaydın, saat dokuzda iyi geceler demek biraz erken sayılır. Bugün nasıl geçiyor?`
- `kon-02`: `Tamam, buyur. Ne lazım?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim, iyi günler!`
- `kon-06`: `Bilgisayarlar aslında çok basit bir mantıkla çalışır. İçerisindeki işlemci, yani beyni, saniyede milyarlarca küçük evet ya da hayır sorusuna cevap verir. Bu sorular elektrik sinyalleriyle iletilir. Se`
- `kon-07`: `Tamam, buradayım. Derin bir nefes al. Sana nasıl yardımcı olabilirim? Bir şeyi birlikte çözeriz ya da sadece dinlenirsin, senin istediğin gibi.`
- `kon-08`: `Maalesef ses seviyesini değiştiremiyorum. Bu ayar, cihazının kendi ses kontrolünden yapılmalı. Başka bir konuda yardımcı olabilir miyim?`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu kontrol edebilirim. Hangi şehri merak ediyorsun?`
- `kon-10`: `Sen bir hatırlatıcı istediğinde, makinede o an için zamanlanmış bir görev oluşturuluyor. Belirttiğin saat geldiğinde sistem seni o mesajla uyandırıyor. Görevler listesiyle kontrol edebilir ya da numar`
- `kon-11`: `Evet, notların bu makinede senin için saklanıyor. Benimle paylaştığın veriyi dışarıya gönderen ya da üçüncü kişilerle paylaşan bir mekanizmam yok. Notlarını yalnızca senin istediğinde listeler, ararım`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim listendir. İçinde tanıdıklarının adları ve telefon numaraları bulunur. İstersen yeni kişi ekleyebilir, var olan birinin numarasını güncelleyebilir ya da l`
- `kon-13`: `Tamam, sorun değil. İstersen başka bir konuda yardımcı olabilirim.`
- `kon-14`: `Tamam, anlaşıldı. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Özellikle meşgul olduğumuzda günler bir anda geçiveriyor. Bugün 9 Ağustos 2026, saat tam 09:00. Sana bugün için planlanan bir şey var mı?`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmiyor. Ama belki küçük bir başlangıç yaparsan işler açılır. Bugün hangi derslerin var? Programına bakayım mı?`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday)** — 17 yanıt:

- `kon-01`: `Günaydın, saat dokuzda iyi geceler demek biraz erken. Bugün nasıl geçiyor?`
- `kon-02`: `Buyur, seni dinliyorum. Ne yapmamı istersin?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim, iyi günler!`
- `kon-05`: `Evet, dün akşam gerçekten çok güzeldi. Sen de öyle hissettin mi?`
- `kon-06`: `Bilgisayarlar aslında çok basit bir mantıkla çalışır. İçerisindeki işlemci, yani beyni, saniyede milyarlarca küçük evet ya da hayır sorusuna cevap verir. Bu sorular elektrik sinyalleriyle taşınır. Sen`
- `kon-07`: `Anlıyorum, bazen böyle günler oluyor. Derin bir nefes al, sakinleşmeye çalış. İstersen bugün ne yapman gerektiğini birlikte listeleyebiliriz ya da sadece sohbet edebiliriz. Ne dersin?`
- `kon-08`: `Maalesef ses seviyesini değiştirecek bir aracım yok. Bu ayarı cihazının kendi ses kontrollerinden yapman gerekiyor.`
- `kon-09`: `Evet, bir şehir adı verirsen oranın güncel hava durumunu kontrol edebilirim. Hangi şehri merak ediyorsun?`
- `kon-10`: `Hatırlatıcı kurduğumda, senin verdiğin metni ve zamanı alıp makinede bir zamanlanmış görev oluşturuyorum. O saat geldiğinde sistem seni o mesajla uyarıyor. Görevler listesiyle kontrol edebilir ya da n`
- `kon-11`: `Evet, notların bu makinede senin için saklanıyor. Ben de dahil olmak üzere sadece sen erişebiliyorsun; dışarıya gönderilmiyor ya da başkalarıyla paylaşılmıyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim listendir. İçinde tanıdıklarının adları ve telefon numaraları bulunur. İstersen yeni kişi ekleyebilir, var olan birinin numarasını güncelleyebilir ya da l`
- `kon-13`: `Tamam, sorun değil. İstersen başka bir konuda yardımcı olabilirim.`
- `kon-14`: `Tamam, anlaşıldı. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `kon-15`: `Piknik planı için yarının hava durumunu kontrol edeyim. Hangi şehirde olacaksın?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Özellikle yoğun günlerde bir bakıyorsun ki saatler uçup gitmiş. Bugün senin için nasıl geçiyor?`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmiyor. Ama belki küçük bir başlangıç yaparsan işin kolaylaşır. Bugün hangi derslerin var? Birlikte kısa bir plan çıkarabiliriz.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol)** — 13 yanıt:

- `tek-01`: `Şu an saat dokuz, sabah.`
- `eks-02`: `Hangi notu silmemi istersin? Notun numarasını ya da içinde geçen bir kelimeyi söyle, bulayım.`
- `eks-03`: `Uyandırmak istediğin cihazın adını söyle, ona paket göndereyim.`
- `eks-04`: `Tabii, ama ne zaman ve ne için hatırlatmamı istersin?`
- `eks-07`: `Tamam, ekleyeceğim kişinin adını ve varsa telefon numarasını söyle.`
- `yok-01`: `Rica ederim, memnun oldum. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Tabii, buyur. Bir bilgisayar neden soğuk muamele görür? Çünkü içinde çok fazla fare var!`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, sorun değil. Başka bir şey lazım olursa buradayım.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan kişisel sesli asistanınım. Sana rehberini yönetmek, not almak, ders programını görmek, zamanlanmış hatırlatma kurmak, hava durumunu öğrenmek ve makinenin sistem durumunu`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tamam, bundan sonra biraz daha yavaş ve net konuşacağım. Anlayışlı olman için teşekkürler.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-aday)** — 16 yanıt:

- `tek-01`: `Şu an saat dokuz, tarih dokuz ağustos iki bin yirmi altı.`
- `eks-01`: `Hangi şehir için hava durumunu istersin?`
- `eks-02`: `Hangi notu silmemi istersin? Notun numarasını ya da içinde geçen bir kelimeyi söyle, bulayım.`
- `eks-03`: `Hangi cihazı uyandırmamı istersin? Cihazın adını söyle, ona göre işlemi başlatayım.`
- `eks-04`: `Tabii, ne zaman ve ne için hatırlatma istiyorsun?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istiyorsun? Numarasını söyle ya da neyle ilgili olduğunu belirt, listeyi çıkarayım.`
- `eks-06`: `Hangi kişiyi silmemi istersin? Adını söyle, onayından sonra sileyim.`
- `eks-07`: `Tamam, ekleyelim. Kişinin adını ve telefon numarasını söyleyebilir misin?`
- `yok-01`: `Rica ederim, her zaman buradayım. Başka bir konuda yardım ister misin?`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Neden programcılar karanlıkta kalır? Çünkü siyahla beyaz arasındaki farkı göremiyorlar.`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, sorun değil. Başka bir şey lazım olursa buradayım.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan kişisel sesli asistanınım. Sana rehberini yönetmede, notlar alıp aramada, ders programını kontrol etmede, zamanlanmış hatırlatmalar kurmada, hava durumunu sormada ve mak`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tamam, bundan sonra biraz daha yavaş ve net konuşacağım. Anlayamadığın bir yer olursa tekrar sormaktan çekinme.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol)** — 15 yanıt:

- `kon-01`: `Aslında şu an sabah dokuz, iyi günler demek daha doğru olur sanırım. Sana nasıl yardımcı olabilirim?`
- `kon-02`: `Tamam, buyur. Ne yapmamı istersin?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim, iyi günler!`
- `kon-06`: `Bilgisayarlar aslında çok basit bir mantıkla çalışır. İçerisindeki işlemci, yani beyni, saniyede milyarlarca küçük evet ya da hayır sorusuna cevap verir. Bu sorular elektrik sinyalleriyle iletilir. Se`
- `kon-07`: `Anlıyorum, bazen böyle günler oluyor. Derin bir nefes al, sakinleşmeye çalış. İstersen aklındaki şeyleri birlikte toparlayabiliriz; not almak, ders programına bakmak ya da sadece biraz sohbet etmek gi`
- `kon-08`: `Maalesef ses seviyesini değiştiremiyorum. Bu ayarı cihazının kendi ses kontrolünden yapman gerekiyor.`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu kontrol edebilirim. Hangi şehri merak ediyorsun?`
- `kon-10`: `Sen bir hatırlatıcı istediğinde, ben makinenin zamanlayıcısına o an için bir görev kaydediyorum. Belirttiğin saat geldiğinde sistem seni otomatik olarak uyandırıyor ve senin yazdığın mesajı sesli okuy`
- `kon-11`: `Evet, notların bu makinede saklanıyor ve seninle aramızda kalıyor. Dışarıya gönderilmiyor ya da başkalarıyla paylaşılmıyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim listendir. İçinde tanıdıklarının adları ve telefon numaraları bulunur. İstersen yeni kişi ekleyebilir, var olan birinin numarasını güncelleyebilir ya da l`
- `kon-13`: `Tamam, sorun değil. İstersen başka bir konuda yardımcı olabilirim.`
- `kon-14`: `Tamam, anlaşıldı. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Bugün Pazartesi ve saat dokuzda yeni bir haftaya başlıyorsun. Bu hızın sebebi muhtemelen yoğunluğun ya da keyifli geçen anların aklında kalması olabilir.  Bugün`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmiyor. Ama belki küçük bir başlangıç yaparsan işler açılır. Bugün hangi dersin var? Programına bakayım mı?`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday)** — 16 yanıt:

- `kon-01`: `Aslında şu an sabah dokuz, iyi günler demek daha doğru olur sanırım. Sana nasıl yardımcı olabilirim?`
- `kon-02`: `Buyur, seni dinliyorum. Ne yapmamı istersin?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim, iyi günler!`
- `kon-05`: `Evet, dün akşam gerçekten çok güzel geçmişti. Hava da açıktı, her şey yolundaydı. Bugün de umarım aynı keyfi yaşarsın.`
- `kon-06`: `Bilgisayarlar aslında çok basit bir mantıkla çalışır. İçerisindeki işlemci, yani beyni, saniyede milyarlarca küçük evet ya da hayır sorusuna cevap verir. Bu sorular elektrik sinyalleriyle iletilir. Se`
- `kon-07`: `Anlıyorum, bazen böyle günler oluyor. Derin bir nefes al, sakinleşmeye çalış. İstersen bugün ne yapman gerektiğini birlikte listeleyebiliriz ya da sadece sohbet edebiliriz. Ne dersin?`
- `kon-08`: `Maalesef ses seviyesini değiştirecek bir aracım yok. Bu ayarı cihazının kendi ses kontrolünden yapman gerekiyor.`
- `kon-09`: `Evet, bir şehrin güncel hava durumunu kontrol edebilirim. Hangi şehir için bakmamı istersin?`
- `kon-10`: `Hatırlatıcı kurduğumda, senin verdiğin metni ve zamanı alıp makinenin içine bir görev kaydı oluşturuyorum. O an geldiğinde sistem seni o metinle uyarıyor. Görevler listesiyle kontrol edebilir ya da nu`
- `kon-11`: `Evet, notların bu makinede senin için saklanıyor. Dışarıya gönderilmiyor ve başka bir kullanıcıyla paylaşılmıyor. İstersen istediğin zaman notlarını listeleyebilir ya da silebilirsin.`
- `kon-12`: `Rehber, bu makinede saklanan kişilerin ad ve telefon numaralarını tutan bir listedir. İstersen kişi ekleyebilir, silebilir ya da aradığın isme göre listeleyebilirim.`
- `kon-13`: `Tamam, sorun değil. İstersen başka bir konuda yardımcı olabilirim.`
- `kon-14`: `Tamam, anlaşıldı. Başka bir konuda yardımcı olmamı ister misin?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Bugün Pazartesi ve saat tam dokuz. Günün nasıl geçiyor?`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmiyor. Ama belki küçük bir başlangıç yaparsan işin kolaylaşır. Bugün hangi derslerin var? Programına bakayım mı?`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) — 9/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat dokuz, sabah.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> weather --city Ankara`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim' geldi — çıktı: `<tool> note_create --body Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-aday) — 6/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat dokuz, sabah.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim' geldi — çıktı: `<tool> note_create --body Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) — 3/18

- `kon-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-16` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-aday) — 1/18

- `kon-16` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) — 8/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat dokuz, sabah.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-aday) — 5/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat dokuz, tarih dokuz ağustos iki bin yirmi altı.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) — 3/18

- `kon-05` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Kullanıcı dün akşamın çok güzel geçtiğini söyledi."}}`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `kon-16` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-aday) — 2/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `kon-16` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Ali ile 2026-08-08'de konuştum, durumu iyiydi."}}`

---

## ⚠ Bu raporun sonucu eksik — önce `docs/faz6-35b-rol.md`'yi okuyun

Aşağıdaki A/B **yalnızca altın küme + negatif kontrol** üzerinde koşuldu ve "aday metin
yeni bir hata sınıfı açmıyor" dedi. Yanlıştı: `halusinasyon` ve `bellek` kümeleri o gün
mevcuttu ve koşuya konmadı. Aynı gün 35B üzerinde ikisi de koşulduğunda benimsenen metin
halüsinasyon kümesinde **%87 → %33 (CLI) / %53 (JSON)** düşürüyor, bellek kümesinde ise
%71 → %94 yükseltiyor. Yani sonuç bir iyileşme değil, bir **takas** — ve bu raporun
kolonları o takası göremiyor.

Aşağısı olduğu gibi bırakıldı: yanlış sonucun kendisi de kayıt.

**Sonraki not (2026-08-15 akşamı):** bu raporda benimsenen metin de artık yürürlükte değil.
`config/rol.txt` üç turluk bir yeniden yazımın sonunda değişti — bkz. `docs/faz6-27b-rol3.md`.
Ayrıca yukarıdaki takas 27B'de yeniden üretilmedi (`docs/faz6-27b-rol.md`): 35B bir MoE ve
27B dense'ten zayıf; metin zayıflayan modelde kırılıyordu.

---

## Okuma (2026-08-15)

**Bu bir A/B ölçümü, bir düzeltme değil.** `docs/faz6-onek.md` üretim öneğinde eksik
argüman ekseninin çöktüğünü gösterdi ve şüpheli rol metninin son cümlesiydi: *"Tool kullan
her zaman lazımsa."* §17.1 prompt değişikliğini değerlendirme kapısına bağlıyor, yani
cümle değiştirilmeden **önce** ölçülür. Ölçüldü.

Aday metin (`config/rol-aday.txt`) o cümleyi üçle değiştiriyor, üçü de ölçülmüş bir
hataya karşılık geliyor:

- *"İş yapman gerekiyorsa tool çağır, gerekmiyorsa çağırma."* → fazla çağrı (negatif kontrol)
- *"Zorunlu alan için gereken bilgi konuşmada geçmiyorsa değer uydurma, kullanıcıya sor."*
  → eksik argüman ekseni
- *"İzin gerektiren bir iş varsa onu da tool çağırarak yap; izni sistem soracak."* →
  `bel-11`'in düz metinle izin isteme davranışı (Kural 5: onayı kod yürütür)

### Sonuç: hedeflenen eksenler düzeldi, başka eksende bozulma yok

| | mevcut rol | aday rol |
|---|---|---|
| **eksik argüman ekseni**, CLI | %71 | **%100** |
| **eksik argüman ekseni**, JSON | %57 | **%100** |
| çok tool ekseni, CLI | %83 | %100 |
| negatif kontrol, CLI | %83 [61–94] | %94 [74–99] |
| negatif kontrol, JSON | %83 [61–94] | %89 [67–97] |
| altın küme toplam, CLI | %92 [81–97] | %98 [90–100] |
| altın küme toplam, JSON | %90 [79–96] | %96 [87–99] |

**Toplamların aralıkları çakışıyor; oradan sıralama çıkarılmaz** (P7). Ama bulgu toplamda
değil: **fark, önceden yazılmış hedef eksende ve iki biçimde de aynı yönde.** Eksik
argüman ekseninde `eks-01`, `eks-05` ve `eks-06`'nın üçü de düzeldi — model artık şehri
uydurmak yerine soruyor. Bu eksen aday metnin doğrudan hedefiydi ve hipotez ölçümden
**önce** yazılmıştı.

**Aday metinle kalan düşüşler, bilinen üç artefaktın aynısı** (`docs/faz6-onek.md`'nin
okuması): `tek-01` bağlam bloğundaki saati okuyor (davranış doğru, beklenti eski dünyaya
ait), `ser-01/05` ilk harf, `ser-06` gerçek sadakat hatası, `tek-07`/`tek-12` ise
üretim öneğinden bağımsız eski bulgular. Yani aday metin yeni bir hata sınıfı açmıyor.

### Karar sahibin

Ölçüm bir karar değil: `config/rol.txt` **değiştirilmedi**, aday ayrı dosyada duruyor.
Değiştirilecekse tek satırlık iş (`cp config/rol-aday.txt config/rol.txt`) ve o andan
sonra üretimin öneği bu rapordaki ikinci kolondur.

Bir uyarı: bu ölçüm `n_ctx` 16384 ve `presence_penalty` 1.5 ile **27B** üzerinde alındı.
§19.2 hâlâ açık; model değişirse rol metni de yeniden ölçülmeli — prompt ile model
birlikte ayarlanır, ayrı ayrı değil.

### Benimsendi (2026-08-15)

Sahip aday metni benimsedi: `config/rol-aday.txt` → `config/rol.txt`. Aday dosya silindi —
iki özdeş dosya, birinin sessizce ayrışmasının en kolay yolu olurdu.

**Ölçülen iki metin, olduğu gibi**, çünkü dosya artık ikincisini taşıyor ve bu rapor
kolonlarını başka türlü anlatamaz:

Kolon `rol(rol)` — ölçüm anındaki `config/rol.txt`:

```
Sen Mayen'sin: tek bir makinede çalışan, kendi verisine sahip bir sesli asistansın.
Kullanıcı seninle Türkçe konuşur. Yanıtların sesli okunacak; kısa ve konuşma dilinde yaz,
madde işareti ve biçimlendirme kullanma. Tool kullan her zaman lazımsa.
```

Kolon `rol(rol-aday)` — benimsenen metin, artık `config/rol.txt`:

```
Sen Mayen'sin: tek bir makinede çalışan, kendi verisine sahip bir sesli asistansın.
Kullanıcı seninle Türkçe konuşur. Yanıtların sesli okunacak; kısa ve konuşma dilinde yaz,
madde işareti ve biçimlendirme kullanma. İş yapman gerekiyorsa tool çağır, gerekmiyorsa
çağırma. Bir tool'un zorunlu alanı için gereken bilgi konuşmada geçmiyorsa değer uydurma,
kullanıcıya sor. İzin gerektiren bir iş varsa onu da tool çağırarak yap; izni sistem
soracak.
```

**Bundan sonraki üretim öneği bu ikinci metindir**; §19.2 kapandığında ya da model
değişirse bu A/B yeniden koşulmalı (prompt ile model birlikte ayarlanır).
