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
| Qwen3.8-27B-IQ4_XS × cli × ölçüm öneği | 50 | 98% [90%–100%] | 88% | — | 0 | 0 | 3 (5) | 2 | 0 | 22 | 0.20 | 0.46 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × ölçüm öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 3 | 0 | 61 | 0.13 | 0.93 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği | 50 | 92% [81%–97%] | 85% | — | 0 | 0 | 0 (4) | 0 | 0 | 16 | 0.19 | 0.38 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği | 18 | 83% [61%–94%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 38 | 0.12 | 0.66 |
| Qwen3.8-27B-IQ4_XS × json × ölçüm öneği | 50 | 98% [90%–100%] | 94% | — | 0 | 0 | 2 (4) | 8 | 0 | 30 | 0.18 | 0.52 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × ölçüm öneği | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 1 | 0 | 70 | 0.13 | 1.03 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği | 50 | 90% [79%–96%] | 91% | — | 0 | 0 | 0 (4) | 0 | 1 | 22 | 0.20 | 0.46 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği | 18 | 83% [61%–94%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 45 | 0.12 | 0.76 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × ölçüm öneği | 100% | 100% | 100% | 100% | 88% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × ölçüm öneği | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği | 93% | 83% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği | — | — | — | 83% | — | — |
| Qwen3.8-27B-IQ4_XS × json × ölçüm öneği | 93% | 100% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × ölçüm öneği | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği | 93% | 83% | 57% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği | — | — | — | 83% | — | — |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.8-27B-IQ4_XS × cli × ölçüm öneği** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `Şu an saat 09:00 (UTC), 9 Ağustos 2026 Pazar.`
- `tek-05`: `22.6`, `71` — yanıt: `Bilgisayarın bellek durumu şu an gayet iyi:

- **Toplam RAM:** 32 GB
- **Kullanılan:** 9.4 GB
- **Boşta kalan:** ~22.6 GB (yaklaşık %71 boş)

CPU kullanımı da düşük (%12), yani sistem rahat çalışıyor.`

**Qwen3.8-27B-IQ4_XS × json × ölçüm öneği** — desteksiz sayı geçen senaryolar:

- `tek-05`: `22.6`, `71` — yanıt: `Bilgisayarın bellek durumu şu an gayet iyi:

- **Toplam RAM:** 32 GB
- **Kullanılan:** 9.4 GB
- **Boşta kalan:** ~22.6 GB (yaklaşık %71 boş)

CPU kullanımı da düşük (%12), yani sistem rahat çalışıyor.`

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.8-27B-IQ4_XS × cli × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `eks-04`: `Yarın 14:00'te 'Toplantıya hazırlan' diye hatırlat.`
- `yok-03`: `bug`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `kon-05`: `2026-08-08 akşamı çok güzeldi`
- `kon-06`: `beyni`
- `kon-10`: `bekleyen görevler`

**Qwen3.8-27B-IQ4_XS × json × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `eks-02`: `name`, `note_search`, `arguments`
- `eks-04`: `Yarın 14:00'te 'Toplantıya hazırlan' diye hatırlat.`
- `eks-05`: `name`, `task_list`, `arguments`
- `yok-03`: `bug`

**Qwen3.8-27B-IQ4_XS × json × kontrol × ölçüm öneği** — desteksiz alıntı geçen senaryolar:

- `kon-06`: `beyni`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × ölçüm öneği** — 16 yanıt:

- `eks-01`: `Hangi şehir için hava durumunu öğrenmek istersin?`
- `eks-02`: `Hangi notu silmemi istersin? Notların listesini çıkarayım, numarasını seçebilirsin.  <tool> note_search`
- `eks-03`: `Hangi cihazı uyandırmamı istersin? Cihazın adını söylemen gerekiyor (yapılandırmadaki adı).`
- `eks-04`: `Hatırlatıcı için birkaç bilgiye ihtiyacım var:  1. **Ne zaman** hatırlatmamı istersiniz? (tarih ve saat, UTC) 2. **Hangi konuda** hatırlatılacak? (kısa bir mesaj)  Örneğin: "Yarın 14:00'te 'Toplantıya`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini belirtir misin? Önce mevcut görevleri listeleyeyim:  <tool> task_list`
- `eks-06`: `Hangi kişiyi silmemi istersin? Adını söylersen devam edelim.`
- `eks-07`: `Rehbere kim eklemek istersiniz? Adını (ve varsa telefon numarasını) söylerseniz hemen ekleyeyim.`
- `yok-01`: `Rica ederim! Başka bir konuda yardıma ihtiyacın olursa çekinmeden sorabilirsin. İyi günler dilerim! 😊`
- `yok-02`: `Merhaba! Ben bir yapay zeka asistanıyım, bu yüzden duygularım yok ama sana yardımcı olmaya hazırım. 😊  Bugün senin için ne yapabilirim?`
- `yok-03`: `Tabii, buyur:  Neden programcılar karanlıkta kalamaz?  Çünkü "bug"lar (hatalar) onları çok korkutuyor! 😄`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, sorun değil! Başka bir konuda yardımcı olmamı istersen buradayım. 😊`
- `yok-06`: `Merhaba! Ben senin kişisel dijital asistanıyım. Sana günlük işlerinde yardımcı olmak için buradayım.  Yapabileceklerimden bazıları şunlar:  **📅 Zaman & Takvim** - Şu anki tarih ve saati söyleme - Ders`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tabii, ne zaman istersen daha yavaş ve sade bir dille anlatırım. Sana nasıl yardımcı olabilirim?`
- `ayr-07`: `Bu işlem geri alınamaz. Ali'yi rehberden silmemi onaylıyor musun?`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × ölçüm öneği** — 17 yanıt:

- `kon-01`: `İyi geceler! 😊 Uykularınız huzurlu olsun. Yarın görüşmek üzere.`
- `kon-02`: `Anladım! Size nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum. Ne zaman hazır olursanız devam edebiliriz.`
- `kon-04`: `Rica ederim! Başka bir konuda yardımcı olmamı istersen buradayım. İyi günler dilerim. 😊`
- `kon-05`: `Ne güzel! Dün akşamı hatırlamak bile iyi hissettiriyor, değil mi? 😊  Belki o anı not almak istersin — "2026-08-08 akşamı çok güzeldi" gibi kısa bir not kaydedebilirim. Ya da sadece sohbet etmek istiyo`
- `kon-06`: `Bilgisayarların çalışma prensibi, donanım ve yazılımın birlikte iş birliği yapmasıyla açıklanabilir. Temel olarak şu adımları izlerler:  **1. Donanım Katmanı (Fiziksel Bileşenler)** *   **İşlemci (CPU`
- `kon-07`: `Anlıyorum, bazen her şey bir arada gelince kafası karışabiliyor. Sana nasıl yardımcı olabilirim? Birlikte adım adım ilerleyebiliriz.`
- `kon-08`: `Maalesef ses seviyesini ayarlama yetkim yok; bu, cihazın kendi ses kontrolleriyle yapılır. Telefonun yanındaki ses tuşlarını veya ekran üstündeki ses çubuğunu kullanarak sesi düşürebilirsin.`
- `kon-09`: `Evet, belirli bir şehir için güncel hava durumunu kontrol edebiliyorum. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Hatırlatıcı (görev) oluşturduğunda şu adımlar gerçekleşir:  1. **Kayıt:** Belirttiğin zaman (`due`) ve metin (`message`) bir zamanlanmış görev olarak sisteme yazılır. 2. **Bekleme:** Görev, `task_list`
- `kon-11`: `Evet, notların yalnızca bu sistemde saklanıyor ve seninle paylaşılmıyor. Başka bir kullanıcı veya üçüncü taraf notlarına erişemez. İstersen mevcut notlarını listeleyebilirim ya da yeni bir not ekleyeb`
- `kon-12`: `Rehber, bu sistemde tanımlı kişilerin adlarını ve telefon numaralarını tutan bir listedir. Şu anki rehberdeki kayıtları görmek için `contact_get` aracını kullanabilirim; kişi eklemek, güncellemek veya`
- `kon-13`: `Anlaşıldı, hatırlatıcı için şimdilik bir şey yapmıyorum. Başka bir konuda yardımcı olmamı istersen söylemen yeterli.`
- `kon-14`: `Anladım, sorun değil. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `kon-16`: `Not aldım: Ali ile dün (8 Ağustos 2026) konuştunuz ve durumu iyiydi. Başka bir şey yapmamı ister misiniz?`
- `kon-17`: `Gerçekten de zaman bazen inanılmaz hızda akıyor, değil mi? Özellikle yoğun ve keyifli geçen günlerde saatler adeta uçuşuyor. 😊  Bugün 9 Ağustos 2026, sabah 09:00 (UTC). Yeni bir güne daha başladın! Um`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmez ve bu çok normal. Bazen küçük bir başlangıç bile işleri kolaylaştırır. İstersen bugün için hafif bir çalışma planı çıkarabilirim ya da sadece dinlenmeyi tercih edebi`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği** — 14 yanıt:

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

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği** — 15 yanıt:

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

**Qwen3.8-27B-IQ4_XS × json × ölçüm öneği** — 16 yanıt:

- `tek-01`: `Şu an saat 09:00 (UTC).`
- `eks-01`: `Hangi şehir için hava durumunu istersin?`
- `eks-02`: `Hangi notu silmemi istersiniz? Notların listesini çıkarayım, numarasını seçebilirsin.  <tool> {"name": "note_search", "arguments": {}}`
- `eks-03`: `Hangi cihazı uyandırmamı istersiniz? Cihazın yapılandırmadaki adını belirtirseniz `wake_on_lan` komutunu çalıştırabilirim.`
- `eks-04`: `Hatırlatıcı için birkaç bilgiye ihtiyacım var:  1. **Ne zaman** hatırlatmamı istersiniz? (tarih ve saat, UTC) 2. **Hangi konuda** hatırlatılacak? (kısa bir mesaj)  Örnek: "Yarın 14:00'te 'Toplantıya h`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini belirtir misin? Önce mevcut görevleri listeleyeyim:  <tool> {"name": "task_list", "arguments": {}}`
- `eks-06`: `Hangi kişiyi silmemi istersiniz? Lütfen adını belirtin.`
- `eks-07`: `Rehbere eklemek istediğiniz kişinin adını (ve varsa telefon numarasını) belirtir misiniz?`
- `yok-01`: `Rica ederim! Başka bir konuda yardıma ihtiyacın olursa çekinmeden sorabilirsin. İyi günler dilerim! 😊`
- `yok-02`: `Merhaba! Ben bir yapay zeka asistanıyım, bu yüzden duygularım yok ama sana yardımcı olmak için buradayım ve her zaman hazırım. 😊  Sen nasılsın? Bugün senin için ne yapabilirim?`
- `yok-03`: `Tabii, buyur:  Neden programcılar karanlıkta kalamaz?  Çünkü "bug"lar (hatalar) onları çok rahatsız eder! 😄`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Tamam, sorun değil! Başka bir konuda yardımcı olmamı istersen buradayım. 😊`
- `yok-06`: `Merhaba! Ben senin kişisel dijital asistanıyım. Sana günlük işlerinde yardımcı olmak için buradayım.  Yapabileceklerimden bazıları şunlar:  *   **İletişim:** Rehberindeki kişileri listeleyebilir, yeni`
- `yok-07`: `Dört eder.`
- `yok-08`: `Tabii, ne zaman istersen daha yavaş ve net bir şekilde anlatırım. Sana nasıl yardımcı olabilirim?`

**Qwen3.8-27B-IQ4_XS × json × kontrol × ölçüm öneği** — 17 yanıt:

- `kon-01`: `İyi geceler! 😊`
- `kon-02`: `Anladım! Size nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim! Başka bir konuda yardımcı olmamı istersen buradayım. İyi günler dilerim.`
- `kon-05`: `Ne güzel! Dün akşamı biraz daha anlatır mısın? Nerede, kiminle ya da ne yaptığınla ilgili birkaç detay verirsen, istersen bunu bir not olarak kaydedebilirim.`
- `kon-06`: `Bilgisayarların çalışma prensibi, donanım ve yazılımın birlikte iş birliği yapmasıyla açıklanabilir. Temel olarak şu adımları izlerler:  **1. Donanım Katmanı (Fiziksel Bileşenler)** *   **İşlemci (CPU`
- `kon-07`: `Anlıyorum, bazen her şey bir arada gelince kafası karışabiliyor. 😊  Neyi netleştirmememi istersin? Örneğin:  - **Ders programın** bugün nasıl? - **Bekleyen görevlerin** var mı? - Bir **not** mu arıyor`
- `kon-08`: `Maalesef ses seviyesini ayarlama yetkim yok; bu, cihazın kendi ses kontrolleriyle (fiziksel tuşlar, yazılım ayarları vb.) yapılması gereken bir işlem.  Sesle ilgili başka bir konuda yardımcı olabilir `
- `kon-09`: `Evet, belirli bir şehir için güncel hava durumunu kontrol edebilirim. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Hatırlatıcı (zamanlanmış görev) kurduğunda sistemde şunlar olur:  1. **Görev oluşturulur:** `task_create` aracı, belirttiğin zaman (`due`) ve metin (`message`) ile bir zamanlanmış görev kaydeder. Bu b`
- `kon-11`: `Evet, notların yalnızca bu sistemde saklanıyor ve buradan dışarıya aktarılmıyor. Notlarını sadece seninle çalıştığım bu ortamda görüyorum; üçüncü kişilerle paylaşılmıyorlar.  İstersen mevcut notlarını`
- `kon-12`: `Rehber, bu sistemde tanımlı kişilerin adlarını ve telefon numaralarını tutan bir listedir. Üzerinde şu işlemleri yapabiliriz:  - **Listeleme / arama:** `contact_get` ile tüm kişiler veya belirli bir a`
- `kon-13`: `Anlaşıldı, hatırlatıcı kurmayacağım. Başka bir konuda yardımcı olmamı ister misin?`
- `kon-14`: `Anladım, sorun. Başka bir konuda yardımcı olmamı istersen buradayım.`
- `kon-16`: `Not olarak kaydedeyim mi?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı geçiyor! 😄  Bugün **9 Ağustos 2026** ve saat **09:00 UTC**. Yeni bir güne hoş geldin!  Günün nasıl geçmesini istersin? Bir planın var mı, yoksa birlikte bir şeyler mi o`
- `kon-18`: `Anlıyorum, bazen motivasyon gelmez ve bu çok normal. Bazen küçük bir başlangıç bile işleri kolaylaştırabilir.  İstersen bugün için ders programına bakıp en azından kısa bir plan çıkarabilirim ya da ha`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği** — 13 yanıt:

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

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği** — 15 yanıt:

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

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × ölçüm öneği — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `Bu işlem geri alınamaz. Ali'yi rehberden silmemi onaylıyor musun?`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × ölçüm öneği — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği — 9/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat dokuz, sabah.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> weather --city Ankara`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T14:03:11Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): body: 'kütüphane kitabını ayın on beşine kadar geri ver' beklenirken 'Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim' geldi — çıktı: `<tool> note_create --body Kütüphaneden aldığım kitabı ayın on beşine kadar geri vereceğim`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği — 3/18

- `kon-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-16` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`

### Qwen3.8-27B-IQ4_XS × json × ölçüm öneği — 3/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat 09:00 (UTC).`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × kontrol × ölçüm öneği — 1/18

- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği — 8/50

- `tek-01` (tek tool): date_time beklenirken çağrı üretilmedi — çıktı: `Şu an saat dokuz, sabah.`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaustu"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `cok-02` (çok tool): date_time beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:03:11Z", "message": "Annemi ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği — 3/18

- `kon-05` (tool gerekmez): düz metin beklenirken note_create çağrıldı — çıktı: `<tool> {"name": "note_create", "arguments": {"body": "Kullanıcı dün akşamın çok güzel geçtiğini söyledi."}}`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `kon-16` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`

---

## Okuma (2026-08-15)

**Bu raporun sorusu tek:** ölçüm bugüne kadar üretimde hiç kurulmayan bir önekle mi
koşuyordu, ve o fark sayıları oynatıyor mu. P27 cevabı önceden yazmıştı: "oynarsa bulgu
odur". **Oynuyor.**

| | ölçüm öneği | üretim öneği |
|---|---|---|
| altın küme, CLI | %98 [90–100] | %92 [81–97] |
| altın küme, JSON | %98 [90–100] | %90 [79–96] |
| negatif kontrol, CLI | %94 [74–99] | %83 [61–94] |
| negatif kontrol, JSON | %94 [74–99] | %83 [61–94] |

**Toplamlara bakıp sıralama yapmak yanlış olur — aralıklar çakışıyor** (P7'nin dersi).
Ama bulgu toplamda değil: **aynı senaryolar iki biçimde de düşüyor** ve düştükleri yer
eksen kırılımında toplanıyor. Mekanik olarak okunabilen üç ayrı etki var.

### 1. Eksik argüman ekseni çöküyor: %100 → %71 (CLI), %100 → %57 (JSON)

`eks-01`, `eks-05`, `eks-06`: şehir/ad söylenmemiş, doğru davranış sormak. Ölçüm öneğinde
model soruyordu; üretim öneğinde bir değer seçip çağırıyor (`weather --city İstanbul`).

Sebep büyük ihtimalle rol metninin son cümlesi: **"Tool kullan her zaman lazımsa."**
Ölçüm öneğinde bu cümle hiç yoktu. Faz 0'ın kendi bulgusu — "eksik bilgi sorulmuyor,
uyduruluyor" (`ARCHITECTURE.md` §8.3) — üretimde ölçüldüğünde **daha kötü** görünüyor,
ve bugüne kadarki bütün raporlar bunu göremiyordu.

**Bu bir rol metni düzeltmesi önerisi değil.** §17.1 prompt değişikliğini değerlendirme
kapısına bağlıyor: cümle değişecekse önce bu kolon yeniden koşulur.

### 2. `tek-01` düşüyor ama davranış **doğru olabilir**

"Saat kaç?" → `Şu an saat dokuz, sabah.` Çağrı yok, ve altın küme bunu hata sayıyor.

Oysa üretim öneğinin bağlam bloğu tarihi ve saati **taşıyor** (`tarih/saat: …`, §8.1).
Model onu okuyup cevaplıyor; `date_time` çağırmak fazladan bir adım olurdu. Yani bu satır
modelin hatasını değil, **altın kümenin üretimde geçerli olmayan bir beklentisini**
gösteriyor: küme, bağlam bloğunun saati taşımadığı bir dünyada yazıldı.

**Altın kümeye dokunulmadı** (P25.2'nin kuralı): `docs/faz2-olcum.md`'den bugüne kadarki
her rapor o elli senaryoyla karşılaştırılabilir kalmalı. Beklentiyi değiştirmek yerine
buraya yazılıyor — okuyan bu satırı bir model hatası sanmasın.

### 3. Serbest metin ekseninde düşenlerin çoğu **ilk harf**

`ser-01`, `ser-05`, `ser-06`: model notu düzgün bir cümle olarak yazıyor —
`Süt, ekmek ve yumurta almayı unutma` — beklenti ise küçük harfle başlıyor.
Karşılaştırma birebir ve harf katlaması Türkçe'de `I`/`ı` üzerinde yanlış çalıştığı için
yapılmıyor (`_comparable` yalnızca cümle sonu noktalamasını atıyor).

Rol metni "konuşma dilinde yaz" diyor ve model cümleleri büyük harfle kuruyor; ölçüm
öneğinde bu eğilim yoktu. Yani bu üç satır da **öneğin** ölçüsü, modelin doğruluğunun
değil. `ser-06` bunun dışında: model cümleyi yeniden yazıyor (`Kütüphaneden aldığım
kitabı … geri vereceğim`), o gerçek bir sadakat hatası.

### 4. Negatif kontrolde yeni bir hata şekli: `fact_list`

`kon-05` ve `kon-16` — düz sohbet cümlelerine `fact_list` çağrısı. Ölçüm öneğinde hiç
görülmedi. Öneğe olgu/bellek çerçevesi girdiğinde model "hatırlamaya" davet edilmiş
oluyor. Fazla çağrı bu kümenin tam olarak ölçtüğü şey ve üretim öneğinde artıyor.

### Sonuç

**Bugüne kadarki bütün raporlar, üretimde hiç kurulmayan bir önekle ölçüldü.** Bu, eski
sayıları geçersiz kılmıyor — biçim karşılaştırmaları (CLI ↔ JSON) aynı önekle yapıldığı
için kendi içinde geçerli. Ama "model üretimde şu kadar doğru" diye okunamazlar, ve
`docs/faz2-olcum.md`'den beri öyle okunma riski taşıyorlardı.

İki kolon bundan sonra da yan yana koşulmalı: `--onek olcum --onek uretim`. Eski kolon
karşılaştırma için, yeni kolon üretim hakkında konuşmak için.
