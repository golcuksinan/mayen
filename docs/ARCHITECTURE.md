# Mayen — Mimari

Yerel çalışan, sahibin cihazlarına yayılmış bir asistan. STT → LLM → TTS omurgası üzerine kurulu;
birden fazla cihazdan, birden fazla insanla konuşur, kullanıcı tetiklemeden de iş yapabilir
ve kendi verisini kendi tutar.

Bu doküman Mayen'in tek doğruluk kaynağıdır ve başka bir dosyaya dayanmaz. Her kural kendi
gerekçesiyle yazılır: gerekçesi yazılmamış bir kural, zamanla gereksiz bir karmaşıklık gibi
görünür ve "sadeleştirilir".

---

## 0. Okuma kuralları

Bu dokümanın kendisi için geçerli üç kural. Diğer her bölümden önce gelir.

1. **AÇIK işaretli madde, cevaplanmadan uygulanmaz.** Yerine varsayım konmaz. Bir iş açık bir
   maddeye bağlıysa hangi maddeye bağlı olduğu söylenir ve iş orada durur. Açık maddeler
   §16'dadır; numaraları sabittir. Kapanan madde silinmez: kararı ilgili bölüme işlenir,
   §16'da yalnızca ✅ ve kararın yazıldığı bölüm kalır. Bir karar tek bir yerde yazar; iki
   yerde yazan karar ilk düzeltmede ikiye ayrılır.
2. **Ölçüm karar değildir.** Ölçüm sonucu raporlanır, kararı sahip verir. Ölçümün yanına
   yazılan bir çıkarım, kaydedilirken kolayca karara dönüşür; bu yüzden bir madde ancak
   sahip kapattığında kapanır.
3. **Ölçülmemiş performans iddiası dokümana yazılmaz.** Bir sayı, hangi modelde, hangi
   prompt'ta, hangi kümede ve hangi tarihte ölçüldüğüyle birlikte yazılır. Sıfır "ölçülen
   dilimde yok" demektir, "yok" değil; payda yazılır.

---

## 1. Kapsam

**Ne:** Kişisel bir asistan platformu. Sesle, yazıyla ve bildirim kanallarıyla konuşur; bağlı
cihazları, sahibin makinelerini ve verisini yönetir; zamanlayıcılarla ve olaylarla kendi
kendine tur açabilir.

**Kimlerle:** Tek sahip. Ek olarak sahibin rol verdiği kişiler ve tanınmayan kişiler
sınırlı yetkiyle konuşabilir (§10). Çoklu kullanıcı hesap sistemi yoktur; kişiler sahibin
yönettiği profillerdir.

**Nerede:** Modüller aynı makinede ya da farklı makinelerde çalışabilir. Sahip nerede olursa
olsun erişim yalnızca özel ağ (LAN ya da Tailscale) üzerindendir. Hiçbir modül internete
doğrudan açılmaz.

**Kapsam dışı:** Bulut model kullanımı, internete açık erişim.

---

## 2. Temel ilkeler ve kararlar

### 2.1 İlkeler

- **Tek program, ağdan geçebilecek sınırlar.** Her modül bir port ya da ödünç alınan
  çerçevenin bir servisi arkasında durur. Çekirdek, modülün aynı süreçte mi başka makinede mi
  çalıştığını bilmez. Bölme kararı gerektiğinde
  verilir, yalnızca adaptör değişir. Bunun sonucu: port sözleşmeleri serileştirilebilir veri
  tiplerinden oluşur.
- **Yerleşim config'te belirlenir ve değişebilir** (§3). Bir modülün devreye girip çıkması
  (makine kapanması, bağlantı kopması, yeniden bağlanma) hata değil, normal durumdur.
- **Bağımlılık yönü içeriye.** `core` ve `ports`, `adapters`, `skills` ya da ödünç alınan
  çerçeveyi import etmez (§4).
- **Değişebilecek her şey (model, sağlayıcı, donanım, taşıma) adaptör ya da ödünç alınan
  çerçevenin bir servisi olur**, çekirdeğe girmez. Seçim config'te yapılır, kodda değil.
- **Her yetenek bir sözleşmeyle tanımlanır.** Arayüz, sonuç durumları ve olaylar baştan
  belirlidir. Her sözleşme `schema_version` taşır. Ama bir sözleşme, en az bir gerçek
  gerçeklemeyle çalışana kadar bir tahmindir; ilk gerçekleme onu değiştirebilir (§17).
- **Yetki kodda uygulanır.** Güvenlik, modelin talimata uymasına bırakılmaz (§10.3).
- **Her şey yerelde çalışır.**
- **Dil yalnızca modelden gelir; sistemin sesi sözsüzdür.** Sistem kullanıcıya önceden
  yazılmış bir cümle seslendirmez, dili kalıpla ya da anahtar kelimeyle yorumlamaz; durumu
  ve eylemi kısa geri bildirim sesleriyle bildirir. Ekranda veri gösteren arayüz metni
  (bildirim, düğme, plan) konuşma değildir ve bu kuralın dışındadır. Sabit bir cümle ya da kalıp, dili
  modelin yerine sistemin taklit etmesidir ve ilk beklenmedik durumda yanlış konuşur.
- **Kapsam sahibin ihtiyacına göre, kavramlar herkese göre.** Ne yapılacağına sahibin ihtiyacı
  karar verir; nasıl adlandırılıp tanımlanacağına "başka biri kendi hayatıyla kursa" sorusu.
  Bir kavram tek bir kişinin hayatından ya da tek bir örnekten çıkarılmaz ve kaynağıyla
  tanımlanır. Sahibe özgü olan her şey config'te ve profilde durur. Aksi hâlde ilk farklı
  durumda kavramın yanına bir kardeşi eklenir ("ev" yetmeyince "okul", sonra "dışarı").
- **Her şey sahte adaptörle test edilebilir.** Tur akışı, politika ve ajan mantığı GPU'suz,
  saniyeler içinde test edilir (§15.1).

### 2.2 Kararlar tablosu

| Konu | Karar |
|---|---|
| Uygulama dili | Python (asyncio), uv |
| Çekirdek | Ses hattı, söz kesme, sıra alma ve tool çağırma ödünç alınan çerçeveden (Pipecat); oturum, tetikleyici, yetki, onay ve depolar onun üstünde Mayen'in katmanı. Sürüm sabittir; güncelleme, kayıtlı senaryolar yeni sürümde koşulduktan sonra verilen bir karardır |
| Model yerleşimi | LLM, STT, TTS, konuşmacı tanıma, karar modeli ayrı süreçlerde; çekirdek model yüklemez |
| Modül yerleşimi | Config'te; aynı süreç ya da ağ üzerinden, sözleşme aynı |
| Taşıma | Ödünç alınan çerçevenin taşıması (WebSocket ya da WebRTC); istemci türüne göre config'te seçilir |
| Ağ sınırı | Özel ağ (LAN, Tailscale); modüller arası ek kimlik doğrulama yok |
| Eşzamanlılık | Mimari paralel turu destekler; oturum ve bağlam istemci başına |
| Tetikleme | Turu bir `Trigger` başlatır; dört öncelik seviyesi |
| STT | Sürekli çalışır, transkript her zaman kaydedilir; LLM yalnızca tetiklenince |
| Tool çağırma biçimi | Modelin kendi tool-calling şablonu; çağrılar liste olarak döner |
| Tool kataloğu | Sabit, herkes için aynı; yetki çağrı anında kodda uygulanır |
| Roller | owner / acquaintance / system / unknown |
| Etki sınıfı | READ / WRITE / EXTERNAL / IRREVERSIBLE / DANGEROUS, artı hassasiyet ekseni |
| `bash` | Sıradan bir skill; kendi izole alanında, gerçek dosyaların kopyası üzerinde, ağsız; WRITE sınıfında |
| Onay | Niyet onayı (sesle) ve kimlik onayı (kişisel cihazdan) |
| Çıkış dili | Kişi profilinde bir tercih |
| Bellek | Tek ortak havuz, kişi etiketli, hassasiyet işaretli |
| Kaçırılan zamanlayıcı | Gecikme toleransı içindeyse açılışta bir kez çalar, değilse "kaçırılanlar" özetine girer |
| Yapılandırılmış veri | SQLite, tek sahibi depo adaptörü |
| Config | Tek YAML; prompt/kişilik ayrı dosya; gizli bilgiler ortamda |

---

## 3. Topoloji ve yerleşim

```
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │ mikrofon     │  │ telefon      │  │ panel        │   istemciler
          │ istemcisi    │  │ (kanal)      │  │              │
          └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                 │ taşıma          │ taşıma          │ taşıma
                 ▼                 ▼                 ▼
          ┌──────────────────────────────────────────────────┐
          │ çekirdek                                         │
          │ ses hattı · söz kesme · sıra alma · tool döngüsü │
          │   (ödünç alınan çerçeve)                         │
          │ oturumlar · tetikleyici · yetki · onay · DND     │
          │ skill'ler · depo adaptörü (SQLite, tek sahip)    │
          └──┬────────┬────────┬────────┬────────┬───────────┘
             │        │        │        │        │   servis + adres (config)
             ▼        ▼        ▼        ▼        ▼
           ┌────┐  ┌─────┐  ┌─────┐  ┌─────────┐ ┌───────┐
           │LLM │  │ STT │  │ TTS │  │konuşmacı│ │ karar │   model süreçleri
           └────┘  └─────┘  └─────┘  └─────────┘ └───────┘
```

Kutular mantıksal modüllerdir; hangisinin hangi makinede durduğu config'tedir.

**Model süreçleri çekirdeğin dışındadır; model ve boyutu config'te seçilir.** Kurulumların
donanımı farklıdır: belleği az olan bir kurulum, kod değiştirmeden daha küçük bir model
kullanır. Ayrı süreç buna üç şey ekler: bir model çökerse ya da belleği taşarsa çekirdek ayakta
kalır; model değiştirmek çekirdeği yeniden başlatmaz; modeli başka makineye taşımak bir adres
değişikliğidir.

**Yapılandırılmış verinin tek sahibi depo adaptörüdür.** SQLite dosyasını başka hiçbir süreç
açmaz; veriye ihtiyacı olan her şey depo portundan geçer. Modüller dağıldığında bu kural
gevşemez, tersine daha önemli olur.

---

## 4. Katmanlar

```
ports/         yalnızca Mayen'in kendi arayüzleri ve sözleşme veri tipleri (depo, tetikleyici,
               kanal, karar, iş ve zamanlayıcı)
core/          oturum, tetikleyici, öncelik/kuyruk, durum kuralları, ortak saat; yetki kararı,
               onay planının kararı, rahatsız etme politikası
skills/        her biri bağımsız, bir dosya (bash dahil)
adapters/      storage/ trigger/ channel/ decider/
pipeline/      ödünç alınan çerçeveye bağlanan her şey: hattaki işlemciler (onay kapısı,
               proaktif kapı, girdi eleme), bağlam ve istek hazırlayan model servisi, yetki
               sarmalayıcısı, model servislerinin istemcileri
app/           giriş noktası: config'i okur, adaptörleri ve servisleri seçer, her şeyi bağlar
replay/        tekrar oynatma ve mock tool adaptörleri
clients/       mikrofon, klavye, masaüstü, telefon istemcileri
panel/         gözlem arayüzü; Python değil, depo kökünde ayrı bir web projesi (§14)
services/      model süreçleri (STT, TTS); her biri depo kökünde kendi bağımlılıklarıyla ayrı
               bir proje (§3)
config/        YAML + prompt dosyaları (kod değil)
```

**Bağımlılık yönü içeriye doğrudur.** Bir iç katmanın dış katmandan bir şeye ihtiyaç duyması,
sınırın yanlış çizildiğinin işaretidir; import eklenerek değil sınır düzeltilerek çözülür.
Olağan çözüm, iç katmanda tanımlanan bir `Protocol` ve onu dışta gerçekleyen bir sınıftır.

**İzin verilen import'lar** (tablonun dışındaki her import yasaktır):

| Katman | Import edebilir |
|---|---|
| `ports` | — |
| `core` | `ports` |
| `skills` | `ports` |
| `adapters` | `ports` |
| `pipeline` | `ports`, `core`, ödünç alınan çerçeve |
| `app` | hepsi |
| `replay` | `ports`, `core`, `pipeline`, `skills` |
| `clients` | `ports` |
| `services` | — (Mayen'in hiçbir katmanı) |

- **Ödünç alınan çerçeve yalnızca `pipeline` ve `app`'te import edilir.** Çerçevenin sürüm
  güncellemesinin dokunduğu yüzey tek katmanla sınırlı kalır, yetki ve onay kararları
  çerçevesiz test edilir ve çerçeve bırakılırsa yalnızca bu katman yeniden yazılır.
- **Karar `core`'da, hatta uygulanışı `pipeline`'dadır.** Onay planının ne olduğu ve neyin
  onay sayıldığı `core`'un kararıdır; hattaki kareleri tutmak, yutmak ve itmek `pipeline`'ın
  işidir. İkisi aynı yerde dururken karar ancak hattı çalıştırarak test edilebilir.
- **Bağlama tek yerde yapılır.** Somut adaptörleri, servisleri ve skill'leri tanıyan tek
  katman `app`'tir; geri kalan her şey yalnızca portları görür. İkinci bir bağlama noktası,
  sözleşmeyi atlayan ikinci bir yol demektir.
- **`skills` ile `adapters` birbirini görmez.** Tool *ne* istendiğini bilir, *nasıl* yapıldığını
  port arkasındaki adaptör bilir (§9.5).
- **Model servisleri çekirdeğin kodunu görmez, çekirdek de onlarınkini;** aralarında yalnızca
  ağ vardır. Sözleşme `ports`'tadır ve servis onu kendi kodunda aynen kurar. Model
  kütüphaneleri çekirdeğin ortamına girseydi ayrı süreç (§3) yalnızca kâğıtta kalırdı. Ses
  birimine çevirmek sesin işidir ve servistedir; hangi parçanın hangi dilde okunacağını
  söyleyen işaret (§7) hatta okunur.
- **İstemciler ve panel ayrı süreçlerdir**; çekirdeğe yalnızca taşımayla bağlanır (§13),
  çekirdeğin koduna değil. Python'da yazılmayan bir istemci ya da panel, `ports`'taki
  sözleşmeyi kendi dilinde aynen kurar ve sürümü tutmayan mesajı göstermez.

**Mekanik olarak zorlanır:** bir test, kaynağın AST'sini gezer ve tabloda olmayan her
import'ta kırılır. Test tablonun döngüsüz olduğunu da doğrular; döngü, iki katmanın aslında tek
katman olduğunu gizler. Aynı test **SQL'in depo adaptörü dışında geçmesini** de yasaklar. Bir
kural ancak onu zorlayan bir şey varsa gerçektir.

**Adlandırma:** API adları ve alan sözlüğünün değerleri (durumlar, etki sınıfları, roller,
sonuç durumları) İngilizcedir; bu doküman Türkçe yazılır ama değerleri koddaki biçimiyle
geçirir. Değerler tool sonuçlarında modele de gider (§8.6); iki dilli bir sözlük her sınırda
bir çeviri tablosu ister ve tablo unutulan yerde modele Türkçe bir değer sızar.

---

## 5. Çekirdek: tetikleyici, tur ve oturum

### 5.1 Tetikleyici tabanlı tur

Turu mikrofon değil bir `Trigger` başlatır. Tetikleyici bir kaynaktan gelir: ses (wake
word, anahtar kelime), yazılı mesaj (klavye, kanal), zaman (zamanlayıcı) ya da iç olay (event
bus'ta yayılan bir olay, örneğin uzun süren bir tool'un bitmesi). Tetikleyici adaptörleri bu
kaynaklardan beslenir; yeni bir girdi yolu yeni bir adaptördür, yeni bir tetikleyici türü
değil. Her tetikleyici bir **öncelik** (`urgent`, `high`, `normal`, `low`), bir **oturum** ve
bir **kaynak** taşır.

**Tetikleme ile yetki ayrı eksenlerdir.** Tetikleyici turun açılıp açılmayacağına karar verir
("bu söz bana mı söylendi"); rol, tur açıldıktan sonra neyin yapılabileceğine karar verir
(§10). STT'nin sürekli akması LLM'in her sese cevap vermesi demek değildir: gürültüyü
tetikleyici katmanı eler.

### 5.2 Oturum ve eşzamanlılık

- Her tur bir oturum kimliği ve bir `turn_id` taşır. `turn_id` sayaç değil uuid'dir: kayıtlar
  süreçten uzun yaşar ve tekil olmak zorundadır.
- **Oturum ve bağlam istemci (cihaz) başınadır.** Turlar birbirinden yalıtılır, global tek
  durum yoktur. Örnek: sahip kendi cihazından yazarken, aynı anda başka biri başka bir
  cihazdan konuşur.
- Aynı anda kaç turun koştuğu bir config değeridir; mimari birden fazlasını destekler.
  Model sunucusunun kapasitesi sınırlıysa LLM istekleri fiziksel olarak sıraya girer; bu bir
  kaynak kısıtıdır, mimarinin değil.
- Paylaşılan kaynaklar (aynı hoparlör, aynı cihaz) turlar arasında
  çakışabilir. İki turun aynı cihaza çelişen eylem vermesi **AÇIK** (§16.11).

### 5.3 Kesme ve kuyruk politikası

Tur sürerken yeni bir tetikleyici gelirse önceliği yüksekse mevcut turu keser, düşükse sıraya
girer. Ses turunda konuşan sahipse yalnızca `urgent` keser; konuşan başkasıysa her yüksek
öncelikli tetikleyici keser. Sahip birincil kullanıcıdır: başkasının turu sahibe ait bir
tetikleyiciyi bekletmez, sahibin kendi turunu ise yalnızca acil bir durum böler. Kesilen
turun akıbeti turu açan tetikleyicinin kaynağına göre config'ten seçilir:

- iptal edilir ve bağlama "yarıda kesildi" notu düşer,
- sıranın başına eklenip baştan başlar,
- kaldığı yerden devam eder.

**Ödünç alınan çerçevenin karşılamadığı bir akıbet config'te seçilirse açılış hata verir.**
Sessizce başka bir akıbete düşen ayar, kesilen turun ne olacağını config'i okuyana yanlış
söyler.

**İptalin kapsamı turdur, kuyruğun tamamı değil.** Kesme yalnızca o `turn_id`'ye ait işleri
ve ses parçalarını düşürür. Aksi hâlde bir turu kesmek, kuyrukta bekleyen bir hatırlatmayı da
sessizce çöpe atardı ve kimse fark etmezdi.

### 5.4 Durum makinesi

Tur durumları: `LISTENING` → `THINKING` → `SPEAKING`, ayrıca `AWAITING_CONFIRMATION` ve
`ENROLLING`. Turu olmayan oturum `IDLE` durumundadır. Durumlar oturum başınadır.

**Durum her değiştiğinde `state.changed` olayıyla yayınlanır.** İstemci ve panel durumu olay
sırasından kendisi çıkarmaz; aynı çıkarımı her istemci ayrıca yazsaydı istemciler zamanla
ayrışırdı. Yazılı hatta ses olmadığından istemciye metin gitmesi konuşmak sayılır.

**İlk üç durumu ödünç alınan çerçevenin kareleri yürütür; kapalı durumlar Mayen'indir.**
Sözün başlaması, bitmesi, söz kesme ve asistanın konuşmaya başlayıp bitirmesi çerçevenin
kendi işidir ve Mayen bunları onun olaylarından okur. Sözün bittiğine nasıl karar verildiği
**AÇIK** (§16.2).

Kurallar:

- **Yazılı mesaj `LISTENING`'den geçmez.** Klavye ve kanal mesajı tek parça gelir, beklenecek
  bir devamı yoktur; doğrudan `THINKING`'e geçer.
- **Tetikleyiciden sonra konuşma gelmezse tur sessizce kapanır.** Süre config'tedir. Yanlış
  tetiklenen wake word cevapsız kalmalıdır; karşıda kimse yokken konuşmak onay zaman
  aşımındaki hatanın aynısıdır.
- **Önce durum, sonra cümle.** Onay gerekiyorsa tur onay cümlesi okunmadan önce
  `AWAITING_CONFIRMATION`'a girer. Kullanıcı okuma bitmeden söze girerse ses durur ama durum
  değişmez ve bekleyen plan yaşar.
- **`AWAITING_CONFIRMATION` ve `ENROLLING` kapalı durumlardır.** İçlerindeyken gelen metin
  modele gitmez; yalnızca onay çözümleyicisine ya da kayıt akışına gider. Çerçevenin boş
  turu kurtarmak için modeli kendiliğinden çalıştırdığı yollar da bu durumlarda kapalıdır.
- **Önce sebep, sonra durum.** Bir hata, durum değişikliğinden önce ayrı hata kanalından
  gider. İstemci `IDLE` durumunu hatadan önce görürse turun sessizce bittiğini sanır.
- **Boş yanıt ile sessiz kalmak farklıdır.** Sessiz kalmak, LLM'in açıkça seçebildiği meşru bir
  çıktıdır (§7). Boş yanıt ise bir arızadır: sebep hata kanalından bildirilir, tur `error`
  ile kapanır, duyulmamış yanıt geçmişe yazılmaz.
- Onay zaman aşımı turu bitirir; karşıda kimse olmadığı için konuşulmaz.

### 5.5 Olay zarfı ve ortak saat

Durum değişimleri, tool çağrıları ve sonuçları olay olarak kaydedilir. Geri bildirim sesleri,
panel ve gözlem bu olaylara abone olur. Olaylar, ödünç alınan çerçevenin gözlemcisinin
gördüğü karelerden ve Mayen'in kendi katmanından üretilir; ayrı bir olay altyapısı kurulmaz.

**Her olay aynı zarfı taşır: sabit bir başlık ve türe özgü bir gövde.**

- **Başlık** (her olayda aynı, çekirdek doldurur): olay kimliği, tür (`tool.finished`,
  `stt.segment`, `state.changed` gibi), kaynak bileşen, oturum ve tur kimliği, zaman, süre,
  durum ve olayın ilgili olduğu kayıtların kimlikleri (boş olabilir). Durumu olayı üreten
  bileşen bildirir, çekirdek başlığa yazar. İlgili kayıtlar başlıktadır, çünkü sil bir kaydın
  olay kaydındaki kopyalarını gövdeyi okumadan bulabilmelidir (§11.4).
- **Gövde** (türe özgü, olayı üreten bileşen doldurur): tool için sonuç zarfının skill kısmı
  (§9.1), STT için metin ve skor, LLM için token sayıları gibi.

Olay kaydı, panel, replay ve gözlem aynı biçimi okur; her aşamanın süresi aynı biçimde
kaydedildiği için gecikmenin aşama aşama dökümü ayrı bir araç gerektirmez. **Log yalnızca
başlığı yazar, gövdeyi yazmaz** (§14): içerik yalnızca olay kaydında durur ve unut ile sil
oraya ulaşır. Zarf olan şeyin kaydıdır; bileşenlerin birbirini çağırması zarftan geçmez.
Tüm modüller zaman damgasını ortak saatten alır; damgalar ISO-8601 UTC, tek biçim ve tek
yerde (iki biçim, kimsenin fark etmediği bozuk bir sıralama demektir). Makineler arası saatin
nasıl ortak tutulduğu **AÇIK** (§16.13).

### 5.6 İptal ve akış

Akış ve iptal ödünç alınan çerçevenindir: her aşama akışlıdır ve söz kesme kareleri bütün
hattan geçer. Mayen'in hatta duran kodu (onay kapısı, tool gövdeleri) da iptal edilebilir
yazılır; iptal edilebilirlik sonradan eklenemez. Yarıda bırakılmaması gereken iş etki sınıfı
kuralına uyar (§8.8).

---

## 6. Girdi ve duyular

| Alan | Ne var |
|---|---|
| **Ses girişi** | Çok tüketicili akış (STT + kayıt + konuşmacı tanıma). Çalınan sesi referans olarak alabilir |
| **Echo cancellation** | Donanımda, istemcide ya da yazılımda; hattın ses girişinden önce. AEC yoksa istemci yarım dubleks çalışır (asistan konuşurken mikrofon kapalı); bu söz kesmeyi öldürür, yani bir kaçış yolu, çözüm değil |
| **Sürekli STT** | STT sürekli çalışır, transkript her zaman kaydedilir. Sunucuya sürekli ses akar; taşıma biçimi **AÇIK** (§16.9) |
| **Wake word** | Bir tetikleyici adaptörü. Motor, kelime ve nerede çalıştığı **AÇIK** (§16.8) |
| **Konuşmacı tanıma** | Bir adaptör. Sonucu bir **skordur**, iddia değil; skor bir eşleşme seviyesine çevrilir. Bağlamda `speaker` alanı olur ve yetkilendirmede profile eşlenir |
| **Genel medya** | Duyu girişi sese özel değil. Kayıt deposu medya türünden bağımsız, `media_id` referansı, LLM mesajında medya parçası |
| **Kamera ve vision** | Medya hattının adaptörleri |
| **Girdi eleme** | Metin seviyesinde (boş, çok kısa, düşük STT skoru). Karar modelini kabul edecek şekilde tasarlıdır |

**Kimlik bilgisi kullanıcının metnine yazılmaz.** Kullanıcı metni ve kimlik ayrı alanlarda
taşınır; kimlik prompt'a yalnızca sistemin kontrol ettiği bağlam bloğunda girer.
Kullanıcının söyleyebildiği hiçbir şey kimlik alanını taklit edemez.

---

## 7. Çıktı ve kanallar

| Alan | Ne var |
|---|---|
| **TTS** | Metin akışı cümle sınırında otomatik olarak TTS'e gider. `speak` tool'u yoktur |
| **Sessiz kal** | LLM'in açık ve meşru bir çıktısı; boş çıktıdan ayrı bir durum (§5.4) |
| **TTS dışı ses** | Ses çıkışı herhangi bir medyayı kabul eder |
| **Geri bildirim sesleri** | Durum olaylarına abone olan bir modül |
| **Kanallar** | Çıkış sese özel değil: bildirim, mesaj gibi kanallar. Aynı kanaldan yazılı komut da alınır. Kimlik onayı bildirimleri (§10.5) bu kanaldan gider ve yanıt aynı kanaldan alınır |

**TTS gerçek zamandan hızlı üretmek zorundadır.** Cümleye bölme ve sıralı seslendirme ödünç
alınan çerçevenin işidir; çerçeve bir cümle çalınırken sıradakini üretir ve yavaş bir TTS'te
cümleler arasında boşluk kalır, ses kesik duyulur.

**TTS sesinin dilinde olmayan parçayı model işaretler; işaretli parça kendi dilinin okunuşuyla
ses birimlerine çevrilip aynı sese verilir.** Kişi adları, not gövdeleri ve ders adları
kullanıcının dilinde kalır (§8.6), ses ise çıkış dilindedir; işaretsiz okunan bir ad
tanınmaz hâle gelir. Hangi parçanın hangi dilde olduğunu yalnızca model söyler (§2.1). İşaret
seslendirilmez, cevabın metin çerçevesinde de görünmez. Ses biriminin hedef seste karşılığı
yoksa en yakın birime çevrilir; atılan bir birim, sesi sessizce bozar.

**Cevabın metni istemciye sesten ayrı gider**, cümle başına ve o cümlenin sesinden önce. Metin
gitmezse istemci cevabı yalnızca sesten öğrenebilir ve bir metin arayüzünde hiç gösteremez.

**`PERSONAL` içerik ortak cihazda verilmez, kişinin kendi cihazına gider.** Ortak bir cihazda
istenen kişisel bir cevap, içeriğin ait olduğu kişinin kişisel cihazına (§10.1) gönderilir ve
konuşma o cihazdaki oturumda sürer; ortak cihaz yalnızca nereye gönderildiğini söyler.
`PERSONAL` içerik ortak cihazın oturumuna hiç yazılmaz: ortak cihazda bir tool sonucu yalnızca
`GENERAL` kayıtları taşır, `PERSONAL` kayıtlar kişinin cihazına gider ve modele kaçının
gönderildiği söylenir (§9.1). Ortak cihazın önünde kimin olduğu
ve kimin duyduğu bilinemez; kişisel içerik ortak cihazın bağlamına girmediği için sonradan
gelen birine de sızamaz. Kişisel cihazı olmayan kişiye kişisel içerik verilmez: güvenle
ulaştırılacak bir yer yoktur. Kural proaktif çıktı için de geçerlidir; bir hatırlatıcı
çaldığında belirleyici olan kaydın kendi etiketidir (§12).

**Kısmi çalışma desteklenir.** LLM ayakta ama TTS yoksa yanıt metin olarak gösterilir. TTS
ölünce sesli bildirim de mümkün değildir; bu yüzden arayüz bildirimi sese yedek değil, ona
paralel bağımsız bir kanaldır.

---

## 8. LLM ve bağlam

### 8.1 Mesaj modeli

Modele giden mesaj listesi ödünç alınan çerçevenin bağlamıdır (rol, içerik, tool çağrıları ve
sonuçları); sağlayıcı biçimine çeviriyi çerçevenin model servisi yapar. Mayen bu listeye alan
eklemez.

- **Kimin konuştuğu ve ne zaman olduğu olay kaydında, mesaj başına tutulur** (§5.5). Modele
  şu anki konuşan bağlam bloğunda gider (§6). Geçmişteki her mesajın kimden geldiğini modele
  göstermek ancak aynı oturumda birden çok kişi konuştuğunda gerekir ve konuşmacı tanımaya
  bağlıdır (§16.5).
- **Başkasının yazdığı içerik oturumun durumunda işaretlenir, mesajda değil.** Bu işareti
  okuyan model değil yetki kararıdır (§10.6); böyle bir içerik getiren tool sonucu bunu
  bildirir ve oturum, içerik bağlamda kaldıkça işareti taşır.

### 8.2 Model servisi

Model, ödünç alınan çerçevenin model servisinden çağrılır. Akış, çoklu tool çağrısı ve tool
sonucundan sonra modelin yeniden çağrılması onun işidir. Reasoning seviyesi soyut bir
kavramdır; modele nasıl iletildiği model kaydındadır (§8.9).

- **Biçim: modelin kendi tool-calling şablonu.** Katalog isteğin `tools` alanında JSON şema
  olarak gider, çağrıyı sunucu ayrıştırır.
  **Gerekçe bir arıza sınıfıdır.** Metin tabanlı biçimlerde (CLI ya da JSON, gramerle
  kısıtlanmış) dal ilk token'da seçilir: model bir üretimde ya konuşabilir ya çağırabilir.
  İkisini birden istediğinde ("anladım, kuruyorum; ama önce saati almam lazım") çağrıyı düz
  metnin içinde **taklit eder**; hiçbir şey çalışmaz ve taklit sesli okunur. Gramerde bir
  karakteri yasaklamak bunu çözmez, model başka bir kılık bulur: **karakter yasaklamak sınıfı
  değil, kılığını değiştirir.** Yerel biçimde metin ile çağrı aynı yanıtta durabilir.
- Şemanın ürettiği tipli değerler doğrulamadan önce tek bir biçime çevrilir; doğrulama tek
  noktadır, yetki sarmalayıcısındadır ve biçim başına gevşetilmez. Argümanı ayrıştırılamayan
  çağrı da modele hata sonucu olarak döner (§9.1); çerçeve böyle bir çağrıyı sessizce atarsa
  yakalamak `pipeline`'ın işidir.
- **Zorunlu tool modu kullanılmaz.** "Tool gerekli mi" sorusu üretimden önce verilen ikili bir
  karardır; zorunlu mod onu tool dalının içinde çok yollu bir "hangi tool" seçimine çevirir.
  O modda "kullanıcıya sor" diye bir davranış yoktur ve eksik alanı olan istekler yer
  tutucu değerlerle çağrıya dönüşür. Ölçüm olmadan getirilmez.

### 8.3 Sabit önek

```
[sistem promptu (sabit)] [özet (varsa)] [konuşma geçmişi] [bağlam bloğu] [güncel tur]
```

- **Sistem promptu tur içinde değişmez.** Değişken içerik (tarih/saat, konuşan kişi, dil
  tercihi, getirilen olgular) daima sondaki bağlam bloğuna yazılır. Önekin bir baytı bile
  değişirse sunucunun önbelleği düşer.
- **Tarih bağlamda ay adıyla yazılır** ("11 Ekim 2026"). Gün ve ay sayıyla yazılınca ikisi
  de 12'den küçükken model onları karıştırabilir ve yanlış güne iş kurar.
- **Değişken kuyruğun arkasına sabit bir şey de konmaz.** Sabit olmak bir istisna değildir:
  değişken içeriğin arkasındaki her şey her tur yeniden işlenir ve önbellekten yararlanamaz.
  Gecikme üzerine teori kurmadan önce sunucunun bildirdiği prefill token sayısı okunur;
  prefill ile üretimi ayıran odur.
- `[özet]` bloğu tek istisnadır ve **seyrek olmak zorundadır**: tur içinde asla güncellenmez.
- **Tool kataloğu herkes için aynıdır.** Konuşana göre filtrelenmiş bir katalog, konuşan
  değiştikçe öneki değiştirir. Model, bir tanıdığın yapamayacağı bir şeyi denerse ret, tool
  sonucu olarak geri döner.
- **Paralel oturumların önbelleği:** her oturumun kendi öneki vardır. Sunucunun paralel istek kapasitesi ile
  önbelleğin oturumlar arasında nasıl paylaşıldığı ölçülmeden bilinmez (§16.1).

### 8.4 Bağlam hazırlayıcı

LLM'e giden mesaj listesi bir arayüzden geçer: geçmiş, özetleme, kırpma, hafıza ve anlık
durum enjeksiyonu. "Unut" işaretli kayıtlar bağlama girmez. Konuşan kişinin profilinden neyin
eklendiği §11.1'dedir.

- **Anlık durum, onu bilen adaptörün portundan okunur.** Hoparlörde ne çaldığını ses çıkış
  adaptörü, hangi istemcinin bağlı olduğunu oturumlar, makinenin durumunu makine denetimi
  adaptörü bilir. Ayrı bir dünya deposu yoktur: kaynağı olmayan bir depo ancak bayat bir kopya
  olabilir ve kopya kaynaktan ayrıldığı an model yanlış bilgiyle konuşur. `PERSONAL` anlık durum
  (§9.1) bağlama otomatik girmez, yalnızca tool ile ve yetkiden geçerek okunur.
- **Token sayısı tahmin edilmez**, sunucunun sayaç ucuna sorulur ve mesaj başına önbelleklenir.
  Ödünç alınan çerçevenin özetleyicisi ne zaman özetleyeceğine karakter sayısından tahminle
  karar verir; özetleme kullanılırsa bu karar sunucunun son cevapta bildirdiği token sayısıyla
  verilir.
- **Bağlam boyutu model deposunda yazar ve açılışta sunucunun bildirdiğiyle karşılaştırılır;
  uyuşmazlık açılış hatasıdır** (§8.9). Yoksa sunucunun gerçek bağlam boyutuyla uygulama
  birbirinden farklı düşünür ve fark ancak kırpma bozulunca görülür.
- **Kırpma istisnai bir olaydır, rutin değil.** Bütçe aşılırsa en eski mesajlar pencereden
  çıkar ama silinmez; her kırpma bir uyarı ve sayaçla kaydedilir. Sık kırpılıyorsa çözüm daha
  iyi bir kırpma stratejisi değil, bütçenin yanlış olduğunu kabul etmektir.
- **Tool sonucu geçmişe `tool` rolüyle yazılır.** Sonuç geçmişe yazılmaz da veri yalnızca
  asistanın cevabında kalırsa model onu kendi bilgisi sanır ve bir daha çağırmaz. Bir sonucun
  bayatlaması, sonucu gizleyerek değil kaynağını görünür tutarak yönetilir.
- **Bir düzeltme eski geçmişi onarmaz.** Geçmişe yazılmış bir hata, kod düzeltilince
  kendiliğinden gitmez; model bozuk geçmişten öğrenmeye devam eder ve arıza kendini besler.
  Ölçüm boş durumdan başlar, üretim başlamaz.

### 8.5 İstek hazırlayıcı

Hangi reasoning seviyesiyle gidileceğini belirler. Karar
modelini kabul eder (§8.7). Katalog değiştirmez (§8.3).

### 8.6 Dil

Çıkış dili kişi profilinde bir tercihtir. Tanınmayan kişiye config'teki varsayılan dille
konuşulur; kimsenin istemediği turda (zamanlayıcı) dinleyen, oturumun cihazının eşleştiği
kişidir. Onay sorusu da turu isteyenin dilinde yazılır. Dil kuralı değişken bir değer olduğu
için bağlam bloğunun sonunda durur; metni sahibin prompt dosyasındadır, dil yer tutucuyla
girer.

**Modele giden her metin İngilizcedir:** sistem promptu, tool adları, açıklamaları ve
parametreleri, tool sonuçları, bağlam bloğu ve yardımcı çağrıların promptları. Kullanıcının
verisi (not gövdesi, isim, ders adı) verildiği dilde kalır; alan sözlüğünün Türkçe değerleri
(§4) modele İngilizce karşılığıyla gider. Talimatlar tek dilde olunca çıkış dili kuralıyla
çelişmez ve çıkış dili hiçbir metne dokunmadan değişir.

**Prompt'ta bir kuralın konumu bir kaldıraçtır ve rol metni en zayıf konumdur.** Önekin
başındaki tek bir talimat, ondan sonra gelen girdi, geçmiş ve katalog tarafından bastırılır.
Yerel tool biçiminde şablon `tools` bloğunu sistem mesajının arkasına ekler; yani "sistem
promptunun sonu" öneğin sonu değildir. Tutmayan bir kural yeniden yazılmadan önce yanlış
yerde olup olmadığına bakılır.

### 8.7 Karar modeli

Bir durum ve birkaç soru verilir; seçenek, evet/hayır ya da puan olarak olasılıklı bir cevap
döner. Metin üretmez, "LLM'e gitmeye değer mi" gibi hızlı kararlar içindir.

- **Kullanım yerleri:** tetikleyici ("bana mı söylendi"), girdi eleme, reasoning seviyesi,
  araya girme, proaktif hatırlatma, onay katmanı. Rahatsız etme ve erteleme
  kararları bunun dışındadır ve tamamen kural tabanlıdır (§12).
- **Konumu:** tetikleyici, girdi eleme ve istek hazırlayıcı arayüzlerinin bir adaptörüdür.
  Hangi noktalarda kullanılacağı config'ten seçilir; eşikler gözlem kayıtlarıyla ve replay
  ile ayarlanır.
- **Karar modeli tool çağırmaz.** Tool argümanları serbest metin gerektirir; karar modeli
  yalnızca LLM'e gidilip gidilmeyeceğine ve nasıl gidileceğine karar verir.
- **Bilinen riskler:** küçük modeller sıfır atışta zayıf kalabilir ve ince ayar gerekebilir;
  profillerdeki dillerde başarımı belirsizdir. Yalnızca barındırılan bir API olarak sunulan
  modeller kapsam dışıdır, çünkü her şey yerelde çalışır. Model ve eşikler **AÇIK** (§16.10).

### 8.8 Ajan döngüsü

Bir tur, modelin cevabı ile tool çağrılarının sırayla birbirini izlediği bir döngüdür:
istek hazırlanır, model cevap verir; cevapta çağrı varsa çağrılar doğrulanır, yetki
kararından geçer (§10.3), çalışır ve sonuçları geçmişe yazılır; döngü başa döner. Döngüyü
ödünç alınan çerçeve yürütür; doğrulama ve yetki, her tool'un önündeki sarmalayıcıdadır.
Aşağıdaki kurallardan çerçevede olmayanları (adım tavanı, sonuç boyut sınırı, uzun süren
tool'un bildirilmesi) Mayen'in katmanı ekler.

- **Döngü, model çağrı döndürdüğü sürece sürer; çağrısız cevap turu bitirir.** Adım tavanı
  (§9.1) tek dış sınırdır. Modelin dışında bir "bitti mi" kararı, modelin bilmediği bir
  sebeple işi yarıda keserdi.
- **Söz kesilirse çalışan `READ` çağrıları iptal edilir; yan etkili bir çağrı bitirilir ve
  sonucu kaydedilir.** Yarıda kesilen bir yazma, yapılıp yapılmadığı belli olmayan bir durum
  bırakır.
- **Her tool sonucu bir boyut sınırı taşır; sınırı aşan sonuç kesilir ve modele kesildiği
  söylenir.** Bir web sayfası tek başına bağlamı doldurabilir ve modelin onu okuması ilk
  sesi dakikalarca geciktirir. Sınırın değeri **AÇIK** (§16.20).
- **Bağlam özetlenirken sözsüz bir ses çalınır** (§2.1). Özetleme uzun sürebilir ve sessizlik
  takılma gibi duyulur.
- **Her tool çağrısı bitince sözsüz bir ses çalınır.** Ses, tool'un gerçekten çalıştığını
  gösterir: model "baktım" ya da "kurdum" der ama ses gelmezse, cevap uydurulmuştur. Modelin
  sözü bir iddiadır; yapılan işi gösteren şey olaydır.
- **Bir tool belirli bir süreyi aşarsa, bunu kullanıcıya model söyler.** Sistem konuşan role
  (§8.10) yan bir istek gönderir; istekte tool'un adı ve geçen süre vardır, sonucu yoktur. Modelin cümlesi
  seslendirilir ve geçmişe yazılır. Süre config'tedir. Sesli arayüzde sessizlik "duymadı" ya
  da "takıldı" diye okunur; isteğe sonucun konmaması, modelin henüz gelmemiş bir sonucu
  uydurmasını önler.

### 8.9 Model deposu

Kullanılabilecek modeller ve ayarları önceden tanımlanmış bir depoda durur; hangisinin etkin
olduğu `.env`'de seçilir. Model değiştirmek kod değiştirmez.

- **Her model kaydı şunları taşır:** adres, model adı, rol başına (§8.10) örnekleme ve
  düşünme ayarları, düşünmenin nasıl açılıp kapandığı, bağlam boyutu ve modele bağlı
  davranış ayarları. Her sunucu örnekleme
  ayarlarını sağlamaz ya da modelin önerdiği değerleri bilmez; değerleri sunucudan beklemek
  davranışı sunucuya bağlar.
- **Modele bağlı bir davranış farkı kodda model adıyla dallanmaz, model kaydında bir ayar
  olur.** Koda yazılmış bir model adı, her yeni modelde kodu değiştirmeyi gerektirir.
- **Sunucunun kendi yaptığı iş ayar olmaz.** Tool argümanlarının şemaya göre kısıtlanması
  sunucunun işidir; Mayen yalnızca doğru şemayı gönderir ve sonucu yine doğrular (§8.2).

### 8.10 Konuşan ve akıl yürüten

LLM'in iki işi vardır ve ikisi ayrı **rol**dür: **akıl yürüten** (reasoner) tool kararını ve
planlamayı yapar, **konuşan** (talker) kullanıcıya cevabı yazar. Ayrım, hızlı ve yavaş
düşünmeyi ayıran Talker–Reasoner mimarisinden gelir. Zayıf bir modelde tool dışı talimatlar
çağrı isabetini düşürür; roller ayrılınca her rolün prompt'u yalnızca kendi işini taşır.

- **Roller üç kipte çalışır ve kip config'ten seçilir:**
  - **tek:** bir rol iki işi birden yapar; persona ve tool kuralları aynı prompt'tadır.
  - **sıralı:** önce akıl yürüten tool'ları çağırır, metni atılır; sonra konuşan sonuçları
    anlatır ve tool çağıramaz.
  - **paralel:** konuşan hemen cevap verir, akıl yürüten arka planda çalışır; sonuç
    geldiğinde konuşan anlatır (§9.5).

  Hangi kipin iyi olduğu modele göre tersine dönebilir; kip kodda değil config'te seçilir ve
  ölçümle belirlenir.
- **Her rol model deposunda bir modele ve bir sunucu yuvasına eşlenir.** Aynı model iki
  yuvada iki rolü üstlenebilir, iki rol iki ayrı model de olabilir. Her rolün kendi yuvası
  vardır: iki rolün farklı önekleri tek yuvayı paylaşsaydı, her geçiş ötekinin önbelleğini
  düşürürdü.
- **Örnekleme ve düşünme ayarları rol başınadır ve her istekte gönderilir.** Sunucunun
  varsayılanı rol farkını bilmez; akıl yürütenin düşük sıcaklığı ile konuşanınki aynı isteğe
  ait değildir.
- **Modeller ayrıldığında büyük model akıl yürüten roldedir.** Tool kararı ve planlama zor
  iştir; sonucu anlatmak daha kolaydır.
- **Paralel kipte konuşan, elinde sonuç yokken içerik söylemez; yalnızca işin başladığını
  söyler.** Sonucu yalnızca akıl yürüten getirir; aksi hâlde konuşan, gelmemiş bir sonucu
  uydururdu. Paralel kip ölçülmeden açılmaz.

---

## 9. Skill sistemi

### 9.1 Sözleşme

Ortak `ToolSpec`. Her skill şunları bildirir:

- **Ad ve açıklama**: katalogda görünen metin.
- **Argümanlar**: tipli ve doğrulanmış. Kullanım metni imzadan üretilir, yanına ayrıca
  yazılmaz; yoksa doküman koddan sapar.
- **Etki sınıfı** (zorunlu): `READ` | `WRITE` | `EXTERNAL` | `IRREVERSIBLE` | `DANGEROUS`.
  - `READ`: yan etkisi yok (saat, hava durumu, not okuma)
  - `WRITE`: kendi verimizi geri alınabilir şekilde değiştirir
  - `EXTERNAL`: dış dünyada geri alınabilir bir etki (ses seviyesi, medya, uygulama açma)
  - `IRREVERSIBLE`: geri getirilemez (silme, pencere kapatma, Wake-on-LAN); niyet onayı
    ister (§10.3)
  - `DANGEROUS`: sınırı önceden bilinemeyen etki; kimlik onayı ister (§10.3). Bu
    sınıfa girecek bir skill olup olmadığı **AÇIK** (§16.19)

  Etki sınıfı yalnızca yan etkiye bakar: hava durumu dışarıya istek atsa da `READ`'dir.
- **Hassasiyet** (zorunlu): `GENERAL` | `PERSONAL`. Etki sınıfı yan etkiyi ölçer, gizliliği
  ölçmez: "salt okuma" ile "zararsız" aynı şey değildir. Transkript `PERSONAL`'dır. Bir
  kişinin konumu ve varlığı (nerede olduğu, orada olup olmadığı) hangi kaynaktan gelirse
  gelsin `PERSONAL`'dır: kimin nerede olmadığını bilmek, bir yere kimin ne zaman
  girebileceğini bilmektir.
  - **Kayıt tutan tool'larda (not, hatırlatıcı, takvim, rehber, hafıza) hassasiyet her
    kaydın kendisindedir; tool yalnızca yeni kaydın varsayılanını bildirir.** Aynı depoda "çöpü çıkar" ile bir tahlil sonucu yan yana durabilir; tool
    başına tek bir etiket ya birini açığa çıkarır ya da ötekini gereksiz yere gizler.
  - **Çağrının izni, sonuçtaki her kaydı okuma izni değildir.** Kayıt tutan bir tool'un
    çağrısı yetki kararından tool'un etki sınıfı ve varsayılan hassasiyetiyle geçer; sonuçtaki
    her kayıt, çağıranın o kaydın etiketini okuma yetkisine göre süzülür ve modele kaç kaydın
    çıkarıldığı söylenir. Süzülmeseydi, aynı depodaki kişisel bir kayıt genel bir aramayla
    açığa çıkardı.
  - **Kaydın etiketini kaydın sahibi belirler.** Kaydederken ya da sonradan söyler; model
    etiketi kendi kararıyla seçmez, yalnızca kişinin söylediğini aktarır. Etiketi düşürmek
    onay ister (§10.3).
- **Dışarı gönderim** (zorunlu): argümanlar makinenin dışına gidiyor mu (web araması gibi).
  Etki sınıfı buna bakmaz; sızdırma kuralı (§10.3) buna bakar. Zorunludur, çünkü isteğe
  bağlı olsaydı doldurmayı unutmak hata vermez, sessiz bir sızıntı yolu açardı.
- **Zaman aşımı.**
- **Varsayılanlar:** skill'in ürettiği kayıtlar için varsayılan değerler (kaydın hassasiyeti,
  zamanlayıcının gecikme toleransı gibi) skill tanımında, tanımın yanında bildirilir.
  Varsayılan ayrı bir dosyada dursaydı, skill'i okuyan onun nasıl davrandığını göremezdi.
  Sahip config'te bir varsayılanın üzerine yazabilir, kullanıcı da tek bir kayıt için
  değiştirebilir; öncelik sırası kayıt, config, skill'dir. Skill tanımı skill'in ne olduğunu,
  config sahibin tercihini anlatır; tercih için kod değiştirmek gerekmemelidir.
- İsteğe bağlı: `requires_confirmation` (§10.3), tersi (§9.6).

**Kurallar:**

- **Bir skill, bir dosya.** Tanım, gövde ve politika sınıfı aynı dosyadadır. Tanım birden
  fazla yere dağılırsa, bir parçası değişirken öteki eski kalır.
- **Etki sınıfı tool başınadır, seçenek başına değil.** Bir seçeneği geri alınabilir, diğeri
  alınamaz olan bir tool ikiye bölünür. Yoksa ya zararsız eylem her seferinde onay ister ya
  da yıkıcı eylem onaysız geçer. Etki sınıfı aynı olan eylemler ise tek tool'da birleşebilir
  (sesi açmak, kısmak, kapatmak gibi): hangi tool'un kullanılacağını bir insan kesin
  söyleyemiyorsa model de söyleyemez ve tool sayısı arttıkça seçim zorlaşır.
- **İzin listesi modele görünür olmalıdır.** Bir argümanın değeri sabit bir listeden geliyorsa
  seçenekler katalogda yazılır. Liste yalnızca gövdede doğrulanırsa model hangi değerlerin
  var olduğunu bilmez ve denemeden "yapılandırılmamış" der.
- **Yeni bir tool eklemeden önce mevcut tool'lara bakılır;** istenen özellik mevcut bir
  tool'a eklenecek bir argüman olabilir. Benzer işi yapan iki tool, modelin hangisini
  çağıracağını şaşırtır.
- **Kayıt defteri bir nesnedir, modül düzeyinde global değildir.** Testler arası sızıntı oradan
  gelir. Katalog ve şema ondan üretilir.
- Skill'ler veriye yalnızca kendilerine verilen bağlam nesnesi üzerinden erişir; bu nesne
  depo portları taşır, **asla genel bir veritabanı tutamacı taşımaz** (genel bir tutamaç,
  SQL'in depo adaptöründen çıkmasına açık davettir).
- **Her tool çağrısı aynı sonuç zarfıyla kaydedilir;** bu, olay zarfının (§5.5) tool
  türüdür. Zarfın iki kısmı vardır:
  - **Çekirdeğin doldurduğu kısım:** olay başlığı (§5.5) ve ona ek olarak çağıran kişi, tool
    adı, etki sınıfı, hassasiyet ve doğrulanmış argümanlar. Skill bu alanlara
    dokunmaz; ortak alanları her skill kendisi yazsaydı biri unutur ya da farklı biçimde yazardı.
  - **Skill'in doldurduğu kısım:** durum (`ok` | `error` | `denied` | `timeout` |
    `cancelled` | `started`), yapılandırılmış veri, varsa hata nedeni ve geri alma için gereken
    bilgi (§9.6).

  Olay kaydı, eylem geçmişi, tool bitti sesi (§8.8) ve panel aynı zarfı okur. Modele zarfın
  kısaltılmış bir görünümü gider; gereksiz alanlar bağlamda yer kaplamaz. Aynı tool birden
  fazla eylem içeriyorsa hangi eylemin yapıldığı argümanlarda görünür, ayrı bir alanda
  tekrar edilmez.
- **Ret ve zaman aşımı modele tool sonucu olarak geri beslenir**, hata olarak yükseltilmez.
  Bozuk bir çağrı da geri beslenir; düzeltme bir adım harcamaz. Adım tavanına ulaşılırsa
  model eldeki sonuçlarla yanıt üretir.
- **Yetkilendirme tool'un adına hiç bakmaz.** Ada göre istisna, "hassas tool listesi" demektir.

### 9.2 Keşif

Skill'ler açılışta klasörden bulunup yüklenir; **çalışırken katalog değişmez**, yeni bir skill
yeniden başlatmayla gelir. Katalog sabit önekin parçasıdır (§8.3); çalışırken değişseydi
önbellek düşer ve ölçülmemiş bir katalogla çalışılırdı (§15.2).

### 9.3 Çoklu çağrı

LLM birden fazla çağrı döndürdüğünde **yan etkili çağrılar sırayla** çalışır. `READ`
çağrıları paralel çalışabilir. Onay gerektiren çağrılar tek bir onay planında toplanır;
kullanıcıya tek tek sorulmaz.

### 9.4 `bash`

Sıradan bir skill; özel bir kod yolu yoktur. Hazır bir tool'un karşılamadığı işleri
(program çalıştırma, hesaplama, dönüştürme, betik) yapar; bu işlerin listesi önceden
yazılamadığı için vardır. Yaklaşım **copy-on-write**'tır: gerçek dosyaların kopyası
üzerinde çalışılır, asıl dosya hiç değişmez.

- **Kendi alanında çalışır.** Alan, makinenin geri kalanından izole bir konteynerdir;
  `bash` alanın dışındaki hiçbir şeyi göremez ve değiştiremez. Alanın içinde serbesttir.
- **Gerçek dosyalar alana kopyalanarak girer.** Kopyalamayı `bash`'in kendisi değil kod
  yapar. Kopya alınan dosya sahibin verisidir; bu yüzden skill'in hassasiyeti `PERSONAL`'dır
  ve kopya almak, o dosyayı okuma yetkisi ister (§10.2).
- **Yalnızca config'teki izin listesinde bulunan yollardan kopya alınır; listede olmayan yol
  reddedilir.** Hassas yerleri önceden saymak mümkün değildir: yasak listesinde unutulan bir
  yer sessizce açık kalırdı, izin listesinde unutulan bir yer ise görünür bir ret üretir.
- **Gizli anahtar dizinleri (`~/.ssh`, `~/.gnupg`) ve `.env` dosyaları, izin listesi ne derse
  desin kopyalanmaz; bu liste kodda sabittir.** İzin listesine geniş bir yol (ev dizininin
  tamamı gibi) eklenirse anahtarlar onunla birlikte açılırdı; bağlama bir kez giren anahtar,
  sonraki her adımda sızabilir.
- **Gerçek dosyaya asla geri yazılmaz.** Sonuç alanda kalır; sahip ona oradan bakar ve ne
  yapacağına kendisi karar verir. Geri yazma olsaydı, onay komutun ya da değişikliğin
  anlaşılmasına dayanırdı; uzun bir komut ya da ekransız bir an (kulaklık, cepteki telefon)
  bu onayı anlamsız kılar.
- **`bash`'in ürettiği dosyalar her çağrı bitince kod tarafından çıktı alanına taşınır.
  Çıktı alanı `bash` için salt okunurdur; diğer tool'lar dosyayı oradan doğrudan kullanır.**
  `bash` sonraki adımda dosyayı okuyabilir ama değiştiremez; böylece sahibin bakacağı ya da
  gönderilecek bir sonuç, sonraki bir komutla bozulamaz.
- **Ağ erişimi yoktur.** Ağ açık olsaydı, alana kopyalanan bir dosya hiçbir onay olmadan
  dışarı gönderilebilirdi. İnternet gereken işler kendi tool'larıyla yapılır.
- **Root yoktur, `sudo` yoktur.** Alanın izolasyonunu aşabilecek tek yol yetki yükseltmedir.
- **Modele komutun metin çıktısı (stdout ve stderr) ve çıkış kodu döner.** Bir sürecin
  sonucu bunlardır; sonuç bir dosyaya yazılsaydı, her sonucu okumak ikinci bir çağrı
  isterdi.
- **Üretilen dosyaların içeriği modele dönmez, çıktı alanındaki yolu döner.** Model bu yolu
  sonraki çağrılarda başka tool'lara girdi olarak verebilir. Dosyanın içeriği her çağrıda geri
  dönseydi, büyük bir dosya bağlamı doldururdu.
- **Sonucu yazdırmayan komut boş çıktı döndürür.** Tool açıklaması modele sonucu yazdırmasını
  söyler ve bu davranış ölçülür (§15.2). Model bunu bilmezse, başarılı bir komutu boş bir
  cevaba çevirir.
- Sözleşmede ayrıca zaman aşımı tanımlıdır; çıktı boyutu sınırı tüm tool'larınkiyle
  aynıdır (§8.8).

Etki sınıfı `WRITE`'tır: etkisi alanın dışına çıkmaz, alandaki her şey bir kopya ya da
kopyadan türetilmiştir. Alanın dışında sistemi değiştiren ve tool'u olmayan işler `bash`'in
kapsamında değildir; bunlar **AÇIK** (§16.19).

**Başka hiçbir yerde model çıktısı kabuğa ya da argv'ye girmez.** Uygulama açma bir config
tablosunu indeksler, pencere eylemi koddaki bir tabloyu. Komutlar argv dizisidir, tek dize
değil (tek dize kabuk bölmesi ister, kaçış hataları da oradan sızar).

### 9.5 Diğer skill türleri

| Alan | Ne var |
|---|---|
| **Uzun süren tool'lar** | Sonuçta `started` durumu. Bitince sonuç yeni bir tetikleyici olarak turu başlatır. Durumları kalıcı iş deposunda tutulur |
| **Görüntü** | Kamera ve vision hattı üzerinden |
| **Profil** | Kişiye özel tercih ve notları okur (§11.1) |
| **Makine denetimi** | Bir adaptörün arkasındadır; tool *ne* istendiğini bilir, *nasıl* yapıldığını bilmez |
| **Eylem geçmişi** | Olay kaydının görünümüdür (§11) |

### 9.6 Geri alma

Bir skill isteğe bağlı olarak bir **tersi** bildirir: yaptığı işi geri alan işlem. Geri alma
bir tool'dur ve kullanıcı ondan yalnızca "geri al" diye isteyebilmelidir.

- **`geri_al` argümansız çalışır; argümanları daraltmak içindir.** Argüman yoksa konuşan
  kişinin geri alınabilir son eylemi, tool adı verilmişse o tool'un son eylemi geri alınır.
  "Notu geri al" demek yeterlidir; notun başlığını tekrar söylemek gerekmez.
- **Aday birden fazlaysa tool seçmez, adayları modele döndürür ve model kullanıcıya sorar.**
  Aynı adımda birden fazla çağrı çalışmışsa "son" belirsizdir; sistemin birini seçmesi,
  kullanıcının istemediği bir eylemi geri alabilirdi.
- **Tersinin girdisi ilk çağrının argümanları ve sonucudur.** Geri almak için gereken bilgiyi
  (oluşan kaydın kimliği, değişmeden önceki ses seviyesi) tool çalışırken kendi sonucuna
  yazar; bu bilgi yalnızca eylem anında elde edilebilir.
- **Geri alma yetki kararından tersinin kendi etki sınıfıyla geçer** (§10.3); ayrı bir izin
  kuralı yoktur.
- **Tersi olmayan eylem geri alınamaz ve bu modele tool sonucu olarak söylenir.**
  `IRREVERSIBLE` sınıfının tanım gereği tersi yoktur. `WRITE` ve `EXTERNAL` için tersi zorunlu
  değildir: tersi tanımsız bir tool'un geri alınamadığı modele ve kullanıcıya zaten söylenir.

---

## 10. Kimlik, güven ve yetki

### 10.1 Tehdit modeli

Kimlik birden fazla kaynaktan gelir ve **kaynakların gücü farklıdır:**

| Kaynak | Güç | Neden |
|---|---|---|
| Kişisel cihaz | güçlü | taşımanın doğruladığı, tek bir kişiye eşleştirilmiş cihaz |
| Ses (konuşmacı tanıma) | zayıf | ses kaydı çalınıp tekrar oynatılabilir |
| Ortak cihaz, doğrulanmamış bağlantı | zayıf | önünde kimin olduğunu cihaz kanıtlamaz |

- **Cihaz kimliği istemcinin beyanı değil, taşımanın doğruladığı kimliktir.** Tailscale her
  bağlantının hangi düğümden geldiğini doğrular; kişi profilindeki eşleştirme bu düğüm
  kimliğine yapılır. Beyan edilen bir kimlik güçlü sayılsaydı, ağdaki her cihaz kendini sahibin
  telefonu olarak tanıtabilirdi. Tailscale'den geçmeyen bir bağlantı doğrulanmış kimlik taşımaz.
- **Kişisel cihaz**, profilde tek bir kişiye eşleştirilmiş ve kimliği doğrulanmış cihazdır.
  **Ortak cihaz** geri kalan her şeydir: kimseye eşleştirilmemiş ya da birden fazla kişinin
  kullandığı cihaz. Ayrım cihazın türünde değil, kime eşleştirildiğindedir; eşleştirmeyi
  sahip yapar.

Ses tek başına yeterli kimlik sayılsaydı, en kötü durum **sahibin ses kaydını çalan birinin
sahip yetkisiyle iş yaptırması** olurdu. Bu yüzden **yetki = rol × kimlik gücü**: sesle
tanınan sahibin bir işi tek başına yaptırıp yaptıramayacağı, işin etki sınıfına ve kimliğin
gücüne birlikte bağlıdır. Hangi işin sesten güçlü bir kimlik istediğine yetki kararı bakar
(§10.3).

Kabul edilen ikinci risk: modüller arasında ek kimlik doğrulama yoktur. Tailnet'teki bir cihaz
ele geçirilirse tüm modüllere erişilir.

**Skill'ler güvenilir koddur;** skill sözleşmesindeki korumalar kötü niyete değil, yazım
hatasına karşıdır. Skill çekirdeğin içinde çalışır; ona karşı çizilecek bir sınır, onun
zaten yapabildiği bir şeyi yasaklayamaz.

### 10.2 Roller

| Rol | Kim | Temel yetki |
|---|---|---|
| **owner** (sahip) | Kurulumla atanmış tek kişi | Tümü; onay gerekip gerekmediğine yetki kararı bakar (§10.3) |
| **acquaintance** (tanıdık) | Sahibin rol verdiği kişi | Sohbet + `READ`·`GENERAL` |
| **system** | Kimse konuşmadan, tetikleyiciyle açılan turlar | Sabit değil; tetikleyici başına config'te |
| **unknown** (tanımsız) | Rolü olmayan herkes: tanınmayan ses, kendini kaydetmiş ama rolü verilmemiş kişi | Sohbet + `READ`·`GENERAL` |

- **Rol ilişkiyi değil yetkiyi anlatır.** Aynı yetkiye sahip iki rol (arkadaş, akraba gibi)
  örnekten çıkmış bir ayrımdır ve her yeni ilişki türü yeni bir rol ister. Kişiler arasındaki
  fark rolde değil, kişi bazlı yetki ayarındadır.
- **Sahip, kişi profilinden** bir kişinin yetkisini genişletebilir ya da daraltabilir
  (örneğin bir tanıdığa `PERSONAL` okuma açmak).
- **Rolü yalnızca sahip verir.** "Ben sahibin arkadaşıyım" bir iddiadır, yetki değildir.
  Kimlik ve rol, kullanıcının söylediğinden okunmaz.
- **Sahip rolü sesle asla verilemez.** Sahip yalnızca kurulum betiğiyle atanır: betik ses
  örneklerini toplar, profili sahip olarak işaretler ve sahip zaten tanımlıysa çalışmayı
  reddeder. Fiziksel makine erişimi gerektirir. Diğer roller ve yetki genişletmeleri kimlik
  onayıyla verilir (§10.3).
- **"Kendini kaydetti ama sahip kefil olmadı" bir kademe değil, profilin durumudur.** Rolü
  olmayan profilin hakları `unknown` rolününkilerdir; ayrı bir kademe ve ayrı bir yetki
  tablosu gerekmez.
- **`system` rolünün yetkisi tanımlanmamış bir tetikleyici yapılandırma hatasıdır.** Sessiz
  bir varsayılan yoktur: unutulmuş bir config, fark edilmeden ya tam yetkiyle ya hiç
  yetkisiz koşan bir tetikleyici üretir.

### 10.3 Yetki kararı

Tek bir zorlama noktası vardır ve kodda durur. Prompt bir güvenlik sınırı değildir: sistem
promptu modele sınırlardan bahsedebilir, ama bu bir kolaylıktır; modelin bunu yok sayması bir
güvenlik olayı değildir, çünkü kararı model vermez.

**Politika tablosu hücre hücre yazılır**, üretilmez. Üretilmiş bir matrisi test etmek,
üreticinin varsayımını test etmek olur. Eksik bir hücre sessiz bir ret değil, bir hatadır.

Her tool çağrısı için karar üç sonuçtan biridir: **izin** (`allow`), **red** (`deny`) ya da
**onay** (`confirm`).

- **Önce yetkiye bakılır.** Rolün o çağrıya yetkisi yoksa sonuç reddir ve onay sorulmaz.
  Yoksa onay, yetkisi olmayan birine yetki vermenin yolu olurdu.
- **Onay türleri kanala göre değil, kanıtladıklarına göre adlanır:** **niyet onayı** kişinin
  bu işi istediğini kanıtlar, **kimlik onayı** buna ek olarak kim olduğunu kanıtlar (§10.5).
  Koddaki değerleri `intent` ve `identity`'dir.
  Kanala göre bir ad, sesle verilen onayın kimliği de kanıtladığı yanılgısına açıktır.
- **Onay isteyen tetikleyiciler:** `IRREVERSIBLE` sınıfı niyet onayı, `DANGEROUS` sınıfı
  kimlik onayı, `requires_confirmation` bayrağı niyet onayı ister. Bir kaydın etiketini
  `PERSONAL`'dan `GENERAL`'a düşürmek niyet onayı ister, yükseltmek istemez: açığa çıkan içerik
  geri alınamaz, gizlemek ise zarar vermez. Rol vermek ve bir kişinin yetkisini genişletmek
  kimlik onayı ister: ikisi de kalıcıdır, ses kaydını çalan biri sesle kendine kalıcı bir
  yetki verebilirdi. `IRREVERSIBLE` için ses yeterlidir: ses kaydıyla saldırı
  bir mikrofonun yanında bulunmayı gerektirir, her silmede kişisel cihaz istemek ise onayı
  düşünmeden verilen bir alışkanlığa çevirir.
- **Sızdırma:** aynı turda hem bir tool ile okunmuş `PERSONAL` içerik hem de başkasının
  yazdığı metin (§10.6) bağlamdaysa, argümanlarını dışarı gönderen çağrı kimlik onayı ister.
  Yoksa metne gömülü bir talimat kişisel veriyi bir sorguya koyup dışarı taşıyabilirdi.
  Geçmiş ve hafıza bu kurala girmez: ikisi her turda bağlamdadır ve sayılsalardı, başkasının
  metni okunduktan sonraki her arama onay isterdi. **Kabul edilen risk:** geçmişte ya da
  hafızada geçen bir bilgi bu yolla sızdırılabilir. Diğer çağrılar bu metin yüzünden ayrıca
  onay istemez: geri alınamaz olanlar niyet onayıyla kişiye zaten okunur, geri alınabilir
  olanlar geri alınır.
- **Tetikleyicilerden herhangi biri onay isterse onay gerekir; birden fazlası isterse en
  güçlüsü istenir.** Kimlik onayı niyeti de kanıtladığı için niyet onayını kapsar; aynı
  çağrı için iki kez sormak bir şey kanıtlamaz.
- **Onayı, işi isteyen kişinin kendisi verir:** niyet onayını sesiyle, kimlik onayını
  kendisine eşleştirilmiş kişisel cihazdan. Başkasının verdiği onay, isteyenin niyetini de
  kimliğini de kanıtlamaz. Kişisel cihazı olmayan birinden kimlik onayı istenemez; sonuç
  reddir.
- **`requires_confirmation` yalnızca onay ekler, hiçbir zaman kaldırmaz.** Bayrak onayı
  kaldırabilseydi, tek satırlık bir yazım hatası etki sınıfının istediği onayı devre dışı
  bırakırdı.

### 10.4 Kayıt akışı

Kayıt ayrı bir durumdur (`ENROLLING`) ve **bir tanışma sohbetidir.** Kişi "beni de kaydet" der;
Mayen adını, nasıl hitap edileceğini ve tercihlerini sorar; kişi bunları söylerken ses
profili çıkarılır. Kullanıcıdan sabit bir metin okuması istenmez: kimse kayıt için uzun süre
tek başına konuşmak istemez.

- **Ses izi yalnızca açık rızayla çıkarılır.** Sürekli STT, sesi zaten kaydeder; ama
  biyometrik veri ancak kişi kaydı kendisi istediğinde çıkarılır. Geçmiş kayıtlardan geriye
  dönük profil çıkarılmaz: o seslerin kime ait olduğu da belirsizdir.
- **Sohbet yeterli ses vermezse profil sonraki konuşmalarla tamamlanır**, ama yalnızca mevcut
  profille güçlü eşleşen, tek konuşmacılı segmentlerle. Yoksa profile başkalarının sesi
  karışır ve profil kayar.
- Kayıt bitince sahibe bildirim gider: "X kaydoldu, rolü ne olsun?". Rol verilene kadar
  kişinin rolü `unknown`'dur.
- Gereken ses süresi, eşikler ve "güçlü eşleşme"nin tanımı **AÇIK** (§16.5).

### 10.5 Onay

Hangi onayın isteneceğine yetki kararı bakar (§10.3); burada iki türün nasıl alındığı yazar.

**Niyet onayı** sesle alınır; kişinin işi istediğini kanıtlar, kim olduğunu kanıtlamaz:

1. Argümanlar önce doğrulanır. Geçersizse kullanıcıya hiç sorulmaz; hata modele geri beslenir.
   Kullanıcıdan bozuk bir işlemi onaylaması istenmez.
2. Tur `AWAITING_CONFIRMATION`'a geçer ve plan tutulur; **bu adım okumadan öncedir** (§5.4).
3. Asistan yapacağı işlemi ve argümanlarını açıkça okur. **Onay cümlesini model, kendi
   geçmişinden değil plandan yazar ve plandaki her argüman değeri cümlede aynen geçer.**
   Geçmiyorsa cümle bir kez yeniden istenir; yine geçmiyorsa sesli onay yapılmaz, kimlik
   onayına geçilir ve plan kişisel cihazda yazılı gösterilir. Onay modelin anlattığını değil
   yapılacak olanı doğrulamalıdır: cümleyi isteği yanlış anlayan model kurarsa, onay yanlış
   anlamayı yakalamak yerine gizler.
4. Sonraki segment yalnızca onay çözümleyicisine gider. Çözümleyici kısıtlı bir çıktıyla üç
   sonuçtan birini üretir: onay / red / belirsiz. Kısıt dışı bir cevap belirsiz sayılmaz,
   hata yükseltir.
   **Segmentin konuşmacısı turu açan kişiyle eşleşmiyorsa sonuç, söylenenden bağımsız olarak
   belirsizdir** (eşleşme eşiği §16.5). Yoksa odadaki başka birinin "evet"i, sorulan kişinin
   onayı yerine geçerdi.
5. Belirsizse bir kez daha sorulur; yine belirsizse iptal edilir.
6. **Zaman aşımı reddir.**

**Onay serbest metinden anahtar kelimeyle çıkarılmaz.** "Tamam ama önce hava durumu" gibi bir
cümlenin onay sayılması, tasarımın kabul etmediği bir hatadır.

**Kimlik onayı** kişisel cihazdan alınır; niyetin yanında kimliği de kanıtlar:
bildirim isteyen kişinin kişisel cihazına (§10.1) gider, yanıt aynı cihazdan yapılandırılmış biçimde
(düğme gibi) gelir. Zaman aşımı yine reddir. Bu yol sesin üstüne bir ikinci faktördür.

**Kimlik onayı tek bir isteğe bağlıdır ve tek kullanımlıktır.** Yanıt, isteğin kimliğini ve
argümanların özetini taşır; eşleşmeyen ya da daha önce kullanılmış bir yanıt reddedilir.
Yoksa eski bir bildirimdeki onay düğmesi yeni ya da değiştirilmiş bir planı onaylayabilirdi.

### 10.6 Başkasının yazdığı metin

Oyun sohbeti, web sayfası, tool çıktısı gibi serbest metinler LLM'e ham hâliyle girebilir
(web araması çalışır) ama oturumun durumunda "bağlamda başkasının yazdığı veri var" diye
işaretlenir (§8.1). Böyle bir içerik bağlamdayken hangi çağrının onay istediğine yetki kararı
bakar (§10.3).

Dış kaynaklı mesaj akışları (oyun sohbeti gibi) kendiliğinden LLM turu başlatmaz; yalnızca
sahibin tanımladığı bir kuralla tur açabilir. Aksi hâlde başkasının yazdığı metin, dışarıdan
herkesin kullanabileceği bir tetikleyici olur.

### 10.7 Acil durdurma

Acil durdurma bir tetikleyicidir ve her girdi yolundan gelebilir (ses, yazılı kanal, panel,
fiziksel bir düğmenin tetikleyici adaptörü). Liste değil tür olduğu için yeni bir girdi yolu
kendiliğinden kapsanır. Kapsam, durdurulan turun nasıl başladığına bağlıdır:

- Tur `system` rolüyle açılmışsa tüm tool'lar ve tüm proaktif davranış kesilir.
- Turu bir kişi açmışsa yalnızca o turdaki tool'lar durur.

Sağlık kontrolü (§14) her durumda çalışmaya devam eder: durdurma sistemi kör bırakmamalıdır.
Kesilen proaktif davranış, sahip elle açana kadar kapalı kalır.

---

## 11. Depolar ve hafıza

| Depo | Ne var |
|---|---|
| **Transkript** | Zaman damgalı, konuşmacı alanlı. LLM'e `search_transcript` tool'u olarak açılır (`PERSONAL`) |
| **Olay kaydı** | Olay zarfındaki olaylar (§5.5), zaman sırasıyla. Eylem geçmişi bu kaydın tool çağrılarından oluşan görünümüdür, ayrı tutulmaz: aynı veri iki yerde tutulursa silme kuralı birinde unutulur |
| **Medya** | Dairesel kayıt, `write` / `read(start, end)`. Her medya türü için. Biçimi **AÇIK** (§16.14) |
| **Kalıcı hafıza** | Transkriptten damıtılmış bilgi, transkriptten ayrı |
| **Kişi profili** | Ad, rol, dil ve hitap tercihi, kişi bazlı yetki ayarları, ses profili, eşleştirilmiş cihazlar (kişinin kanalı), tercih ve notlar |
| **İş ve zamanlayıcı** | Zamanlayıcılar, hatırlatmalar, sıradaki tetikleyiciler, rahatsız etme modunda biriken olaylar, uzun süren tool'ların durumu. Kalıcıdır |
| **Arşiv** | Transkriptin ve olay kaydının değişmez kopyası (§11.7) |

### 11.1 Kişi profili

LLM'e açılış: ad, rol, dil ve hitap bağlama otomatik girer. Tercih ve notlar yalnızca tool ile
istenince verilir. **Ses profili ve yetki ayarları LLM'e hiç ulaşmaz**; ses profilini konuşmacı
tanıma adaptörü, yetki ayarlarını çekirdek kullanır.

### 11.2 Kalıcı hafıza

- **Tek ortak havuz, kişi etiketli.** Her olgu kimin söylediğini taşır. Asistan "arkadaşın bu
  konuda şöyle demişti" diyebilir: bilgi ortak, kaynağı belli.
- **Her olgu hassasiyet taşır.** Ortak havuz, bir kişinin söylediği kişisel bir şeyin başka
  birine okunması demek değildir; `PERSONAL` olgular yetki tablosundan geçer.
- Getirilen olgular bağlam bloğunda kaynağı ve tarihiyle verilir; bayat olabilecekleri ve
  gerçek zamanlı veri için tool çağrılması gerektiği açıkça yazılır.
- Olgular listelenebilir ve silinebilir. Kullanıcının göremediği ve silemediği bir bellek,
  hata ayıklanamaz bir bellektir.

### 11.3 Arka plan işleri

Özetleme ve olgu çıkarımı **aktif turla yarışmaz.** Boşta ya da açılışta çalışır; başlamış bir
iş, tur kuyruğa girdiği anda iptal edilir ve sonraki boşlukta baştan başlar. Yarım kalmış işin
sonucu yazılmaz. "Tur sırasında başlamaz" demek yetmez: boşta başlamış bir iş, tur geldiğinde
hâlâ model sunucusunu meşgul ediyor olabilir ve kullanıcının ilk token'ı onu bekler.
Özetleme ve çıkarım aynı kayıt grubu üzerinde tek iş olarak çalışır, böylece tek bir ilerleme
işareti ("buraya kadar işlendi") ikisine de yeter.

### 11.4 Unut ve sil

İki kademe, ikisini de yalnızca sahip verir. Bir kaydın kime ait olduğu tek anlamlı değildir
(söyleyen, hakkında olan, kaydeden ayrı kişiler olabilir); başkasına tanınan bir silme hakkı,
sahibin kendi verisini (rehberindeki bir numarayı) silmenin yolu olurdu.

- **Unut** (varsayılan): kayıt silinmez, ama LLM'e hiçbir yoldan girmez; `search_transcript`
  gibi tool sonuçları ve replay (§14) da dahil. Yalnızca sahip kendisi arayıp bulabilir. Tool
  sonucu da bağlama girer; tool'a açık kalan bir kayıt, tek bir aramayla geri gelir ve
  unutulmuş olmaz.
- **Sil**: sahip hangi depoyu söylediyse (transkript, medya, damıtılmış hafıza) ondan ve
  kaydın olay kaydındaki kopyalarından gerçekten silinir. Kopyası kalan bir kayıt silinmiş
  sayılmaz. Otomatik yedekler bunun dışındadır (§11.6).
- **Unut ve sil kararları bir mezar taşı listesinde de tutulur ve her geri yüklemeden sonra
  yeniden uygulanır.** Yoksa eski bir yedeğe dönmek, unutulan kaydı LLM'e geri getirirdi.
  Liste yedeklenen veritabanının dışında durur; içinde olsaydı geri yükleme onu da eski hâline
  döndürürdü. Listede kaydın içeriği değil yalnızca kimliği bulunur; içerik taşısaydı, sildiği
  şeyin kopyası olurdu.
- **Arşive ikisi de ulaşmaz** (§11.7).

### 11.5 Saklama

Arşiv dışındaki her depoda bir saklama süresi alanı vardır. Değerler, tanımsız seslerin kayıtlarının süresi
dahil, **AÇIK** (§16.15).

### 11.6 Depo adaptörü

- SQLite, WAL kipi, tek sahibi depo adaptörü (§3). Erişim depo portları üzerinden; adaptör
  `sqlite3.Row` değil dondurulmuş dataclass döndürür (`Row` sütun adlarını yukarı sızdırır ve
  bir şema değişikliği tool gövdelerini kırar).
- **Bir transaction asla bir LLM ya da HTTP çağrısını kapsamaz.**
- `autocommit=True` altında `Connection.rollback()`/`.commit()` sessizce hiçbir şey yapmaz;
  transaction'lar düz `COMMIT`/`ROLLBACK` SQL'iyle yönetilir. `executescript` örtük COMMIT
  yapar; migration'lar ondan geçmez. İkisi de testle kilitlenir.
- Şema sürümlenir; migration'lar sıralı ve idempotenttir; hataları yutulmaz (sessiz yutma
  şema sapmasını gizler).
- **Saklanan sözlük (rol, görev durumu gibi) `ports`'ta durur.** Depo adaptörü CHECK kısıtını
  ondan kurar; bir test, veritabanındaki kısıtın sözlükle aynı olduğunu doğrular. Sözlük depo
  adaptöründe dursaydı, onu kullanan iç katmanlar `adapters`'ı import edemezdi (§4).
- Otomatik yedek SQLite'ın kendi mekanizmasıyla alınır, dosya kopyalanarak değil. Sıklık,
  sayı ve konum **AÇIK** (§16.16).
- **Alınmış bir yedeğe yazılmaz;** sil de ona ulaşmaz. Geri yüklemede yedeğin kopyası canlı
  veritabanı olur ve yazma ona yapılır, yedeğin kendisi değişmez. Yedek yazılabilir olsaydı,
  geri dönülecek an kendisi değişebilirdi.

### 11.7 Arşiv

Ne olur ne olmaz diye tutulan kayıttır; sahip acil bir durumda ona elle bakar. **Mayen'in hiçbir
sürecine katılmaz:** LLM onu hiçbir yoldan görmez, unut, sil ve saklama süresi ona
uygulanmaz. Kenarda duran bir kayıt, Mayen'in içinde olanlardan etkilenseydi acil durumda
eksik çıkabilirdi.

- Transkript ve olay kaydı arşive de yazılır; medya, kalıcı hafıza ve profil yazılmaz. Medya
  dairesel tutulur ve arşivde bu sınır kalkardı; hafıza ve profil transkriptten türetilir,
  kaynağı arşivdedir.
- **Yalnızca ekleme yapılır.** Kod arşivde kayıt silen ya da değiştiren bir işlem sunmaz.
- **Mayen'de arşivi okuyan bir arayüz yoktur;** biçimi Mayen olmadan okunabilir olmalıdır.
  Mayen'in içinde bir okuma yolu olsaydı, ona bir tool bağlanabilir ve arşiv LLM'e ulaşırdı.

---

## 12. Proaktif davranış ve rahatsız etme

**Proaktif davranış:** orchestrator kullanıcı tetiklemeden de tur başlatabilir (hatırlatma,
sohbette uygun anda araya girme). Bu turlar `system` rolüyle açılır, kendi `turn_id`'lerini
taşır ve başka bir turun kesilmesinden etkilenmez. Hedef cihaz, içeriğin ait olduğu kişinin
en son etkileşimde bulunduğu cihazdır; hiçbir cihaz bağlı değilse kuyruklanır. Mayen'in
genelinde son kullanılan cihaz başka birinin olabilir; oraya giden bir hatırlatma ya hiç
duyulmaz ya da yanlış kişiye duyulur.

Kişisel içeriğin ortak cihazda verilmemesi (§7) proaktif çıktı için de geçerlidir.

**Rahatsız etme politikası** proaktif davranışı sınırlar ve **tamamen kural tabanlıdır**; LLM
erteleme kararı vermez. Model, tool seçimi gibi daha küçük kararlarda bile tedbirlerle
çalıştırılır; kullanıcıyı rahatsız edip etmeme kararı ona bırakılmaz. Kurallar:

- sessiz saatler (zaman aralığı; `urgent` kapıyı geçer),
- elle açılan "rahatsız etme" modu,
- iş ve zamanlayıcı deposundaki zaman aralıklarından otomatik mod (iş ya da ders saatleri gibi).

Mod sürerken biriken olaylar mod bitince tek bir özet olarak iletilir.

**Kaçırılan zamanlayıcılar:** her zamanlayıcının bir **gecikme toleransı** vardır. Mayen
kapalıyken vadesi geçen bir zamanlayıcı, toleransı içinde kaldıysa açılışta bir kez çalar;
aştıysa "kaçırılanlar" özetine girer. Tekrarlayan bir zamanlayıcının kaçırılan
tekrarları tek bir çalmada birleşir. Zamanlayıcının anlamı türüne bağlıdır: üç saat geç
çalan bir uyandırma alarmı işe yaramaz, yirmi dakika gecikmiş bir ilaç hatırlatması
yarar; birleştirilmezse uzun bir kapanıştan sonra aynı hatırlatma art arda çalar.
Toleransın varsayılanı zamanlayıcıyı kuran skill'in tanımındadır (§9.1); kullanıcı tek
bir zamanlayıcı için değiştirebilir.

---

## 13. Taşıma

İstemciler çekirdeğe ödünç alınan çerçevenin taşımasıyla bağlanır (WebSocket ya da WebRTC);
hangisinin kullanılacağı istemci türüne göre config'tedir. Çerçeve biçimi, gönderim kuyruğu
ve ses parçalarının bölünmesi çerçevenin taşıma ve serileştirme katmanındadır. Mayen'e ait
kurallar:

- **Erişim yalnızca özel ağdandır; cihaz kimliği istemcinin beyanından değil taşımadan
  okunur** (§10.1).
- **Söz kesildikten sonra kesilen cevabın sesi çalınmaz.** İptalden sonra ağda hâlâ ölü
  cevabın parçaları olabilir; istemci onları yeni cevabın ilk parçasından ayırabilmelidir.
  Ses ile kesme bildiriminin ayrı kanallardan gittiği bir taşımada sıranın korunduğu ayrıca
  doğrulanır.
- **Bozuk ya da işlenirken hata veren bir çerçeve bağlantıyı kapatmaz;** hata olarak
  bildirilir. İstemci tarafı da bir çerçevede hata alınca ölmez; aksi hâlde tek bir hata
  okuma görevini öldürür ve istemci **sessizce sağırlaşır**.
- Bağlantı kopması ve yeniden bağlanma normaldir ve sağlık kontrolüne beslenir.

---

## 14. Dayanıklılık, gözlem ve işletim

| Alan | Ne var |
|---|---|
| **Yedek adaptör** | Adaptörler için config'te sıralı yedek listesi |
| **Sağlık kontrolü** | Adaptörlerin durumunu izler, yedeğe geçişi besler. Çıkış biçimi sabit olan bir servis (TTS örnekleme hızı gibi) farklı biçim bildirirse sağlık kontrolü yüksek sesle başarısız olur: sessiz bir uyuşmazlık "asistan ince sesle konuşuyor" diye duyulur ve sebebi okunamaz |
| **Gözlemlenebilirlik** | Her aşamanın başlangıç ve bitiş damgası, yapılandırılmış ve seviyeli log. Karar modeli için de veri kaynağı. **Loga içerik girmez:** log olay zarfının yalnızca başlığını yazar (§5.5); konuşma metni, tool argümanı ve tool sonucu yazılmaz. İçerik taşıyan log, unut ve silin ulaşmadığı bir depo olurdu |
| **Panel** | Olayları ve oturumların durumunu canlı gösteren, salt okunur bir web arayüzü (React, TypeScript): telefondan da açılır. Sohbet etmez; konuşmak istemcilerin işidir. Önce istenen andan bu yana kayıtları, sonra kayda girdikçe canlı kayıtları alır. **Yalnızca sahibin cihazından açılır:** panel herkesin konuşmasını gösterir; cihaz taşımadan okunur (§10.1). Tarayıcıda açık başka bir sayfa da sahibin cihazından bağlanabileceği için panelin açıldığı adres config'teki izin listesinde olmalıdır. Yavaş bir panel kaydı bekletmez; geride kalınca bağlantısı bir hatayla kapanır, olay sessizce atlanmaz |
| **Config** | Tek YAML: adaptörler, skill'ler, yerleşim, model deposu (§8.9), skill varsayılanlarının üzerine yazmalar (§9.1), saklama süreleri, izin listeleri. Prompt/kişilik ayrı dosyadan. Gizli bilgiler ortam değişkenlerinde ya da `.env`'de; YAML'da yalnızca adı geçer ve kod içinde maskeli bir tipte taşınır |
| **Çoklu istemci** | Birden fazla istemci aynı çekirdeğe taşıma üzerinden bağlanır; oturum ve bağlam istemci başına |
| **İşletim** | Servisler işletim sisteminin servis yöneticisiyle çalışır; uygulama kendini yeniden başlatmaya çalışmaz. Kalıcı bir yapılandırma hatası, yeniden başlatma döngüsüne gömülmesin diye ayrı bir çıkış koduyla biter. Servisler arası bağımlılık zayıf kurulur: ölü bir TTS asistanı susturur ama öldürmez |
| **Replay** | Kaydedilmiş turlar (olay kaydı, ortak saat) yeniden oynatılır. Amaçları: hata ayıklama, karar modeli eşiklerini gerçek olaylar üzerinde ayarlama, regresyon (prompt ya da model değişince eski turları oynatıp karşılaştırma). Replay'de tool'lar kullanıcının tanımladığı mock'larla çalışır, hiçbir gerçek eylem tetiklenmez. Unut işaretli kayıtlar replay'de modele verilmez (§11.4) |
| **Test adaptörleri** | `TextInput`, `NullTTS`, sahte STT/LLM, replay için mock tool adaptörleri |

**Hiçbir hata sessizce yutulmaz.** Başarısız bir işlem hem kayda hem kullanıcıya yansır.

---

## 15. Test ve ölçüm

### 15.1 Kapılar

Her iş paketinin sonunda yeşil: ortam kilit dosyasından, lint, format, katı tip kontrolü,
testler. Sınır testi (§4) bunların içindedir.

- **Tur akışı testleri** sahte adaptörlerle, GPU'suz, saniyeler içinde.
- **Politika testleri:** her (rol × etki sınıfı × hassasiyet) hücresi için bir test.
- **Durum makinesi testleri:** söz kesme, zaman aşımı, onay okunurken söz kesme (plan yaşamalı),
  iptalden sonra gelen eski `turn_id`'li parça (atılmalı), kesme sırasında kuyrukta bekleyen
  proaktif tur (düşmemeli), kayıt sırasında kesinti, paralel oturumlar.

### 15.2 Davranış ölçümü (`evals`)

Prompt, tool açıklaması ya da model değişikliği ölçümden geçmeden kabul edilmez: modelin
davranışı metindeki küçük değişikliklere duyarlıdır ve etkisi okuyarak tahmin edilemez.

- **Her oran Wilson %95 aralığıyla raporlanır.** Aralıkları çakışan iki koşu bir sıralama
  değildir.
- **Halüsinasyon üç ayrı sayaçtır:** olmayan tool, olmayan argüman, tool sonucunda olmayan
  bilgiyi iddia etme. Tek bir doğruluk sayısında eritilmez.
- **Altın küme dondurulur.** Yeni iş yeni bir küme ekler, eskisini düzenlemez. Bir kümeyi
  sonuca uydurmak, ölçümü kendi varsayımının testine çevirir.
- **Katalog büyüyünce bir kümenin beklentisi bayatlayabilir.** "Tool gerekmez" işaretli bir
  senaryonun doğru cevabı, yeni bir tool'la değişebilir. Bir kontrol regresyonu, kataloğun ne
  kazandığıyla birlikte okunur.
- **Hakem model yoktur.** Hakemin kendi halüsinasyonu ölçüme girer.
- **Tool gövdeleri ölçümde çalıştırılmaz.** Ağ ve veritabanı ölçümü belirlenimsiz yapar.
- **Ölçüm hangi dünyayı ölçüyor?** Bir sayıyı aktarmadan önce fikstürün geçmişinin üretimin
  geçmişiyle aynı olup olmadığı sorulur; aynı model iki dünyada çok farklı sonuç alabilir.
  Üretim davranışı hakkında hüküm vermenin aleti, üretimin dizisini birebir kuran kabul
  kapısıdır.
- **Ölçüm, üretimin kurduğu prompt'u ölçer.** Ölçüm aracı prompt'u üretimin kendi
  fonksiyonundan kurar; elle kurulmuş bir önek, üretimin hiç kurmadığı bir şeyi ölçer.
- **Bir kolun skoru düşükse önce kolun tutarlı olduğu doğrulanır.** Bozuk bir kolun skoru da
  bir sayıdır, ama ölçüm değildir.
- **Örnekleme ayarı rapora yazılır.** Açgözlü ölçülen bir sayı, sunucunun sıcaklığıyla çalışan
  üretim hakkında bir şey söylemez.

### 15.3 Prompt ve model ilkeleri

1. **Vaka listesi değil, ilke yazılır.** "Şöyle olursa şunu yap" listesi, parametresi biraz
   değişmiş bir durumda modeli çaresiz bırakır. Eksik olan kavram yazılır.
2. **Uydurma, yasağa cevap vermez.** "Yaptığını ancak sonucu görünce söyle" gibi bir yasak
   işe yaramaz: model kuralı çiğnediğini düşünmez, konuşmanın bilgiyi zaten verdiğine inanır
   ve daha ayrıntılı uydurur. Öğretilecek olan ayrımdır: konuşmada söylenen bir **iddiadır**,
   tool sonucu **bilgidir**.
3. **Aynı düzeydeki iki ilkeden model birini seçer.** Öncelik açıkça yazılır: eksik alan
   kontrolü, çağırmanın rakibi değil **önkoşuludur**.
4. **Kalan fark bir-iki senaryoya inince durulur.** Devam etmek metni kümeye uydurmaktır.
5. **Rol metni A/B'si bütün kümeleri koşar.** Bir prompt düzenlemesinin açtığı arıza sınıfı,
   hedeflenmeyen kümede görünür.
6. **Sonuç yalnızca koştuğu modele aittir.** Aynı metin güçlü bir modelde tutup zayıf bir
   modelde çökebilir; iyi ölçülen bir metin bu yüzden sağlam değildir. Model ya da önek
   değişirse rol metni yeniden ölçülür.
7. **Persona modele kimden bahsettiğini değil, kime konuştuğunu söyler.** Rapor üslubu
   verilen model üçüncü şahsa geçer ve kendi talimatlarını sesli okunacak metne sızdırır.
   İlke: *kişiye konuş, hakkında değil; yalnızca sesli söyleyeceğini yaz.*
8. **Bir takas bilerek seçilir:** gereksiz bir çağrı gecikmedir; "evet, kurdum" deyip kurmamak
   ise bir hatadır.

---

## 16. Açık maddeler

Cevaplanmadan uygulanmaz; yerine varsayım konmaz (§0). Numaralar sabittir.

1. **LLM modeli.** Seçim ölçümle yapılır. Ölçülecekler: hız, davranış kümeleri (hız,
   davranış kalitesi değildir), ilk token süresi ve prefill token sayısı,
   eşzamanlı oturumlarda hız ve önbellek.
2. **STT modeli**, nerede çalıştığı ve sözün bittiğine nasıl karar verildiği.
3. **Her çıkış dili için TTS sesi.** Profillerdeki her çıkış dili için bir ses gerekir.
4. ✅ §7
5. **Konuşmacı tanıma:** model, eşleşme eşikleri, kayıt için gereken ses süresi, "güçlü
   eşleşme"nin tanımı.
6. ✅ §10.3
7. ✅ §10.3
8. **Wake word:** motor, kelime, istemcide mi sunucuda mı çalışacağı.
9. **Ses taşıma biçimi:** PCM mi sıkıştırma mı. Sürekli STT yüzünden ses sürekli akar; karar
   bant genişliği ölçümüne bağlı.
10. **Karar modeli:** model, profillerdeki dillerde başarımı, eşikler, hangi noktalarda devreye gireceği.
11. **Paylaşılan kaynakta çakışma:** iki turun aynı cihaza çelişen eylem vermesi.
12. **Oturumun zaman sınırı:** cihaz başına bağlamın ne zaman sıfırlandığı, ya da hiç
    sıfırlanmadığı.
13. **Ortak saatin makineler arasında nasıl sağlandığı.**
14. **Medya deposunun biçimi ve boyutu.**
15. **Saklama süreleri:** depo başına değerler, tanımsız seslerin kayıtları dahil.
16. **Yedekleme:** sıklık, sayı, konum.
17. ✅ §14
18. **İlk ses hedefi: kapsam gereği sayısız.** Sahibin kararı: bir eşik bir yükümlülük üretir.
    İlk ses süresi ölçülür ve raporlanır, ama ona bir hedef sayı önerilmez.
19. **`bash`'in alanı dışında sistemi değiştiren işler** (ekran parlaklığı, çalışan bir
    programı kapatma, zamanlı kapatma gibi) tool'u yoksa nasıl yapılır; `DANGEROUS` sınıfına
    girecek bir skill olacak mı. Gerçek bir ihtiyaçla karar verilir.
    Konuşulmuş yön (karar değil): eylemin hedefi oturumun cihazıdır ve cihazı taşıma zaten
    bildirir (§10.1); tarayıcı sistemi değiştiremez, bu yüzden eylem cihazdaki yerel bir parçada
    (telefon uygulaması, masaüstü ajanı) çalışır. Komut ya istemcinin açık bağlantısından gider
    ya da cihazdaki bir servise ağ üzerinden. İstemci tipi yerine istemci bağlanırken
    yeteneklerini bildirir: tipler her yeni cihazda çoğalır, yetenek cihazda olanı söyler; beyan
    kimlik değildir, yalan bir yetenek yetki kazandırmaz. Katalog sabit kalır (§8.3, §9); yeteneği
    olmayan cihazda çağrı, ret gibi tool sonucu olarak döner. Cihazın yetenekleri bağlam
    bloğuna girebilir.
20. **Tool sonucu boyut sınırının değeri** (§8.8): tool başına mı, tek değer mi.
21. **Düşünmenin (reasoning) yönetimi:** hangi adımda açık olduğu, bütçesi, kimin karar verdiği. Modele özgü değil, genel bir politika olarak.
22. **Onay promptlarının dile bağlılığı** (§10.5, §8.6, §2.1). Bugünkü gerçekleme sahibin
    dilini kavrama gömüyor: çözümleyici promptu cevabın "genellikle Türkçe" geleceğini
    varsayıyor ve örnekleri yalnızca Türkçe ve İngilizce; soru yazıcısının dil etiketi örneği
    tek bir dil çiftine (`<tr>`) bağlı. Çıkış dilinin kaynağı kapandı (§8.6). Açık olan: başka
    dilde konuşan biri için çözümleyicinin nasıl çalışacağı (örneksiz model Türkçe olumsuzluğu
    göremedi; örnekler kişinin dilinden mi gelir, çok dilli mi olur) ve etiket örneğinin dil çiftine bağlanmadan nasıl yazılacağı.
    Değişiklik yeniden ölçüm ister.

---

## 17. Uygulama sırası

Sözleşmeler baştan tanımlanır, gerçeklemeler dilim dilim gelir. Bir sözleşme, ilk gerçek
gerçeklemesiyle doğrulanınca kesinleşir; `schema_version` bunun içindir. Her dilim uçtan uca
çalışır ve §15.1'in kapılarından geçer.

Ödünç alınan çerçevenin verdiği parçalar (mesaj listesi, model servisi, akış, söz kesme,
taşıma) sözleşme olarak yeniden tanımlanmaz; Mayen'in sözleşmeleri onun üstündeki katmandır.

**Sözleşme sırası** (en çok şeyin bağlı olduğu ve sonradan değiştirmesi en zor olandan):

1. Tool/skill sözleşmesi: `ToolSpec`, etki sınıfı, hassasiyet, sonuç durumları ve her
   tool'un önündeki yetki sarmalayıcısı
2. Model deposu: her istek hangi rol için gittiğini taşır (§8.10), model, yuva ve ayarlar
   depodan okunur. Rol sonradan eklenseydi, kip ya da model değişikliği sözleşmeyi
   değiştirirdi.
3. Tetikleyici ve oturum: tetikleyicinin turu nasıl başlattığı, kesme/kuyruk politikası,
   oturum başına hat
4. Depo portları ve olay zarfı: medya türünden bağımsız kayıt, ortak saat (§5.5)
5. Çıkış/kanal, karar, hafıza, profil, iş ve zamanlayıcı portları

**`bash` kendi izole alanıyla birlikte gelir.** Alan olmadan gelen bir `bash` gerçek makineye
doğrudan erişir; güvenliği tümüyle alana dayandığı için (§9.4) alan sonradan eklenemez.

---

## 18. Değişmez kurallar

Tercih değil, sert kısıt. Bunlardan birini bozan kod, çalışsa bile yanlıştır.

1. Yapılandırılmış veri deposunun tek sahibi depo adaptörüdür; başka hiçbir süreç dosyayı açmaz.
2. Çekirdek süreç model yüklemez; modeller kendi süreçlerindedir ve adresleri config'tedir.
3. Sistem promptu tur içinde değişmez. Değişken içerik daima önekin sonundadır ve arkasına
   sabit bir şey konmaz.
4. Yetkilendirme koddadır. Prompt bir güvenlik sınırı değildir. Katalog konuşana göre değişmez.
5. Onay serbest metinden anahtar kelimeyle çıkarılmaz. Zaman aşımı reddir.
6. Sahip rolü sesle verilemez. Hiçbir rol, kişinin kendi iddiasıyla verilmez.
7. Kullanıcıya ait metin alanına sistem verisi (kimlik, rol, politika) yazılmaz.
8. Model çıktısı kabukta yalnızca `bash`'in izole alanında çalışır; başka hiçbir yerde model
   değeri argv'ye girmez. `bash` gerçek dosyaya yazmaz.
9. Bir skill tek dosyada tanımlanır.
10. Token sayısı tahmin edilmez, sayaca sorulur.
11. Arka plan LLM işleri aktif turla yarışmaz; tur kuyruğa girdiği anda iptal edilir.
12. Her tur her aşamasında iptal edilebilir. İptalin kapsamı turdur, kuyruğun tamamı değil.
13. Hiçbir hata sessizce yutulmaz.
14. Ölçülmemiş bir performans iddiası dokümana yazılmaz.
15. Onay durumuna onay cümlesi okunmadan önce girilir.
16. Söz kesildikten sonra kesilen cevabın sesi çalınmaz.
17. Ses izi yalnızca kişinin açık rızasıyla çıkarılır; geçmiş kayıtlardan geriye dönük
    çıkarılmaz.
18. Mayen'in her sözleşmesi `schema_version` taşır.
19. Gizli bilgi config dosyasına yazılmaz; yalnızca ortamdan okunur.
20. Sistem kullanıcıya önceden yazılmış bir cümle seslendirmez; dil yalnızca modelden gelir.
21. Onay cümlesinde plandaki her argüman değeri aynen geçer; geçmezse sesli onay yapılmaz.
22. Unut ve sil kararlarını yalnızca sahip verir.
23. `bash` alanına yalnızca izin listesindeki yollardan kopya alınır; gizli anahtar dizinleri
    ve `.env` dosyaları hiçbir zaman kopyalanmaz.
