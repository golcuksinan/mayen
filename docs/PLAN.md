# Mayen — Kod Yazma Planı

`docs/ARCHITECTURE.md` ne yapılacağını söyler. Bu doküman **hangi sırayla** yazılacağını
söyler. Mimari kararlar burada verilmez; verilmesi gerekenler §19'a geri işlenir.

Planın dayandığı tek gözlem şu: **§19'daki açık maddelerin neredeyse hiçbiri ilk altı iş
paketini engellemiyor.** §19 "açık madde cevaplanmadan uygulanmaz" der ve bu doğrudur, ama
yanlış okunursa her şey durur. Gerçekte model seçimleri (§19.2), konuşmacı eşikleri
(§19.3), gecikme hedefi (§19.4), ses formatı (§19.5), wake word (§19.6) ve GUI bağlayıcısı
(§19.11) iskeleti, veri katmanını, politikayı, durum makinesini veya tool kayıt defterini
engellemez. Sadece §19.7/8/9 birer tool gövdesini, §19.14 ise Faz 4'ü engeller.

---

## P0 — Doküman kapatma ✅ TAMAMLANDI (2026-08-06)

Mimari incelemesinde çıkan on bir kusurun tamamı `ARCHITECTURE.md`'ye işlendi. Verilen
kararlar:

| # | Karar | Nereye işlendi |
|---|---|---|
| A2 | Kademe sayısı **dört**: sahip / kayıtlı kişi / bekleyen / tanınmayan | §2 |
| A3 | Konuşmacı tanıma **kendi sürecinde, HTTP arkasında, CPU'da**. Kural 2'ye istisna açılmadı; dört model süreci var, üç değil; VRAM bütçesi LLM/STT/TTS'e kalıyor | §2, §3 |
| A1 | Bütçe aşımında **sert kırpma**, ardından **boştaki ilk fırsatta özetleme**. Kırpılan mesaj DB'den silinmez. Kural 11 korunuyor. Kırpma-özet arası boşluğu kapatan şey olgu deposu. Kırpma istisnai olay; sıklığı ölçülür, sık kırpılıyorsa bütçe yanlıştır | §2, §8.1, §11.1, §11.2 |
| B1 | Her ses parçası **`(turn_id, seq)`** taşır. İptalin kapsamı tur, kuyruk değil — proaktif hatırlatıcı söz kesmeden etkilenmez (B2) | §5, §12, §13, Kural 12/17 |
| B3 | **`ONAY_BEKLİYOR`'a okuma öncesinde girilir.** Okuma sırasında söz kesme sesi durdurur, durum ve bekleyen plan yaşar; segment doğrudan çözümleyiciye gider | §5, §8.5, Kural 16 |
| B5 | Sunucuda `DİNLİYOR` yok (`IDLE → ÇÖZÜMLÜYOR`); "aynı anda tek tur" kapsamı **global** | §5, §2, Kural 15 |
| B4 | Arka plan LLM işleri **preempt edilebilir**; tur kuyruğa girince iptal, yarım sonuç yazılmaz | §11.3, Kural 18 |
| A4 | Alanlar çok kelimeli olabilir, bir sonraki bilinen bayrağa kadar okunur; **en fazla bir alan** bayrak gibi görünen metin barındırır ve sonda durur | §8.3, §9.1 |
| C3 | GBNF, tool çağrısı dalını **sabit zorunlu bir önekle** başlatır — dallanma ilk token'da belli | §6 |
| A5 | Tool bildirimleri Faz 0'ın önüne, asgari istemci Faz 5'e alındı | §18 |
| C1 | Türkçe içeriğin İngilizce TTS'ten geçmesi **yeni açık madde §19.15** oldu; Faz 2'de karara bağlanacak | §19 |

Ayrıca §17.5'e üç yeni durum makinesi testi eklendi: onay okunurken söz kesme, iptalden
sonra gelen eski `turn_id`'li parça, söz kesme sırasında kuyruktaki proaktif bildirim.

Kalan açıklar §19'da. Yakın vadede engelleyenler yalnızca §19.7 / 8 / 9 (birer tool gövdesi)
ve §19.14 (Faz 4). **P1 başlayabilir.**

---

## P1 — İskelet ve araç zinciri ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** yok. İlk iş.

- **Yorumlayıcı sürümünü açıkça sabitle.** Sistem varsayılanı yeni; torch / speechbrain /
  faster-whisper sınıfı paketlerin tekerlekleri yeni Python sürümlerinin gerisinde kalır.
  Modeller P-Faz 2'ye kadar gelmiyor, ama o gün gelip de yorumlayıcı yüzünden geri dönmek
  en aptalca kayıp olur. Sürümü seçmeden önce hedef paketlerin tekerlek durumunu doğrula.
- `src/mayen/` düzeni, §4'teki katmanların her biri bir paket.
- ruff + pytest + mypy (`strict`). structlog.
- **Yapılandırma ve sır yönetimi.** §19.7 ile sisteme ilk sır giriyor (OpenWeatherMap
  anahtarı). Bir kez kurulur: yapılandırma tipli ve tek yerde, sırlar ortam
  değişkeninden, `.gitignore` ilk günden doğru. Sonradan eklenen sır yönetimi, önce
  depoya girmiş bir anahtar demektir.
- **Katman sınırı testi.** §4'ün tek yönlü bağımlılık kuralını mekanik olarak zorlayan bir
  test: paketlerin import'larını gezer, alt katman üst katmanı import ediyorsa kırılır.
  Bu, tüm plandaki en ucuz ve en yüksek getirili tek parça — kuralı yorumdan çıkarıp
  çalıştırılabilir hale getiriyor.

**Bitti kriteri:** `ruff check` temiz, `mypy` temiz, `pytest` yeşil (içinde sınır testi
var ve kasıtlı bir ihlalle kırıldığı doğrulanmış). — **Karşılandı: 27 test yeşil.**

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **Python 3.13**, `>=3.13,<3.14` | Sistem yorumlayıcısı 3.14; üst sınır uv'nin oraya kaymasını engelliyor. torch 2.13, ctranslate2 4.8, onnxruntime 1.28 hepsi cp313 tekerleği yayınlıyor — pin öncesi doğrulandı |
| **uv**, `uv.lock` depoda | Yorumlayıcıyı da uv yönetiyor; ortam birebir yeniden üretilebilir |
| **Yapılandırma: `dataclass`, pydantic yok** | Beş alan için harici bağımlılık §2'nin uyardığı spekülatif esneklik. Yapılandırma diş çıkarırsa geçilir |
| **`Secret` sarmalayıcısı** | `repr`/`str` maskeli; sır structlog alanına veya traceback'e kazara girse bile sızmaz. Değere yalnızca `.reveal()` ile ulaşılır |
| **Geçersiz yapılandırma `ConfigError` fırlatır** | Sessizce varsayılana düşmek Kural 13'ün ihlali |
| **Adlandırma** | API adları İngilizce, alan sözlüğü Türkçe, tanımlayıcılar aksansız. Gerekçesiyle `CLAUDE.md`'de |
| **`RUF001/002/003` kapalı** | Türkçe metinde her `ı`/`ş`/`ğ` için yanlış alarm |
| **Katman rütbeleri birbirinden farklı** | Eşit rütbe karşılıklı import, yani sessiz döngü demek. Yanlış sıralamanın bedeli gürültülü bir ret; eşitliğin bedeli kimsenin görmediği bir döngü |
| **`scheduler`, `transport`'un altında** | Proaktif ses §12'ye göre oturum kuyruğuna girer; `scheduler`'ın `transport`'a ihtiyacı yok |
| **`obs` en dipte** | P3'te tur izi `data`'ya inmek isteyecek ve sınır testi reddedecek. Çözüm: `obs` bir `TraceSink` `Protocol`'ü tanımlar, `data` uygular — bağımlılık tersine döner (§4'ün ports & adapters kalıbı) |

### Ertelenen: STT

Uygulama `--stt` / `--tts` / `--llm` bayraklarıyla **hangi adaptörün bağlanacağını** seçer
(`real` \| `fake`). "Özellik açık/kapalı" değil — üst katmanlar hiç değişmez, yalnızca uç
değişir. `fake` STT, istemciden gelen **metin segmentini** transkript sayar; böylece gerçek
STT gelmeden uçtan uca yazışılabilir. Bu zaten P3–P8'in yazdığı sıra; bayrak onu çalışma
anında da erişilebilir kılıyor.

**P3'e düşen sonuç:** `transport/` çerçeve tipleri arasında ses segmentinin yanında bir
**metin segmenti** olmalı ve o da §13'ün `(turn_id, seq)` sözleşmesini taşımalı. Aksi
hâlde gerçek STT geldiğinde protokol yeniden açılır.

---

## P2 — Veri katmanı (§16) ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P1. **Engelleyen açık madde:** yok (§19.12 yalnızca yapılandırma değeri).

- SQLite tek dosya, WAL, tek sahip.
- Şema v1 + migration koşucusu: sıralı, idempotent, **hata sessizce yutulmaz** (Kural 13;
  §16 bunu ayrıca vurguluyor çünkü sessiz yutma şema sapmasını gizler).
- Repository modülleri. `data/` dışında SQL yok — sınır testi bunu da yakalayabilir.
- **Yedekleme:** SQLite'ın kendi backup API'si ile, dosya kopyalayarak değil. Döndürmeli.
  Hedef konum ve sıklık yapılandırmadan gelir (§19.12 açık kalabilir, kod yazılabilir).
- Tablolar (§16): açılış kayıtları, konuşma geçmişi, özetler, olgular, kişiler + ses
  profilleri, notlar, ders programı, zamanlanmış görevler, tur izleri.

**Bitti kriteri:** boş dosyadan migration tam çalışıyor; yedekten geri dönülen veritabanı
açılıyor ve okunuyor; repository testleri yeşil. — **Karşılandı: 94 test yeşil.**

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **Tek bağlantı, muteksle** | SQLite'ta yazmalar zaten serileşir; WAL'da bile tek yazar olur. Bağlantı çoğaltmak eşzamanlılık kazandırmaz, kilit beklemesini `SQLITE_BUSY`'ye çevirir. Karşılığı tek bir kural: **bir transaction hiçbir zaman bir LLM/HTTP çağrısını kapsamaz.** Ölçüm çekişme gösterirse iş parçacığı başına bağlantıya geçmek `data/` içinde yerel bir değişiklik |
| **Açık `COMMIT`/`ROLLBACK` SQL'i** | `autocommit=True` altında `Connection.rollback()` **sessiz bir no-op**: işlem açık kalır, geri alındığı sanılan yazma sıradaki COMMIT'e yapışır. Deneyerek doğrulandı; `test_failed_transaction_leaves_nothing_behind` geri dönüşü engelliyor |
| **Migration'lar ayrı `script()` yolundan** | `executescript` bekleyen işlemi kendiliğinden COMMIT ediyor, yani `transaction()` içinden çağrılamaz — atomikliği sessizce bozar. İşlem denetimi betiğin kendi içinde, sürüm damgası DDL ile aynı işlemde |
| **Sürüm `PRAGMA user_version`'da** | SQLite'ın kendi alanı; ayrı bir sürüm tablosuna ve o tablonun kendi migration'ına gerek yok |
| **`STRICT` tablolar** | Varsayılan SQLite'ta `token_count` sütununa `"çok"` yazılabilir ve sessizce kabul edilir |
| **Zaman: ISO-8601 UTC metni** | Sıralaması kronolojik, gözle okunur, SQLite tarih fonksiyonları çalışır. Biçim `data/clock.py`'de tek yerde |
| **Repository'ler dataclass döndürür** | `sqlite3.Row` döndürmek sütun adlarını üst katmanlara sızdırır ve "SQL `data/` dışına çıkmaz" kuralını kâğıt üstünde bırakır |
| **`Tier` / `TaskStatus` `data`'da** | Saklanan değerler ve CHECK kısıtı zaten bu sözlüğün sahibi. `policy`, `data`'yı import edebilir; tersi §4'e aykırı |
| **Yedek: `.partial` → `rename`** | Yarım kalmış bir yedek `mayen-*.db` desenine uymaz, rotasyon onu sağlam sanıp yerine sağlamı silmez |
| **`backup_keep < 1` reddedilir** | `keep=0` "yedek alma" demek değil, ayarın yanlış yazıldığı anlamına gelir ve ancak lazım olunca fark edilir |
| **Sınır testine ikinci denetim** | `data/` dışındaki SQL dizeleri AST'den yakalanıyor; repository kalıbı ancak mekanik olarak zorlanınca gerçek |

**P3'e düşen:** `obs`'un `TraceSink` `Protocol`'ü. `TraceRepository` şu an doğrudan
çağrılıyor; tur izini `obs` yazmak isteyince sınır testi reddedecek ve bağımlılık
tersine dönecek (P1'de öngörüldüğü gibi).

---

## P3 — Sözleşmeler: protokol, adaptör arayüzleri, fake'ler ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P1, P0/B1, P0/A3. **Engelleyen açık madde:** yok — §19.5 (PCM/Opus)
çerçevede bir kodek alanıyla açık bırakılır, seçim sonra yapılır.

- `transport/`: tipli çerçeveler, sürümlü el sıkışma (uyuşmazlıkta açık hatayla ret,
  sessizce farklı davranış yok), backpressure.
- **Ses çerçevesi `(turn_id, seq)` taşır.** İstemci aktif `turn_id` dışındaki her şeyi
  sessizce atar. İptal turun kapsamına bağlıdır, kuyruğun tamamına değil — böylece söz
  kesme, kuyruktaki proaktif hatırlatıcıyı düşürmez (B1/B2).
- `adapters/`: LLM, STT, TTS, konuşmacı tanıma için `Protocol` tanımları + her biri için
  fake. Fake'ler oyuncak değil — tüm P4–P8 bunların üstünde test ediliyor.
- `obs/`: tur izi kaydı ve `turn_id` üretimi. İz, mesaj gövdelerini kopyalamaz;
  veritabanındaki kayda referans + içerik özeti tutar (§15'in kayıt hacmi kuralıyla
  çakışmasın diye).

**Bitti kriteri:** fake'ler Protocol'lere karşı tip denetiminden geçiyor; bir tur izi
yazılıp geri okunabiliyor; el sıkışma sürüm uyuşmazlığı testi yeşil. — **Karşılandı:
143 test yeşil.**

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **`transport/` yalnızca sözleşme; WebSocket sunucusu yok** | P3'ün bitti kriteri çerçeve, el sıkışma ve backpressure istiyor, sunucu değil. Konuşacak istemci Faz 5'te geliyor; sunucuyu şimdi yazmak, test edilecek karşı tarafı olmayan kod demek |
| **Kontrol çerçeveleri JSON metin, ses çerçeveleri ikili** | Sesi base64'e sokmak her parçayı %33 şişirir ve tur boyunca sürekli kodlama yapar. Her şeyi ikili yapmak protokolü gözle okunamaz hale getirir. İkili çerçeve melez: `[4B başlık uzunluğu][JSON başlık][ham yük]` — başlık okunur, yük kopyalanmaz |
| **Gelen ses `segment_id`, giden ses `(turn_id, seq)` taşır** | Asimetri §7'den geliyor: endpointing istemcide, sunucuya tamamlanmış segment gelir ve o segment henüz bir tura ait değildir — `turn_id`'yi sunucu üretir. `Transcript` çerçevesi ikisini birbirine bağlar. Gelen tarafa uydurma bir `turn_id` koymak, istemcinin sunucunun kimliğini tahmin etmesi demek olurdu |
| **Metin segmenti birinci sınıf çerçeve** | P1'in ertelenmiş STT kararı. Bu yol protokolde yoksa gerçek STT geldiğinde protokol yeniden açılır |
| **Bilinmeyen tip / eksik / fazla alan reddedilir** | Kural 13. Sessizce yok saymak, sürüm uyuşmazlığını el sıkışmadan kaçırıp turun ortasında gizli davranış farkına çevirir. Başlık uzunluğuna da üst sınır kondu: bozuk bir uzunluk sağlamından ayırt edilemez ve keyfi büyüklükte ayırma isteğine dönüşür |
| **El sıkışma reddi istisna değil `Rejected` çerçevesi** | Ret de protokolün parçası: istemcinin sunucu sürümünü ve sebebi görebilmesi gerekiyor |
| **Kuyruk dolduğunda yazan bekler, çerçeve düşmez** | §6'ya göre sıra bozulması kabul edilemez. Beklemek baskıyı kaynağa kadar geri yürütür (TTS yavaşlar); sınırsız kuyruk ise belleği şişirip gecikmeyi kimsenin ölçmediği yere saklar. Tek istisna iptal ve kapsamı **tur** (B1/B2) |
| **Adaptörler async, iptal ayrı jeton değil** | `stream`/`synthesize` `AsyncGenerator` döndürüyor; `aclose()` sözleşmenin parçası. Kural 12'nin iptal yolu asyncio'da zaten var — ikinci bir yol eklemek, ikisinden birinin unutulması demek |
| **`count_tokens` arayüzün parçası** | Kural 10: çağıran tarafa tahmin edebileceği bir yol bırakılmıyor. Sahte LLM bile **sayaç**, tahminci değil |
| **Konuşmacı adaptörü yalnızca gömü çıkarır** | Skor ve eşik §19.3'te açık, karşılaştırma `policy`'nin işi. Skorlamayı adaptöre koymak açık bir maddeyi varsayımla kapatmak olurdu |
| **`obs` → `TraceSink` `Protocol`, `data` uygular** | P1'de öngörülen an geldi: iz kalıcı yazılmalı ama `obs` en dipte. Bağımlılık tersine döndü, sınır testi dokunulmadan yeşil kaldı |
| **`TurnTrace` aşama süresini `monotonic` ile ölçer** | Duvar saati tur ortasında geri alınırsa negatif süre yazılır ve ölçüm sessizce bozulur. Aşamanın *ne zaman* başladığı ayrı bir şey; onu `data/clock.py` yazıyor |
| **Aşama, istisna çıksa da yazılır** | Ölçümün en çok işe yaradığı an, bir şeyin yavaşlayıp patladığı andır |
| **`pytest-asyncio`, `asyncio_mode = "auto"`** | Sistemin tamamı asyncio; her testi tek tek işaretlemek gürültü |

**P4'e düşen:** `StateChanged.state` şimdilik düz metin — durum sözlüğünün sahibi oturum
aktörü ve o katman henüz yok. Enum P4'te doğunca tipi `transport`'a bağlanır
(`transport → session` §4'e uygun, tersi değil).

---

## P4 — Oturum aktörü ve durum makinesi (§5)

**Bağımlılık:** P3, P0/B3, P0/B5. **Engelleyen açık madde:** yok.

Saf mantık, I/O yok. Bu paketin tamamı GPU'suz ve milisaniyeler içinde test edilebilir
olmalı.

- Cihaz başına aktör, kendi kuyruğu, iptal edilebilir aktif tur tutamacı.
- **İptal edilebilirlik baştan tasarlanır** (Kural 12). Sonradan eklenen iptal, iptal
  değildir — her aşama bir iptal jetonu taşır.
- `ONAY_BEKLİYOR` ve `KAYIT` kapalı durumlar: gelen metin ajana hiç ulaşmaz.
- Varlık takibi: cihaz başına son etkileşim zamanı (§12 buna dayanıyor).

**Bitti kriteri:** §17.5'teki liste yeşil — söz kesme, zaman aşımı, onay sırasında konu
değiştirme, eşzamanlı segment, kayıt sırasında kesinti. Artı B3'ten gelen yeni vaka:
onay okunurken söz kesme. — **Karşılandı: 172 test yeşil.** Listenin son iki maddesi
(iptalden sonra gelen eski `turn_id`'li parça, söz kesme sırasında kuyruktaki proaktif
bildirim) P3'te `SendQueue.cancel_turn` ile zaten kapanmıştı.

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **Geçiş tablosu eksiksiz; tanımsız çift `InvalidTransitionError`** | Sessizce yerinde kalmak Kural 13 ihlali: sıra hatası ancak çok sonra, başka bir yerde patlar. Bu yüzden `ONAY_BEKLIYOR`'un kendine dönen geçişi de tabloda açıkça yazılı — "yazılmayan kendine döner" kuralı, okuyanın hangi olayın beklendiğini göremediği bir tablo demek |
| **Aktör cihaz başına, tur kilidi global** | §5 ikisini ayrı söylüyor. Kuyruk cihaz başına, çünkü bir cihazın segmenti diğerinin olaylarını bekletmemeli; tur global, çünkü tek GPU ve tek konuşma akışı var. `asyncio.Lock` bekleyenleri geliş sırasında uyandırıyor |
| **Koşucu kendi `Task`'ında** | İptalin tutunacak bir yeri olması için. Ayrı iptal jetonu yok (P3 kararı): asyncio'nun yolu zaten var, ikincisi unutulacak ikinci yol demek |
| **`TurnRunner` ve `SessionSink` `Protocol`** | `turn` katmanı henüz yok ve `transport` `session`'ın *üstünde* — aktör `StateChanged`'i kendisi üretemez. `obs`/`TraceSink` kalıbının aynısı |
| **`Segment.payload` opak** | Aktör içeriğe hiç bakmıyor; sesi çözen de metni okuyan da koşucu. Ses/metin ayrımını `session`'a koymak `transport`'un çerçeve tiplerini aşağı sızdırırdı |
| **Kapalı durumda segment yeni tur açmaz, turun kuyruğuna girer** | §5: `ONAY_BEKLIYOR`/`KAYIT`'ta gelen metin ajana *hiç* ulaşmaz. Sıraya alıp turun bitmesini beklemek de olmazdı — onay bekleyen tur zaten o segmenti bekliyor, sistem kendini kilitlerdi |
| **`ONAY_BEKLIYOR`'da söz kesme turu öldürmez** | B3: ses durur (`speech_stopped`), durum değişmez, plan yaşar, iptal bildirimi gitmez |
| **İlgisiz `turn_id`'li söz kesme yok sayılır, ama loglanır** | §13 iptal sonrası ağda kalan ölü tur trafiğini zaten öngörüyor: hata değil. Sessiz de değil — iptal sonrası trafiğin ölçülebilmesi gerekiyor |
| **Patlayan tur durumu `IDLE`'a çeker** | Aksi halde sistem `ÇÖZÜMLÜYOR`'da kalır ve bir sonraki segment ikinci bir hata olarak geri gelir. Aktör hatayı kayda düşüp sıradaki segmente devam ediyor (Kural 13) |
| **Onay zaman aşımı sayacı burada değil** | §10 onayın sahibi; aktör yalnızca `ONAY_ZAMAN_ASIMI` olayını tabloya uyguluyor. Sayacı buraya koymak P5'in kararını varsayımla kapatmak olurdu |

**P5'e düşen:** §5'in tablosu `DÜŞÜNÜYOR` durumunda söz kesmeyi tanımlamıyor; kod da
tanımlamıyor, `InvalidTransitionError` yükseltiyor. Kullanıcının ses başlamadan söze
girmesi gerçekçi bir senaryo — tabloya satır eklenecekse bu **doküman kararı**, kodda
varsayımla kapatılmadı.

---

## P5 — Politika (§10)

**Bağımlılık:** P4, P0/A2. **Engelleyen açık madde:** §19.14 (sahibin ilk kurulumda nasıl
atandığı) — kodu engellemez, ilk gerçek kullanımı engeller.

- Etki sınıfı × kademe matrisi, kodda, **tek zorlayıcı nokta** (Kural 4).
- Onay çözümleyicisi: kısıtlı çıktı, üç sonuç (onay / red / belirsiz). Serbest metinde
  anahtar kelime araması **yok** (Kural 5). Zaman aşımı = red.
- Argüman doğrulaması onay sorulmadan **önce** çalışır — kullanıcıdan bozuk bir işlemi
  onaylaması asla istenmez (§8.5 adım 1).

**Bitti kriteri:** §17.4 — her (etki sınıfı × kademe) hücresi için bir test. Dört kademe ×
dört etki sınıfı = on altı hücre, hepsi ayrı ayrı. — **Karşılandı: 206 test yeşil.**

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **`Effect` `policy`'de, `data`'da değil** | `Tier`'ın aksine saklanan bir değer değil: şemada etki sınıfı sütunu yok, tool tanımı kodda. Kararı veren katman sözlüğün de sahibi; `tools` (rütbe 5) `policy`'yi (6) import ediyor, tersi §4'ü kırardı |
| **`Authority` `Tier`'dan ayrı** | Matris dört kademe tanımak zorunda, `Tier` üç taşıyor — `TANINMAYAN`'ın rehberde satırı yok (§10.1). Dördüncüsü kimliği yetkiye çeviren yerde; `data`'nın CHECK kısıtına dokunulmadı |
| **Matris hücre hücre yazıldı** | `dict.fromkeys` gibi bir kısayolla üretilen matris, testte de üretenin varsayımını doğrular. Eksik hücre `KeyError` — sessiz "izin yok" değil (Kural 13) |
| **`SAHİP × GERİ_ALINAMAZ` = onay, izin değil** | §10.2 sahibe "tümü" derken parantezi de yazıyor. Onay yetki sorusu değil niyet sorusudur; sahiplik onu kaldırmaz |
| **`authorize()` tool adına bakmaz** | Karar yalnızca etki sınıfından çıkar (§9.1). Ada göre istisna yazmak, doğrudan yasaklanmış olan ikinci bir "hassas tool listesi" kurmaktır |
| **Gramer dışı yanıt `BELİRSİZ` değil, hata** | Belirsiz saymak bozuk servisi kullanıcının kararsızlığı gibi gösterir; ikinci soru da aynı bozuk servise gider ve akış sessizce iptalle biter (Kural 13) |
| **Zaman aşımı süresi varsayılansız** | Kural 5 zaman aşımının *sonucunu* söylüyor, süresini değil; doküman da bir sayı vermiyor. Sayaç `policy`'de (P4'ün bıraktığı yer) ama değeri çağıranın |
| **Argüman doğrulaması burada değil** | Şemalar `tools`'ta ve `policy` onları import edemez. Sıra yine de korunuyor: akış bir `PendingPlan`'dan başlıyor, o da okunacak cümleyi istiyor — geçersiz argümanla o cümle kurulamaz (§8.5 adım 1) |

**P5'ten devreden:** P4'ün bıraktığı `DÜŞÜNÜYOR`'da söz kesme satırı hâlâ açık. Politika
katmanı onu kapatmadı, çünkü kapatacak olan yer §5'in tablosu — doküman kararı.

---

## P6 — Tool kayıt defteri, katalog, gramer ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P2, P5, P0/A4, P0/C3. **Engelleyen açık madde:** yok — §19.7, §19.8 ve
§19.9 kapatıldı, katalogdaki her tool'un gövdesi yazılabilir.

- Kayıt defteri. Bir tool = bir dosya; şema, gövde ve politika sınıfı aynı yerde (Kural 9).
- Her tool bildirir: ad, açıklama, tipli argümanlar, **etki sınıfı**, zaman aşımı, kullanım
  metni (`--help` çıktısı).
- Tool'lar veriye yalnızca kendilerine verilen bağlam nesnesi üzerinden erişir.
- Tool sonucu yapılandırılmış: başarı, veri, okunacak biçim, hata — ayrı alanlar.
- Katalog metninin sistem promptuna işlenmesi (§8.4). Promptun bağlam bütçesindeki payı
  **ölçülür** ve bir sayı olarak raporlanır.
- **GBNF üretimi kayıt defterinden**, her iki aday biçim için. Dallanma ilk token'da
  ayırt edilebilir (C3).

§9.2 kataloğunun tamamı yazılabilir durumda. Üç tanesi kapatılan açık maddelere dayanıyor:
hava durumu OpenWeatherMap'e (anahtar ortamdan, depoya girmez), ders programı depodaki
program dosyasına, Wake-on-LAN yapılandırmadaki ad→MAC listesine.

**Bitti kriteri:** katalog metni üretiliyor; GBNF her iki adayda geçerli ve dallanma
testi yeşil; bloke olmayan tool'ların testleri yeşil. — **Karşılandı: 265 test yeşil;
katalog 14 tool / 70 satır; iki gramer de defterden üretiliyor.**

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **Kullanım metni üretilir, ayrı alanda yazılmaz** | İmzadan bağımsız ikinci bir metin, imza değişince sessizce yalan söyler — §9.1'in "dağıtılmış tanım, dokümanın koddan sapmasının sebebidir" cümlesinin ta kendisi |
| **`Tool.validate()` `tools`'ta** | §8.5 adım 1 doğrulamayı onaydan önce istiyor ve şemalar burada; `policy` `tools`'u import edemez. Hata `usage()`'ı üstünde taşıyor, çünkü modele geri beslenen şey o |
| **Serbest metin alanı kuralı tanım anında zorlanıyor** | A4'ün "en fazla bir alan, o da sonda" kuralı `ToolSpecError`. Çalışma anında keşfedilseydi, bozuk imza ancak yanlış ayrışan bir çağrıyla belli olurdu |
| **Bağlam nesnesi repository taşıyor, `Database` değil** | Tool'a verilen şey erişim yetkisidir; genel bir tutamaç, SQL'in `data/` dışına çıkması için açık davetiye |
| **`contact_save` yeni kişiyi `BEKLEYEN` yazar** | §10.3. Aksi hâlde "rehbere ekle" cümlesi sessizce `KAYITLI_KISI` yetkisi veren bir cümle olurdu; kademe yükseltme §10.4'ün ayrı, geri alınamaz işi |
| **Kişi eşleştirmesi harf katlamasız** | Türkçe `I`/`ı` katlaması yanlış; yanlış eşleşen ad var olan bir kişinin kaydını değiştirir |
| **Ders dönemi argüman değil, bağlamdan** | Model hangi dönemde olunduğunu bilmez; sorulsaydı uydururdu. Dönemi bilen, §19.8'in program dosyasını yükleyen taraf |
| **Katalog payı sayaçtan ölçülür, eşikle karşılaştırılmaz** | Kural 10 sayıyı sayaçtan istiyor; §8.4 ise aşılınca ne yapılacağını söylüyor ama bir sayı vermiyor. Eşiği uydurmak, ölçümü kendi varsayımını doğrulayan bir teste çevirirdi |
| **Tool dalı ile düz metin dalı aynı öneki paylaşır (`<tool> `)** | C3 dallanmanın ilk token'da belli olmasını istiyor. Önek iki adayda da aynı: P7 çağrı *kodlamasını* karşılaştırsın, iki farklı öneki değil |
| **CLI'de hiçbir kelime `--` ile başlayamaz** | A4'ün "bir sonraki bilinen bayrağa kadar oku" kuralının gramer karşılığı: değerin sonraki bayrağı yutması gramer düzeyinde imkânsız |
| **JSON'da isteğe bağlı alanlar iki kural zinciri** | Tek zincirde, ilk alanı atlanan çağrı baştaki virgülle geçersiz JSON olurdu |
| **Gramer testleri yapıyı doğrular, geçerliliği değil** | Kendi yazdığım doğrulayıcı, gramerin geçerliliğini değil GBNF'i doğru anladığımı ölçerdi. Dış doğrulama P7'de, gerçek koşucuyla |
| **WOL yalnızca yapılandırmadaki adları kabul eder** | §19.9. Ham MAC kabul edilseydi modelin söyleyebildiği bir adres listenin dışındaki bir cihazı uyandırırdı; okunamayan hedef dosyası da `ConfigError`, boş liste değil (Kural 13) |

**P6'dan devreden:** §9.2'nin "ses profili kaydet/sil" satırı yazılmadı — kayıt ayrı bir
oturum durumu (`KAYIT`, §10.5) ve birden fazla ses örneği istiyor, konuşmacı adaptörü tur
akışına bağlanmadan (P8) gövdesi yazılamaz. P4/P5'ten devreden `DÜŞÜNÜYOR`'da söz kesme
satırı hâlâ açık; yeri yine §5'in tablosu.

---

## P7 — Faz 0 ölçümü

**Bağımlılık:** P6. **Engelleyen açık madde:** yok — "eldeki modeller" üzerinde koşar.

§18'in Faz 0'ı, ama tool kataloğu artık var olduğu için gerçekten çalıştırılabilir.

- 50 Türkçe senaryo, §18'deki dağılıma göre: tek tool, çok tool, eksik argüman, tool
  gerektirmeyen, benzer iki tool arasında ayrım, serbest metin argümanı.
- İki çağrı biçimi de GBNF ile kısıtlanmış halde ölçülür.
- Ölçülenler: tool seçim doğruluğu, argüman doğruluğu, üç ayrı halüsinasyon sayacı,
  üretilen token sayısı, çağrı başına süre, kendini düzeltme turu sayısı.
- Eldeki LLM adaylarının her biri için koşar.

Bu araç atılmaz; §17.1'in tool seçim değerlendirmesi olarak kalır ve her prompt / model
değişikliğinin geçmesi gereken kapı olur.

**Bitti kriteri:** sonuç raporu + gerekçeli karar, ve o karar §2'nin tablosuna işlenmiş.

### P7'de olan — 2026-08-09

**Karar: CLI-tarzı.** Rapor `docs/faz0-olcum.md`, araç `evals/`. Tool seçimi %94'e %92,
argüman doğruluğu berabere (%94), belirleyici bedel: CLI %22 daha az token, %13 daha hızlı.
İki biçimde de sıfır uydurulan tool/argüman — gramer görevini yapıyor, P6'nın "llama.cpp
bu grameri kabul ediyor mu" borcu da kapandı. Karar bir aday modele dayanıyor ve Faz 2'de
diğerleriyle yeniden ölçülecek; iki gramer üreticisi bu yüzden yerinde bırakıldı.

| Karar | Gerekçe |
|---|---|
| **`evals/` `src/mayen/` altında değil** | §4'ün on bir katmanı sayılı ve `test_layout` onları tek tek arıyor. Ölçüm aracı bir katman değil, `mayen`'i dışarıdan kullanan bir tüketici; ruff/mypy/pytest köklerine eklendi, aynı kapılardan geçiyor |
| **Çağrı yönergesi (`agent/calls.py:instructions`) katalogla aynı yerde değil** | Katalog hangi tool'ların *var* olduğunu, yönerge nasıl *çağrılacağını* yazıyor; ikincisi biçim kararına bağlı ve `tools` → `agent` importu §4'e aykırı. İlk koşuda bu metin hiç yoktu ve model kendi yerel biçimine düşüp prose dalına giriyordu — bulgu ölçümün kendisinden çıktı |
| **Yönergedeki örnekte gerçek tool adı yok** | Katalog hemen altında; buraya kopyalanan gerçek bir imza, imza değişince sessizce yalan söylerdi — `usage()`'ın ayrıca yazılmamasıyla aynı gerekçe. Şematik örneğin yettiği deneyle doğrulandı |
| **Ayrıştırıcı ham metin üretir, tiplemez** | Şemalar `tools`'ta. JSON'un sayısı/listesi CLI'nin yazdığı metne çevrilip ikisi de aynı `validate()`'ten geçiyor: ölçüm iki biçimi eşit koşulda karşılaştırsın diye |
| **`UnknownToolError` ve `UnknownArgumentError` ayrı istisnalar** | §17.1'in üç halüsinasyon sayacından ikisi bunlar; tek bir "ayrıştırma hatası" altında toplanınca sayaçlar ayrılamıyor |
| **Karşılaştırma birebir, tek istisna cümle sonu noktalaması** | Türkçe'de harf katlaması `I`/`ı` üzerinde yanlış çalışır, o yüzden yok. İlk koşuda argüman hatalarının yarısı "süt al." ile "süt al" farkıydı — kullanıcının cümlesini bitiren nokta argümanın içeriği değil |
| **Argüman doğruluğu, tool yanlışsa tanımsız** | Yanlış tool'un argümanını doğru ya da yanlış saymak, ikisi de anlamsız |
| **Üçüncü halüsinasyon sayacı `None`, sıfır değil** | Tool'un çalışıp sonucun modele geri beslenmesini, yani ajan döngüsünü gerektiriyor (P8). Sıfır yazmak ölçülmemişi ölçülmüş göstermekti (Kural 14) |
| **Düzeltme turu tavanı 2** | §19'da sayı yok; bu bir ölçüm parametresi, doküman kararı değil — o yüzden rapora yazılıyor |
| **`NOW` dondurulmuş** | Gerçek saatle koşmak altın kümeyi her gün başka bir sınav yapardı |

**P7'den devreden:** yerleşik defterde hiç `ArgType.LIST` argümanı yok — §8.3'ün
`--fields temperature,condition` örneği katalogda karşılıksız, yani liste kodlaması gerçek
modelde ölçülmedi. Ayrıca §8.3'e iki bulgu işlendi: eksik bilginin sorulmak yerine
uydurulması (biçimden bağımsız, Faz 3'ün düzeltme döngüsünün işi) ve CLI'nin tırnak açığı.

---

## P8 — Tur akışı ve ajan döngüsü (Faz 1'in bitişi) ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P4, P6, P7, P0/A1. **Engelleyen açık madde:** yok — gerçek modeller değil,
fake'ler kullanılıyor.

- `turn/`: segment → konuşmacı tanıma ∥ STT → ajan → cümle bölücü → TTS kuyruğu.
- `agent/`: `MAX_ADIM` sınırlı döngü. Sınıra ulaşılırsa **eldeki sonuçlarla yanıt üretilir,
  sessizce devam edilmez.** Tool zaman aşımı hata değil, modele geri beslenen sonuç.
- Sabit önek düzeni (§8.1). Değişken içerik yalnızca `bağlam bloğu`nda.
- Token sayısı LLM sunucusunun sayacından alınır, tahmin edilmez (Kural 10).
- Cümle bölücü + **sıralı** TTS kuyruğu: parça N+1, parça N gönderilmeden gönderilmez.
- Tur izi + **yeniden oynatma**: aynı girdi, fake adaptörlerle tekrar koşuyor (§15).

**Bitti kriteri — §18 Faz 1'in bitti kriteri:** fake adaptörlerle uçtan uca test yeşil,
GPU'suz, saniyeler içinde. Artı: kaydedilmiş bir iz yeniden oynatılıp aynı sonucu veriyor.
— **Karşılandı: 475 test yeşil, tamamı 1 saniyenin altında.**

### Verilen kararlar

| Karar | Gerekçe |
|---|---|
| **`turn` → `session` import'u reddedildi, bağımlılık ters çevrildi** | Koşucu `ActiveTurn`, `Segment` ve `Event`'e uzanıyordu; sınır testi P8'in ortasında devreye girdi ve haklıydı. `turn/report.py` neye ihtiyaç olduğunu `Protocol` olarak yazıyor, `session` uyguluyor — `TraceSink`/`SessionSink`/`AudioSink` kalıbının dördüncü tekrarı |
| **`TurnReport` olay enum'u değil, dokuz metot** | §5'in sözlüğünün sahibi `session/state.py`. `Event`'i `turn`'e kopyalamak, iki enum arasında elle bakımı yapılan bir çeviri katmanı demekti; onun yerine tur kendi diliyle konuşuyor, olaya çeviren tablonun sahibi (`session._Report`) |
| **`Protocol` alanları salt okunur `property`** | Yazılabilir `Protocol` alanı değişmez (invariant) sayılır: `segment: SegmentLike` yazmak `Segment` taşıyan gerçek tutamağı reddederdi |
| **Ajan döngüsü bir üreteç** | İlk ses gecikmesi §6'nın birinci sınıf hedefi. Token'ları toplayıp sonunda dönmek, ölçülen bütçeyi baştan harcamak olurdu |
| **Dal tamponu en fazla önek kadar** | §6/C3: gramer tool dalını sabit önekle başlatıyor, düz metin o karakterle başlayamıyor. Tampon tek token'da boşalıyor ve bunu bir test ölçüyor |
| **Adım başına tek çağrı** | §8.2 çoğul yazıyor ama gramerin kökü tek üretimde tek çağrı veriyor. "Her çağrı için" döngüsü, gramerin üretemediği bir girdiye yazılmış kod olurdu |
| **`MAX_ADIM` sınırında gramer tool dalını kapatıyor** | Modele "artık çağırma" demek yetmez: söz dinlemezse döngü ya sessizce devam eder ya hatayla biter. `PROSE_GRAMMAR` ile sınırdaki yanıt dilbilgisel olarak çağrı **olamaz** |
| **Red ve zaman aşımı `ToolResult` olarak geri besleniyor** | §8.2 ikisini de açıkça sonuç sayıyor; istisnaya çevirmek modelin kullanıcıya durumu anlatmasını engellerdi |
| **Bozuk çağrı onarılmıyor, yükseliyor** | §8.3'ün `--help` düzeltme döngüsü bu planda Faz 3'ün kalemi. Yutulmuyor (Kural 13) ve `ToolArgumentError` `usage()`'ı zaten taşıyor — düzeltme geldiğinde besleyeceği metin hazır |
| **Cümle bölücü ikiye ayrıldı: saf bölücü + zamanlı sarmalayıcı** | §6 üç ölçüt sayıyor ve üçüncüsü zaman. Zamanı saf bölücünün içine koymak, noktalama kurallarını ancak saat ilerleterek test edilebilir hâle getirirdi |
| **Noktalamanın ardından bir karakter bekleniyor** | "18.5 derece" cümlenin ortasıdır. Bir karakterlik gecikme, yanlış yerden bölünmüş bir cümleden ucuz |
| **Eşik dolduğunda bekleyen `anext` iptal edilmiyor** | Kaynağı yarıda kesmek, gelmekte olan parçayı düşürmek olurdu; §6 sıra bozulmasını kabul edilemez sayıyor. Görev bir sonraki tura devrediliyor |
| **TTS kuyruğunda paralellik yok** | Önden sentez ilk sesi hızlandırmaz (ilk cümle zaten sıradaki ilk iş) ama sırayı yalnızca zamanlamaya emanet ederdi |
| **`speak` ve `end` ayrı** | Onay cümlesi de aynı kuyruktan geçiyor; turun ortasında yazılan bir `AudioEnd` istemciye turun bittiğini söylerdi. `seq` ikisi boyunca artıyor (§13), `AudioEnd` tur başına bir kez |
| **Onay zaman aşımı turu bitiriyor, `False` dönmüyor** | §5'te `ONAY_ZAMAN_AŞIMI` → `IDLE`. `False` döngüyü `DÜŞÜNÜYOR`'a sokardı, oysa durum artık `IDLE` |
| **Onay okunurken söz kesme ayrı görevle yarıştırılıyor** | B3: ses durur, durum ve plan yaşar. `speech_stopped` her okumadan önce temizleniyor; kalan bir bayrak ikinci soruyu hiç okunmadan bitirirdi |
| **Boş yanıt hata** | Hiç ses çıkmazsa `İLK_SES_HAZIR` de olmaz ve §5 `DÜŞÜNÜYOR`'dan `SES_BİTTİ` tanımlamıyor. Tabloya olmayan bir geçiş uydurmak yerine `EmptyAnswerError` (Kural 13) |
| **Kimlik bir geri çağrımdan geliyor** | Gömü §6'nın istediği gibi STT ile paralel çıkarılıyor, ama gömü → kademe eşikleri §19.3'te **açık**. Karşılaştırmayı buraya yazmak açık bir maddeyi varsayımla kapatmak olurdu |
| **`TTS_İLK_PARÇA` ile `İLK_SES` ayrı ölçülüyor** | İlki TTS'ten çıkan ilk bayt, ikincisi istemciye kabul edilen ilk bayt. Backpressure varken (§13) aradaki fark tam da ölçülmek istenen şey |
| **Yeniden oynatmanın girdisi transkript, ses değil** | §15 bunu açıkça söylüyor: "ses kaydetmeden hata ayıklama bunu gerektirir". Kayıt üç şey taşıyor — segmentin metni, LLM'in ürettikleri, onay yanıtları |
| **Yeniden oynatmada süreler karşılaştırılmıyor** | Süre makineye bağlı; eşitlik ölçütü yapmak testi donanım hızına bağlamak olurdu. Karşılaştırılan şey aşamaların adı ve sırası |
| **Sayılar varsayılansız** (`max_steps`, `min_chars`, `max_wait_seconds`, `approval_timeout_seconds`) | Hiçbirinin dokümanda sayısı yok; §19.4 de açık. `ApprovalFlow.timeout_seconds` ile aynı gerekçe: ölçülmemiş bir sayıyı koda gömmek, sonra kimsenin nereden geldiğini bilemediği bir varsayım demek |

**P8'den devreden — Faz 2 ve sonrasına:**

- **Konuşma geçmişi ve özet tura bağlanmadı.** `build_messages` ikisini de alıyor ama koşucu
  boş geçiyor: `messages` tablosu P2'de var, bağlam bütçesi ve kırpma §11.1'in işi ve Faz
  6'ya ait. `Recording`'in nereye yazılacağı da bu yüzden açık — gövdelerin yeri o tablo.
- **Ses profili kaydı akışı (`KAYIT`, §10.5) yazılmadı.** `TurnReport` onu söyleyebiliyor
  (§5 tabloda tanımlı) ama gövdesi yok; birkaç ses örneği ve konuşmacı eşikleri gerekiyor
  (§19.3, Faz 4).
- **§5'te iki boşluk kodun kapatmadığı yerde duruyor:** `DÜŞÜNÜYOR` sırasında söz kesme
  (P4'ten devreden) ve `DÜŞÜNÜYOR` + `SES_BİTTİ` (boş yanıt). İkisi de doküman kararı; kod
  ikisinde de hata yükseltiyor, varsayım koymuyor.

---

## P9 — Faz 2: model ölçümü ⏳ SÜRÜYOR

**Bağımlılık:** P7 (ölçüm aracı), P8. **Engelleyen açık madde:** yok — ölçümün kendisi
§19.2/4/10/15'i kapatacak olan iş.

### Yapıldı — LLM adayları (2026-08-09)

Beş aday, aynı `llama-server` bayraklarıyla, `evals/`'in aynı 50 senaryosuyla koştu.
Rapor `docs/faz2-olcum.md`, model başına ham çıktı `docs/faz2/`.

| Bulgu | Ayrıntı |
|---|---|
| **§19.1'in kazananı modele göre değişiyor** | Büyük modellerde (35B-A3B, 27B) CLI, küçüklerde (9B ×2) JSON önde; 9B-Q4'te fark %60'a %84. P7'nin "karar modele bağlı" uyarısı ve iki gramer üreticisini saklama kararı doğrulandı. **Nihai karar model üçlüsü seçilene kadar verilmiyor** |
| **Uydurma yok** | On koşunun hiçbirinde uydurulmuş tool ya da argüman yok; düzeltme turu yalnızca üç koşuda birer kez |
| **VRAM ölçüldü** | 27B tek başına 15628 MiB — STT/TTS'e yer bırakmıyor. 35B-A3B ancak `--n-cpu-moe 7` ile sığıyor. gemma-12B 7194 MiB'de en yüksek tool doğruluğunu (%96) veriyor. Seçim değil gözlem: üçlü ölçülmeden karar yok |
| **CLI gramerinde açık** ✅ **kapandı (P11)** | `cli-word` `<` kabul ettiği ve CLI satırının sonlandırıcısı olmadığı için model ikinci bir çağrıya kalkıştığında önek birincinin argümanının **içine** yazılıyor ve geçerli ama yanlış tek bir çağrı çıkıyor. JSON'da mümkün değil. `--` yasağının eşi olarak `<` yasaklandı — bkz. P11 |
| **`LlamaCppLLM`'de aralıklı `httpx.ReadError`** ✅ **kapandı (P12)** | Bir koşu `/tokenize`'da koptu, tekrarı geçti, sonraki dokuz koşuda görülmedi; repro tutturulamadı. Ölçümde yeniden koşu, gerçek turda turu öldüren hata. Kaydedildi, düzeltilmedi |

### Kalan

- STT adayları (faster-whisper large-v3 / turbo / small): VRAM ve Türkçe doğruluk.
- TTS (Kokoro-82M): VRAM, §19.10'un ses karakteri.
- Üçlünün birlikte 16 GB'a sığdığının ölçümü → model seçimi → §19.1'in nihai kararı.
- §19.4 gecikme temel çizgisi ve regresyon testi eşiği.
- C1/§19.15.

**Bitti kriteri (§18, Faz 2):** seçilmiş model üçlüsü ve ölçülmüş gecikme temel çizgisi.

---

## P10 — §8.3 düzeltme döngüsü ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P8. **Engelleyen açık madde:** yok — tavan bir ölçüm parametresi, doküman
kararı değil.

`agent/loop.py` bozuk çağrıda artık yükselmiyor: `CallParseError` ve `ToolArgumentError`
tur bağlamına geri besleniyor (ikincisinde `usage()` ile birlikte) ve aynı adım yeniden
üretiliyor. `evals/runner.py`'nin P7'de yazdığı semantiğin aynısı, üç farkla:

| Karar | Gerekçe |
|---|---|
| **Düzeltme turu adım harcamıyor** | `MAX_ADIM` §8.2'nin *tool* sayısı; modelin kendi hatasını düzeltmesini ondan düşmek, iki farklı bütçeyi tek sayaca bindirmek olurdu |
| **Tavana ulaşınca tur ölmüyor, düz metinle kapanıyor** | Yükseltmek gerçek bir turu öldürür — düzeltilmek istenen şey buydu. Sessizce sürdürmek Kural 13'e aykırı; ikisi de değil: `log.warning` + modele sistem notu + `MAX_ADIM` dalındaki kapanışın aynısı, yani kullanıcı bir yanıt duyuyor |
| **`max_corrections` varsayılansız** | `max_steps` ve `ApprovalFlow.timeout_seconds` ile aynı gerekçe: §19'da sayı yok |

Doğrulama (`Tool.validate`) `_invoke`'tan `_resolve`'a taşındı — ayrıştırma ve doğrulama
aynı düzeltme döngüsünün içinde. §8.5'in sırası bozulmadı: doğrulama hâlâ politikadan önce.

**Bitti kriteri:** bilinmeyen tool, bilinmeyen argüman ve geçersiz argüman tipi ikinci
denemede düzeliyor; tavan aşıldığında tur bir cümleyle bitiyor; dört kapı yeşil. ✅

---

## P11 — CLI gramerinde `<` yasağı ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P9'un bulgusu. **Engelleyen açık madde:** yok.

`cli-word`, `cli-item` ve `cli-text` artık `<` kabul etmiyor. `--` yasağının eşi: ikisi de
"bir değer kendinden sonrakini yutmasın" diyor. Bedeli, argüman metninde `<` geçememesi —
§9.2'nin alanlarında karşılığı olmayan bir karakter ve sessiz yanlış çağrıdan ucuz.

**Ölçüm sonuçlarına etkisi:** `docs/faz2-olcum.md` ve `docs/faz2/` **eski gramerle**
alındı. Sayılar geçersiz olmadı — bulgu ölçümde bir kez görüldü ve o koşu zaten yanlış
sayıldı — ama model üçlüsü seçilirken CLI adayı yeniden koşulursa bu gramerle koşulacak.

**Bitti kriteri:** üç kuralın hiçbiri `<` üretemiyor, önek yalnızca `tool-call` dalında
geçebiliyor; dört kapı yeşil. ✅

---

## P12 — Akışsız uçlarda taşıma yeniden denemesi ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P9'un ikinci bulgusu. **Engelleyen açık madde:** yok.

`LlamaCppLLM._post` taşıma koptuğunda isteği bir kez daha deniyor (`_POST_ATTEMPTS = 2`).

| Karar | Gerekçe |
|---|---|
| **Yalnızca `httpx.TransportError`** | Durum kodu dönen bir sunucu çalışıyordur; aynı isteği tekrarlamak §14'ün "servis hata döndürdü" dalını gizlemek olurdu |
| **Akış yeniden denenmiyor** | Yarısı tüketilmiş bir üretimin tekrarı, aynı token'ları ikinci kez akıtmak demek |
| **Bekleme yok** | Gözlenen kopma anlıktı; bir bekleme süresi ölçülmemiş bir sayı olurdu |
| **Deneme tükenince yükseliyor** | Kural 13; hata yutulmuyor, mesaja deneme sayısı yazılıyor |

**Bitti kriteri:** ilk denemede kopan `/tokenize` ikincide sonuç veriyor, sürekli kopan
hata yükseltiyor, 500 tekrarlanmıyor; dört kapı yeşil. ✅

---

## P13 — §17.1'in üçüncü halüsinasyon sayacı ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P8 (ajan döngüsü). **Engelleyen açık madde:** yok.

P7 ve P9 raporlarında `None` duran sayaç artık ölçülüyor — ama **dar tanımıyla**:
*desteksiz sayı*. Doğru çağrıyı üreten ve `Scenario.result` taşıyan senaryolarda hazır tool
sonucu geri besleniyor, yanıt tool dalı kapalı gramerle üretiliyor, yanıttaki her sayı iki
kaynağa karşı aranıyor (tool sonucu + kullanıcı turu); ikisinde de olmayan sayı sayılıyor.

| Karar | Gerekçe |
|---|---|
| **Yalnızca sayısal iddia** | Serbest cümlenin "sonuçta var mıydı" sorusunu mekanik cevaplayan tek şey sayı; gerisi bir hakem modeli ister ve hakemin kendi halüsinasyonu ölçüme karışır. Rapor sayacı dar adıyla ve **paydasıyla** yazıyor (Kural 14) |
| **Hazır sonuç, gerçek tool gövdesi değil** | Ağ ve veritabanı ölçümü belirlenimci olmaktan çıkarırdı; ölçülen şey tool'un doğruluğu değil |
| **Yanıt turu `PROSE_GRAMMAR` ile** | Yanıt turunda ikinci bir çağrı ölçülen şey değil; `agent/loop.py`'nin sınırdaki kapanışıyla aynı gerekçe |
| **Ondalık ayracı normalize** | `9,4` ile `9.4` aynı sayı; ayracı iddia saymak modelin doğrusunu yanlış raporlardı |

Beş senaryoya hazır sonuç yazıldı (`tek-01`, `tek-02`, `tek-03`, `tek-05`, `tek-10`).
Sonucu olmayan senaryolar paydaya girmiyor.

**Bitti kriteri:** sonuçta olmayan sayı sayılıyor, olan sayılmıyor, sonucu olmayan senaryo
paydaya girmiyor, rapor kapsamı yazıyor; dört kapı yeşil. ✅ **Ölçüm koşulmadı** — sayılar
model üçlüsü seçilirken alınacak.

---

## P14 — `ArgType.LIST` argümanı ve liste kodlamasının ölçülmesi ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P6. **Engelleyen açık madde:** yok.

Defterde hiç `ArgType.LIST` argümanı yoktu; §8.3'ün kendi CLI örneği
(`weather --city Denizli --fields temperature,condition`) hem gramerde hem ayrıştırıcıda
karşılığı olduğu hâlde gerçek modelde hiç ölçülmemişti. `weather` tool'una isteğe bağlı
`fields` argümanı eklendi.

| Karar | Gerekçe |
|---|---|
| **Doküman örneğinin tool'u seçildi** | §8.3 liste kodlamasını `weather --fields` üzerinden anlatıyor; başka bir tool uydurmak, doküman ile kodun aynı örnekte ayrışması olurdu |
| **Alan isteğe bağlı** | Yokluğu boş filtre değil, filtre yok demek: iki alan da döner |
| **Tanınmayan alan hata sonucu** | Sessizce atmak, modelin istediğini aldığını sanmasıyla biterdi (Kural 13) |
| **Geçerli alanlar katalogda tek tek yazılı** | Model neyi isteyebileceğini tahmin etmek zorunda kalmasın |

`spec.py`'ye `strings()`/`optional_strings()` okuyucuları eklendi — `text`/`number`'ın
liste karşılığı.

**Altın küme değişti, sayısı değişmedi:** `tek-04` düz bir hava sorusuydu ve `tek-03`'ün
eşiydi; yerine yalnızca tek bir alan isteyen bir cümle yazıldı, yani doğru çağrı tek
anlamlı. Küme hâlâ 50 senaryo (§18) ve eksen dağılımı aynı. Karşılığı: `docs/faz2-olcum.md`
o senaryoda eski metinle ölçüldü. Bir senaryo ince bir kanıt; üçlü ölçülürken liste
kodlaması zayıf çıkarsa senaryo eklenir.

**Bitti kriteri:** `--fields` seçtiğini döndürüyor, yokluğu her şeyi döndürüyor,
tanınmayan alan hata; altın kümede en az bir liste senaryosu var ve bunu bir test
koruyor; dört kapı yeşil. ✅ **Ölçüm koşulmadı** — model üçlüsüyle birlikte.

---

## P15 — WebSocket sunucusu ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P3 (sözleşme), P4 (oturum), P8 (tur). **Engelleyen açık madde:** yok —
§19.5 (ses formatı) çerçevede zaten alan olarak duruyor, sunucu kodek seçmiyor.

Faz 5'in ilk parçası. P3 bilerek sözleşmede durmuştu ("konuşacak istemci Faz 5'te
geliyor"); artık konuşan taraf var. `transport/server.py` üç parça: `Connection` (tek
soket, tek yazıcı görev), `Connections` (bağlantı defteri), `FrameSink`. Bağımlılık:
`websockets`.

| Karar | Gerekçe |
|---|---|
| **Tek `FrameSink` hem `SessionSink` hem `TurnSink`** | İkisi de "dışarıya duyur" demek ve duyurulan yer aynı soket; ikiye bölmek aynı bağlantı defterini iki yerde tutmak olurdu |
| **Sink oturumu ikinci fazda alıyor (`attach`)** | Gerçek bir döngü: `Session` kurulurken sink'i, sink de turun sahibini bulmak için oturumu istiyor. Bir `Protocol` bunu kıramaz — iki taraf da somut örneği istiyor. İkinci faz wart'ı görünür bırakıyor; kurucu sarmalayıcı yalnızca gizlerdi |
| **Durum yayın, ses turun cihazına** | Aynı anda tek tur var (§5), yani durum ikinci cihaz için de doğru bilgi. Ses/transkript/tool bildirimi ise o turun; cihazı `session.active_turn` söylüyor. Ayrı bir `turn_id → cihaz` defteri tutmak, oturumun zaten tuttuğu şeyin ikinci kopyası olurdu |
| **Eşleşmeyen `turn_id` düşer, kayda geçer** | §13 ölü turun geç kalmış çerçevesini açıkça bekliyor; hata değil ama sessiz de değil |
| **Yön doğrulanır** | Tel üzerinde `Welcome` çözülebiliyor; doğrulanmasa istemci sunucunun sözlüğünü karşısına koyabilirdi (Kural 13) |
| **Bozuk çerçeve bağlantıyı düşürmüyor** | Bir çerçevenin bozuk olması sonrakinin de bozuk olacağı anlamına gelmiyor; hata ayrı kanaldan gidiyor (§14). Turun ortasında soketi kapatmak, hatayı bildirmekten pahalı |
| **İşlenemeyen çerçeve de `ErrorFrame`** | §5'in tablosunda tanımsız bir geçiş (`DÜŞÜNÜYOR`'da söz kesme, P4'ten devreden açık) artık bağlantıyı öldürmüyor: yükselen istisna kayda ve çerçeveye çevriliyor. Açık madde kapanmadı — yalnızca patlaması görünür oldu |
| **Segment gönderilip beklenmiyor** | Beklemek okuma döngüsünü tur boyunca durdururdu; söz kesme de o döngüden geliyor, yani turu iptal edecek çerçeve turun bitmesini beklerdi (Kural 12) |
| **İptalde önce kuyruk boşalır, sonra `Cancelled`** | Ters sırada istemci iptali duyduktan sonra ölü turun parçalarını almaya devam ederdi |
| **Aynı cihazın ikinci bağlantısı eskisini değiştirir** | Reddetmek, kopan bir bağlantının soketi henüz toplanmadığı için yeniden bağlanmayı imkânsız kılardı |
| **El sıkışma cevabı kuyruğu atlıyor** | Yazıcı görev henüz yok ve `Rejected`'ın ardından bağlantı kapanıyor |

**Testler gerçek soket üzerinden** (`serve` ile gevşek bir bağlantı noktası, `websockets`
istemcisi). Sahte soket tam da bu paketin işini — el sıkışma, kodlama, sıralı yazma —
atlardı. GPU yok, model yok; tur sahte bir koşucuyla yürüyor çünkü ölçülen şey
yönlendirme.

**Bu pakette olmayanlar:** istemci (mikrofon, endpointing, ses çalma, AEC), tur hatasının
istemciye bildirilmesi (aktör onu kayda düşürüyor, dışarı çıkaracak bir kanca yok) ve
süreç giriş noktası — sunucuyu kuran `main` hâlâ yok, kurulum testlerde elle yapılıyor.

**Bitti kriteri:** el sıkışma sürüm uyuşmazlığını ve el sıkışma olmayan ilk çerçeveyi
reddediyor; metin ve ses segmenti tur açıyor; transkript/ses/tool bildirimi yalnızca
konuşan cihaza, durum herkese gidiyor; söz kesme `Cancelled` üretiyor; bozuk çerçeve ve
tanımsız geçiş bağlantıyı öldürmüyor; dört kapı yeşil. ✅

---

## P16 — Süreç giriş noktası ve ders programı yükleyicisi ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P15 (sunucu), P8 (tur), P2 (veri). **Engelleyen açık madde:** yok.

P15'ten devreden iki eksikten biri: sunucuyu, oturumu ve gerçek koşucuyu birleştiren bir
`main` yoktu — montaj yalnızca testlerde elle yapılıyordu. Artık
`uv run --env-file .env python -m mayen` sistemi ayağa kaldırıyor. Yanında §19.8'in
yükleyicisi geldi: ders programı depodaki TOML'dan açılışta DB'ye yazılıyor.

| Karar | Gerekçe |
|---|---|
| **`main.py` bir katman değil, montaj** | Her şeyi import eden tek modül; sınır testinde rütbesi `transport`'un da üstünde (`-1`). Rütbesiz bırakılsaydı denetim dışı kalırdı: bir katman ondan import etse test görmezdi |
| **Sayılar `main`'de sabit, sınıflarda varsayılansız** | `max_steps`, `min_chars`, `max_wait_seconds`, `approval_timeout_seconds` bilerek varsayılansızdı — §19'da sayı yok ve sınıfa gömülen sayı ölçülmüş bir karar gibi görünür. Süreç bir sayı vermek zorunda; hepsi tek ekranda, gerekçeleriyle ve §19.4 ölçülünce değişecekleri yazılı |
| **Yapılandırmaya yalnızca üç alan eklendi** (`courses_path`, `host`, `port`) | Bunlar kurulumdan kuruluma değişir; bölücünün eşiği değişmez, ölçülür. Ayarı çoğaltmak, ölçülmemiş sayıları ortam değişkeni kılığında kalıcılaştırmak olurdu |
| **LLM gerçek, STT/TTS/konuşmacı sahte** | Model üçlüsü seçilmedi (§19.2) ve sahibi STT'yi bir süre daha sahte tutuyor. Sahte STT metin segmentini transkript sayıyor: sistem bugün metinle uçtan uca konuşuyor. Gerçek uçlar geldiğinde değişecek yer bu dosyadaki üç satır |
| **Kimlik `TANINMAYAN` dönüyor** | §19.3'ün eşikleri açık. Eşiksiz eşleştirme uydurmak yerine matrisin en dar satırı kullanılıyor; açılışta uyarıya yazılıyor (Kural 13). Sessizce `SAHİP` dönmek Kural 6 ihlaliydi |
| **`build()` bir async bağlam yöneticisi ve `llm` dışarıdan verilebiliyor** | Açtığını kapatan tek yer olsun diye; `llm` kancası da §4'ün şartı — montajın kendisi GPU'suz ölçülebilmeli. Testin montajı atlaması, tam da bu paketin yazdığı şeyi ölçülmemiş bırakırdı |
| **Kapanış SIGINT/SIGTERM olayıyla** | `KeyboardInterrupt` turun ortasında rastgele bir noktada yükselirdi; olay beklemek kapanışı tek yere toplar |
| **Dönemi ders dosyası söylüyor, ayrı bir değişken değil** | İki yerde tutulsa biri unutulur ve sistem "bugün dersin yok" der — sessiz ve inandırıcı bir yanlış. `tools/spec.py`'nin `course_term` notu da yükleyiciyi işaret ediyordu |
| **Boş/eksik program dosyası hata, boş program değil** | Yolu yanlış yazılmış bir dosyayı "ders yok" diye okumak Kural 13 ihlali. Dosya hiç verilmezse dönem boş kalıyor ve bu uyarıya yazılıyor — uydurulmuyor |

**Bitti kriteri:** `python -m mayen` soketi açıyor, bağlanan istemcinin metin segmenti
montaj elle bağlanmadan transkript → ses → bitiş üretiyor; program dosyası açılışta
yükleniyor ve bozuk dosya `ConfigError` veriyor; SIGTERM temiz kapatıyor; dört kapı
yeşil. ✅

**P16'dan devreden:** Faz 5'in kalan tek kalemi istemci (mikrofon, endpointing, ses çalma,
AEC). Ayrıca tur hatasının istemciye bildirilmesi hâlâ yok (P15'ten devir) ve yedekleme
işi süreçte zamanlanmıyor — o `scheduler/` ile birlikte Faz 6'da.

---

## P17 — Metin tabanlı başsız istemci ✅ TAMAMLANDI (2026-08-09)

**Bağımlılık:** P15 (sunucu), P16 (giriş noktası). **Engelleyen açık madde:** §19.6 (wake
word) yalnızca aktivasyonu engelliyor; protokol tarafı engelli değil.

Faz 5'in istemcisi iki adımda yazılıyor: **önce protokol, sonra donanım.** Bu paket
birincisi. `client/` depo kökünde, `evals/` gibi — istemci bir katman değil, `mayen`'i
import eden ikinci bir süreç. Üç parça: `core.py` (el sıkışma, tur takibi, söz kesme),
`output.py` (`Output` protokolü + metin uygulaması), `__main__.py` (uçbirim).

| Karar | Gerekçe |
|---|---|
| **Önce metin, sonra ses** | Sahte STT istemcinin metnini transkript sayıyor (P1), sahte TTS cevabı UTF-8 baytı olarak seslendiriyor. Yani §13'ün **en zor kısmı** — `turn_id`/`seq` kuralı, söz kesme, iptal — bugün mikrofonsuz koşuyor ve ölçülebiliyor. Donanımla başlamak, protokolü PortAudio'nun arkasında test edilemez hâlde bırakırdı |
| **`Output` tek arayüz** | "Sesi giydirmek" = ikinci bir uygulama. Tur takibi, ölü tur filtresi ve söz kesme yolu aynı kalıyor; değişen yalnızca parçanın nereye gittiği |
| **Aktif tur filtresi istemcide de var** | §13 filtreyi iki tarafa birden yazıyor: sunucu düşürse bile ağda ve tamponda yolu yarılamış parça kalır. `seq` tek başına ölü turun kırıntısını yeni cevabın ilk parçasından ayıramaz |
| **Turu `Transcript` açıyor** | Segment gönderilirken `turn_id` henüz yok — endpointing istemcide (§7), kimliği sunucu üretiyor |
| **Sıra atlaması bildiriliyor, parça atılmıyor** | Eksik `seq` kaybolmuş ses; parçayı da atmak kaybı ikiye katlardı. Susmak Kural 13'e aykırı |
| **Yön doğrulaması istemcide de** | Sunucudaki kontrolün aynası: istemciden çıkması gereken bir çerçeve tel üzerinden geri gelirse protokol hatası |
| **Çözme artımlı** | Parça sınırı karakter sınırı değil. İlk elle denemede `ş`'nin ortasından kesilen parça "8 bayt" diye raporlandı; artımlı çözücü yarım baytı sonraki parçaya taşıyor. Tur sonunda hâlâ yarım bayt varsa yük gerçekten metin değildir ve boyutu yazılıyor |
| **Girdi ayrı iş parçacığından** | `input()` olay döngüsünü bloklasaydı, asistan konuşurken yazılan `/iptal` ancak tur bittikten sonra gönderilirdi — tam da işe yaramayacağı anda |
| **Canlılık yoklamasının zamanlayıcısı yok** | `ping()` var; aralık ölçülmemiş bir sayı ve §19'da yok |

**Yol boyunca bulunan gerçek hata — `turn_id` sayaçtı.** `Session._next_turn_id` süreç
başına `t1, t2…` üretiyordu; `turn_traces.turn_id` ise UNIQUE ve dosya süreçten uzun
yaşıyor. Sunucu ikinci kez başlatıldığında ilk tur `IntegrityError` ile düşüyordu. Testler
hep taze veritabanıyla koştuğu için görünmemişti; **elle koşulan ilk gerçek tur ortaya
çıkardı.** `obs/trace.py:new_turn_id()` zaten "sayaç değil, uuid — çakışmaması bir kolaylık
değil, doğruluk şartı" diye yazılmıştı ve `session` onu kullanmıyordu; artık kullanıyor.
Sabit kimlik bekleyen testler koşan turun kimliğini soruyor.

**Bitti kriteri:** el sıkışma, metin segmenti, transkript, akan cevap, tool bildirimi,
durum değişiklikleri ve `/iptal` uçtan uca çalışıyor; ölü turun parçası çalınmıyor; testler
sunucu tarafında `main.build`'in kurduğu gerçek sistemi kullanıyor; dört kapı yeşil. Gerçek
`llama-server` ile elle de koşuldu: `selam` ve `saat kaç` (tool dâhil) doğru cevaplandı. ✅

**P17'den devreden:** mikrofon/hoparlör arka ucu, endpointing, wake word (§19.6 açık) ve
AEC. Bunların hepsi bir sonraki pakette ve hiçbiri bu paketin protokol tarafını
değiştirmiyor.

---

## P18 — İstemcinin ses yarısı: mikrofon, endpointing, hoparlör ✅ TAMAMLANDI (2026-08-10)

**Bağımlılık:** P17 (protokol tarafı). **Engelleyen açık madde:** §19.6 (wake word) —
yazılmadı, varsayılmadı. §19.2 (STT modeli) ses **girişini** uçtan uca engelliyor; aşağıda.

P17'nin sözü buydu: protokol tarafı hiç değişmeden ikinci bir `Output` yazılıyor. Dört
yeni dosya — `client/audio.py` (biçim, `rms`, `AudioSource`/`AudioPlayer` protokolleri ve
sahteleri), `client/portaudio.py` (`sounddevice` uygulaması), `client/endpointing.py` (saf
VAD), `client/voice.py` (`VoiceOutput` + dinleme döngüsü) — ve `client/core.py`'de tek
satır değişiklik yok.

| Karar | Gerekçe |
|---|---|
| **Endpointing enerji tabanlı, model değil** | Yerel bir VAD modeli Kural 2'nin sınırında dolaşırdı ve karşılaştırılacak bir şey de vermezdi: önce çalışan bir zincir gerekiyor. Eşik ve sayılar **işletim değeri**, ölçülmüş karar değil — §19'da bu sayılar yok, o yüzden modül sabiti ve `--esik` bayrağı |
| **Ön tampon `pre_roll + start_frames`** | Yalnızca ön tampon kadar tutulsaydı, başlangıcı kanıtlayan gürültülü çerçeveler sessizlerin yerine geçer ve ilk hece yine kaybolurdu — transkript "elam" diye başlardı. İlk yazımda tam bu hata vardı; test yakaladı |
| **Segmentin tavanı var** | Sessizliğin gelmediği ortam (fan, sokak) segmenti sonsuza büyütürdü. Tavan dolunca olduğu yerde kapanır: kaybolmaz, geç kalmaz |
| **Yarım dubleks, bilerek ve geçici** | AEC yok; asistan konuşurken mikrofon kendi sesini duyar ve her cevabı kendi kendine keserdi. §18 bu ödünü adıyla koyuyor: yarım dubleks söz kesmeyi **öldürür**. `--soz-kesme` ödünü tersine çevirmek isteyene açık ve ne olacağı yardımda yazılı. Bu bir karar değil, AEC gelene kadarki ara durum |
| **Söz kesme konuşmanın başında** | Segmentin sonunu beklemek, kullanıcı sustuktan yarım saniye sonra kesmek olurdu — asistan o sırada hâlâ konuşuyor |
| **`Cancelled` tamponu atıyor** | PortAudio'nun `stop()`'u tampondakini çalıp bitiriyor, `abort()` atıyor. İptalin duyulur olması tam olarak çalmamaktır (§13) |
| **Mikrofon kuyruğu sınırlı, en eskiyi düşürür ve sayar** | Geri çağrım ayrı iş parçacığında ve bloklamak ses kartını bekletmek demek (tıklama, altakış). Gecikmiş ses kaybolan sesten kötü; düşen çerçeve sayılıyor (Kural 13) |
| **`sounddevice` isteğe bağlı bir ekstra** | Metin kipi ses kartı olmayan makinede de koşmalı, testler sahtelerle çalışıyor. Import fonksiyonun içinde; eksikse `MissingBackendError` kurulum talimatı veriyor ve **bağlanmadan önce** yoklanıyor — mikrofon görevinin içinde patlasaydı kullanıcı yalnızca sessizlik görürdü |
| **Wake word yazılmadı** | §19.6 açık: motor da kelime de seçilmedi. Mikrofon bağlantı boyunca dinliyor ve bu belgede yazılı — varsayılan bir kelime uydurmak açık maddeyi kapatmak olurdu |

**Yol boyunca kapanan P15 açığı — tur hatası istemciye ulaşmıyordu.** Aktör hatayı kayda
düşüyordu ama dışarı taşıyan bir uç yoktu: konuşan taraf sessizlikle hatayı ayırt edemez ve
**sesin hiç gelmemesi de bir cevaptır, yanlış olanı** (§14, Kural 13). `SessionSink` üçüncü
bir yöntem kazandı (`turn_failed`), `FrameSink` onu §14'ün ayrı kanalından — yayına değil,
turun cihazına — `ErrorFrame(code="turn_failed")` olarak yolluyor. Sıra bilinçli: **önce
sebep, sonra durum**; istemci `IDLE`'ı hatadan önce görseydi turun sessizce bittiğini
sanırdı.

**Ses girişi uçtan uca çalışmıyor ve sebebi açıkta duruyor.** `FakeSTT` yükü UTF-8 metin
sayıyor (P1'in ertelenmiş kararı); gerçek PCM orada `UnicodeDecodeError` veriyordu. Artık
adı konmuş bir hata veriyor: "sahte STT gerçek sesi çözemez (§19.2: STT modeli
seçilmedi)". Yani ses **çıkışı** bugün çalışıyor, ses **girişi** §19.2'ye bağlı — sahibin
STT'yi bir süre daha sahte tutma kararı bu paketi engellemedi, yalnızca sınırını çizdi.

**Bitti kriteri:** endpointing, yarım dubleks, söz kesme ve iptal sahte mikrofon/hoparlörle
uçtan uca test ediliyor; `python -m client --ses` gerçek PortAudio ile açılıyor ve cevabı
çalıyor; patlayan tur istemciye `ErrorFrame` olarak ulaşıyor; dört kapı yeşil. ✅

**P18'den devreden:** AEC (bu fazın en büyük kalemi) ve wake word (§19.6). İkisi de
yazılmadı, ikisi de varsayımla kapatılmadı.

---

## P19 — Zamanlayıcı ve proaktif ses kanalı ✅ TAMAMLANDI (2026-08-10)

**Bağımlılık:** P15 (sunucu), P16 (montaj), P17 (istemcinin tur takibi). **Engelleyen açık
madde:** yok. §19.13 (kaçırılmış görev toleransı) haritada zaten "hiçbir şeyi engellemiyor —
yapılandırma değeri" diye işaretliydi; sayı `Config`'e girdi, davranışı §12 tanımlıyor.

`scheduler/` P1'den beri boştu: `scheduled_tasks` tablosu, `TaskRepository` ve üç tool
(`task_create`, `task_list`, `task_cancel`) vardı ama **kuran ile çalan arasında kimse
yoktu** — kullanıcı hatırlatıcı kurabiliyor, hatırlatıcı hiç çalmıyordu. Aynı boşluk
yedeklemede de vardı: `data/backup.py` P2'den beri hazır, tetikleyeni yok. "Yedeği var"
sanılan kurulum, yedeği olmayan kurulumdur.

Üç dosya: `scheduler/loop.py` (tik, açılış taraması, yinelenen bakım işleri),
`scheduler/announce.py` (§12'nin proaktif kanalı) ve `scheduler/reminders.py` (`reminder`
türünün işleyicisi).

| Karar | Gerekçe |
|---|---|
| **Proaktif ses bir tur *değil*** | §5'in tablosunda karşılığı yok. Ona durum yürütmek, tabloda olmayan bir geçişi kodun uydurması olurdu. Turdan aldığı tek şey **sıra**: `Session.exclusive()` global tur kilidini tutuyor, yani §12'nin "araya girmez, sıraya girer" kuralı kilidin kendisiyle sağlanıyor |
| **Yeni bir çerçeve: `Announcement`** | §13'ün filtresi gereği istemci bilmediği turun parçasını atar — ve proaktif turu kullanıcı açmıyor. Ses başlamadan turu duyuran bir çerçeve olmadan hatırlatıcı *sessizce* düşerdi. `Transcript` kullanılamazdı (o kullanıcının konuşmasını bağlar), `StateChanged` de kullanılamazdı (bkz. üstteki satır). §13'ün çerçeve listesine bir satır eklendi |
| **Metin çerçevede de taşınıyor** | TTS çökerse ses yok ama hatırlatıcının içeriği kaybolmamalı (§14'ün ikinci, bağımsız kanalı) |
| **Kendi `turn_id`'si söz kesmeden koruyor** | İptalin kapsamı tek tur (§5, §12): kullanıcının asistanı kesmesi, kuyrukta bekleyen hatırlatıcıyı sessizce çöpe atmıyor. Yeni kod gerekmedi — `interrupt` zaten yalnızca `active_turn` ile eşleşeni iptal ediyor; test bunu kilitliyor |
| **Hedef: en son etkileşimli *bağlı* cihaz** | Sıra oturumdan (`recent_devices`, §5 varlık takibi), bağlılık `transport`'un defterinden geliyor; `session` defteri göremez (§4), o yüzden seçim `Announcer`'da ve sink `connected()` diyor |
| **Cihaz yoksa kuyruklanır, düşürülmez** | §12'nin kendi kuralı. Hatırlatıcı, duyulmadığında hiçbir işe yaramayan tek çıktı türü. İlk bağlanan cihaza sırasıyla veriliyor: iki hatırlatıcı ters sırada duyulursa hangisinin ne zamana ait olduğu kaybolur |
| **Bağlanma kancası senkron, seslendirme ayrı görevde** | Kanca el sıkışmayı yeni bitirmiş okuma döngüsünden çağrılıyor; orada beklemek, bildirim bitene kadar o bağlantıdan gelen hiçbir çerçevenin —söz kesme dâhil— okunmaması demekti (Kural 12) |
| **Aynı TTS kuyruğu, cümle bölücüsüz** | §12 kuyruğun ortak olmasını istiyor ve `SpeechQueue` olduğu gibi çağrılıyor. Bölücünün işi akan token'ı erkenden sese çevirmek (§6); burada metnin tamamı zaten elde, bölücüyü çağırmak olmayan bir akışı taklit etmek olurdu |
| **Tolerans yalnızca açılışta** | §12 kaçırılmış görevi *uygulama kapalıyken* tanımlıyor. Her tik'te uygulansaydı, uzun bir işin arkasında bekleyen görev toleransı aşıp düşerdi. Süreç ayaktayken bir görev en fazla bir tik (15 sn) geç kalır |
| **Patlayan ve tanınmayan görev kapatılıyor** | `BEKLIYOR` bırakmak, aynı hatayı her tik'te tekrarlayan ve kaydı dolduran bir döngü demekti. Sebep `outcome` sütununa yazılıyor — `DUSURULDU` bir durum, sessiz bir silme değil (Kural 13) |
| **Okunamayan damga = sonsuz gecikme** | `due()` yalnızca dizi karşılaştırması yapıyor, yani elle düzenlenmiş bozuk bir damga pekâlâ "vakti gelmiş" görünebilir. Onu zamanında saymak, dünkü hatırlatıcıyı bugün çalmak olurdu |
| **Yinelenen iş ilk aralıktan sonra koşuyor** | Açılışta koşsaydı her yeniden başlatma bir yedek alır ve `keep` penceresini birkaç dakikaya sıkıştırırdı. Saati `monotonic`: duvar saatinin geri alınması bir sonraki yedeği saatlerce erteleyebilirdi |
| **Yedek ayrı bir görev satırı değil** | Bakım işini `scheduled_tasks`'a yazmak, kullanıcının `task_list` ile gördüğü kuyruğu sistemin kendi işleriyle doldurmak olurdu |
| **Tik aralığı montajda, tolerans yapılandırmada** | Aralık bir işletim değeri (§12 sayı vermiyor) ve `main.py`'deki diğerlerinin yanında duruyor; tolerans kurulum başına değişir ve §19.13 onu zaten yapılandırmaya bırakmış |

**Yol boyunca kapanan küçük bir çatlak:** zaman damgasının biçimi iki yerde yazılıydı —
`data/clock.py` ve `tools/task_create.py`. `clock.py`'nin kendi başlığı "tek yerde, çünkü
iki farklı biçim yazan iki modül sıralamayı bozar" diyordu; zamanlayıcı "vakti ne kadar
geçmiş" diye sorarken üçüncü bir kopya doğacaktı. `clock.FORMAT` ve `clock.parse()` eklendi,
tool onu kullanıyor.

**Bitti kriteri:** vakti gelen hatırlatıcı `main.build`'in kurduğu gerçek sistemde bağlı
istemciye `Announcement` + ses + `AudioEnd` olarak ulaşıyor; hiç cihaz yokken kuyruklanıp
ilk bağlanana veriliyor; kaçırılmış görev toleransa göre çalışıyor ya da kaydedilerek
düşüyor; koşan turun arkasında sıraya giriyor; söz kesme onu etkilemiyor; yedekleme
aralıkla koşuyor; dört kapı yeşil. ✅

**P19'dan devreden:** `memory/` (§11) hâlâ boş — B4'ün iptal jetonu orada kapanacak ve
arka plan LLM işleri bu zamanlayıcının değil, boştaki fırsatın işi (Kural 11).

---

## P20 — Bellek: bağlam penceresi, özet ve kalıcı olgular ✅ TAMAMLANDI (2026-08-10)

**Bağımlılık:** P8 (ajan `summary`/`history` alıyordu ama kimse vermiyordu), P16 (montaj),
P19 (boştaki işin sırası). **Engelleyen açık madde:** yok — §11'in tamamı yazılı ve §19'da
belleğe ait bir madde yok.

`memory/` on birinci katmandı ve tek boş olanıydı. Şema P1'den beri hazırdı
(`messages`, `summaries`, `facts` + repository'leri), `build_messages` özet ve geçmiş
parametrelerini P8'den beri kabul ediyordu — **ikisinin arasında kimse yoktu.** Yani sistem
her turu sıfırdan başlıyordu: iki cümle önce söyleneni hatırlamıyor, konuşma bütçesi diye
bir şey tanımıyordu.

Beş dosya: `memory/budget.py` (bağlam boyutunun bölündüğü tek yer), `memory/window.py`
(pencere + sert kırpma), `memory/recall.py` (§11.3'ün bağlam bloğu), `memory/digest.py`
(boştaki iş: olgu çıkarımı + özet) ve `memory/background.py` (preemptible koşucu).

| Karar | Gerekçe |
|---|---|
| **Bağlam boyutu sunucudan soruluyor** (`LLMClient.context_size`, `/props` → `n_ctx`) | §11.1 bütçenin **gerçek** bağlam boyutundan türetilmesini ve tek yerde tanımlanmasını istiyor. Yapılandırma değeri olsaydı, sunucu başka bir `-c` ile açıldığında iki bileşenin bağlam boyutu hakkında farklı fikri olurdu — maddenin adıyla yasakladığı şey. Sayaç ucunun (Kural 10) ikizi: tahmin edilebilecek bir yol bırakılmıyor |
| **Token sayısı satırda önbellekleniyor** | §11.1 "mesaj başına önbelleklenir" diyor. Sütun (`messages.token_count`) zaten vardı ve boş kalıyordu; sayı bir kez soruluyor, ikinci turda satırdan okunuyor |
| **Sayı tur sırasında değil, bir sonraki pencere kurulurken soruluyor** | Kaydederken sormak, her tura bir HTTP gidiş-dönüşü daha eklerdi (§6, ilk ses gecikmesi) |
| **Kırpma delik bırakmıyor** | Sığmayan mesajda döngü duruyor; daha eskisini araya sıkıştırmak konuşmayı deliklerle dolu bir metne çevirirdi |
| **Kırpma `warning`'e yazılıyor ve sayacı okunabiliyor** | §11.1'in asıl kuralı kırpmanın **istisnai** olması: sık kırpılıyorsa çözüm daha akıllı bir kırpma değil, bütçenin yanlış olduğunu kabul etmek. Sessiz bir kırpma bunu hiç öğretmez |
| **Negatif bütçe yuvarlanmıyor** | Sabit kısım tek başına bağlamı aşıyorsa sorun geçmişin uzunluğu değil; sıfıra yuvarlamak o gerçeği gizlerdi |
| **Olgu çıkarımı ve özetleme tek iş** | "Hangi mesajlar işlendi" sorusunun cevabı şemada zaten var: `summary_id`. Ayrı işler olsalardı çıkarımın kendi filigranı için ikinci bir sütun gerekirdi. Aynı yığında önce olgular, sonra özet — `summary_id` ikisinin birden filigranı |
| **En yeni mesajlar özetin dışında** (`keep_recent`) | Pencerede hâlâ kelimesi kelimesine duran bir mesajı özetlemek, modele aynı konuşmayı iki kez vermek olurdu. Canlı pencerenin sınırına bakmak daha dar olurdu ama yeniden başlatma o sınırı siler |
| **Özet birikimli** | `latest()` tek özet döndürüyor ve §11.1'in dizilimi tek bir özet bloğu koyuyor; eski özet prompt'a konmasaydı kapsadığı konuşma sessizce buharlaşırdı |
| **Aynı olgu iki kez yazılmıyor** | Çıkarım ile özet arasında iş preempt edilirse yığın bir daha işlenir. Kopya olgu, kullanıcının silmek zorunda kalacağı bir depo demek |
| **Boş özet reddediliyor** | Kapsadığı konuşmayı hiçbir şeye çevirmek olurdu (Kural 13) |
| **İptal jetonu asyncio'nun kendisi** | §11.3 "iptal jetonu taşır" diyor; taşınan jeton işin kendi görevi. Projede ikinci bir iptal yolu bilinçli olarak yok (bkz. `adapters/llm.py`, `session/actor.py`) — iki yoldan biri unutulur, ve unutulan yol sessizce çalışmaya devam eden bir arka plan işidir |
| **İş, segment kuyruğa girerken çekiliyor** (`DeviceActor.submit`) | §11.3 "tur kuyruğa girdiği anda" diyor. Turun başladığı yerde çekmek geç olurdu: global kilidi beklerken hâlâ üretim yapan bir özetleme, ilk token'ı bekletir (B4, Kural 11) |
| **Aktör belleği görmüyor** | `session` yalnızca `IdleWork` `Protocol`'ünü tanıyor — turun ne zaman kuyruğa girip ne zaman bittiğini biliyor, arkasında ne koştuğunu değil. `TurnRunner`/`SessionSink` kalıbının aynısı |
| **Koşucu belleği dar bir `Protocol` üzerinden görüyor** (`turn.runner.Conversation`) | `memory` alt katman, doğrudan import edilebilirdi; ama §4 bütün tur akışının GPU'suz **ve** veritabanısız test edilmesini şart koşuyor. Gerçek pencere iki repository ile bir LLM istiyor, turun istediği ise iki yöntem |
| **Tur yalnızca iki satır yazıyor: kullanıcı ve asistan** | Tool sonucu alındığı adımın verisi ve bir sonraki turda bayat; saklamak, modele eski bir hava durumunu konuşma geçmişi diye vermek olurdu (§11.3 zaten "bayatsa tool çağır" diyor) |
| **Söz kesilen turun yanıtı yazılmıyor** | Kullanıcının duymadığı yarım cümleyi "asistan bunu söyledi" diye kaydetmek, geçmişe olmamış bir konuşma yazmak olurdu |
| **Olgular bağlam bloğunun sonunda** | §8.1: değişen içerik en sona, yoksa öneğin baytı değişir ve KV önbelleği düşer. `ContextBlock` yalnızca bir alan kazandı; metnin biçimi (kaynak, tarih, "bayat olabilir" uyarısı) depoyu okuyan tarafta |
| **"İlgili olanlar" bugün tazelik + konuşan** | §11.3 ilgili olguların getirilmesini istiyor ama ilgililiğin nasıl ölçüleceğini söylemiyor; anlamsal arama bir gömü indeksi ister ve ne §19'da maddesi ne de ölçülmüş bir eşiği var. Uydurulmuş bir benzerlik eşiği yerine iki sıralama kuralı yazıldı: **konuşanın kendi olguları önce**, sonra en yeniler. Gerekçe `memory/recall.py`'nin başlığında |
| **İki yeni tool: `fact_list`, `fact_forget`** | §11.3'ün son satırı: "kullanıcının göremediği ve silemediği bir bellek, hata ayıklanamaz bir bellektir." Silme `GERİ_ALINAMAZ` — geri getirileceği yer yok ve §10.2'ye göre sahipte bile onay ister |
| **Sayılar montajda** | `RESERVED_OUTPUT_TOKENS`, `MAX_HISTORY_MESSAGES`, `MAX_FACTS`, `DIGEST_KEEP_RECENT`, `DIGEST_BATCH`, `DIGEST_MAX_TOKENS`, `IDLE_DELAY_SECONDS`. §11 hiçbirine sayı vermiyor; sınıfların içine gömülen sayı ölçülmüş bir karar gibi görünürdü (`max_steps` ile aynı gerekçe) |

**Yol boyunca kapanan küçük çatlaklar:** `SummaryRepository.set_token_count` yoktu (özetin
token'ı her turda yeniden sorulurdu) ve `BackgroundWork.stop()` patlamış bir işi ikinci kez
yükseltmesin diye `await task` yerine `asyncio.wait` kullanıyor — hata zaten kayda geçmiş
oluyor.

**Bitti kriteri:** geçmiş ve özet modele gidiyor; bütçe aşılınca en eskiler kırpılıyor ve
satırlar silinmeden özetleme kuyruğuna düşüyor; token sayıları sunucudan gelip satırda
önbellekleniyor; boşta özet ve olgular yazılıyor; koşan iş tur kuyruğa girer girmez iptal
oluyor ve yarım sonuç yazılmıyor; olgular kaynağı, tarihi ve bayatlık uyarısıyla bağlam
bloğuna giriyor; kullanıcı olguları listeleyip silebiliyor; dört kapı yeşil. ✅

**P20'den devreden:** hiçbir şey — Faz 6'nın iki yarısı (P19 zamanlayıcı, P20 bellek) da
kapandı. Kalan iş §19'un model üçlüsüne (Faz 2), konuşmacı eşiklerine (Faz 4) ve AEC'ye
(Faz 5) bağlı.

---

## P21 — Dört karar: LLM seçimi, kimlik kapısı ve §5'in iki boşluğu ✅ TAMAMLANDI (2026-08-10)

**Bağımlılık:** P16 (montaj), P20. **Engelleyen açık madde:** yok — bu paket üç açık maddeyi
*kapatıyor* ya da geçici olarak yanından geçiyor, hiçbirinin yerine varsayım koymuyor.

Sahibin verdiği kararlar: **ses tarafı bir süre bekliyor** (STT sahtede kalır, ölçümü sonra).

> **Düzeltme (2026-08-15).** Bu paket "sahibin verdiği kararlar" arasına **LLM
> Qwen3.6-35B-A3B**'yi de yazmıştı. Sahip böyle bir karar vermediğini söyledi: ölçümlerin
> yanındaki bir çıkarım, kaydedilirken karara dönüşmüş. §19.2'nin LLM yarısı **yeniden
> AÇIK**; aşağıdaki iki satır o gün yazıldığı gibi bırakıldı, çünkü P21'in kalan kararları
> (`MAYEN_ASSUME_OWNER`, §5'in iki boşluğu) onlara atıf yapıyor. Ölçümler geçerli, ölçümden
> karar üretilmiş olması geçersiz.

| Karar | Gerekçe |
|---|---|
| ~~**§19.2'nin LLM yarısı kapandı: Qwen3.6-35B-A3B.**~~ **2026-08-15'te geri alındı**, yukarıdaki nota bakın. STT/TTS açık kaldı | Ses girişi ölçümü bilinçli olarak erteleniyor; sistemin geri kalanı bitince gerçek STT'ye geçilecek. Kapanan yarı yazılıyor, kapanmayan yarı "seçilmedi" olarak kalıyor — biri diğerini beraberinde kapatmıyor |
| **§19.1 aynı kararla kapandı: CLI-tarzı** | P9 sıralamanın modele göre değiştiğini ölçmüştü; model artık sabit ve o modelde CLI önde (94/94, %22 daha az token). Ayrıştırıcı ve gramer **iki biçimi de** üretmeye devam ediyor: silmek, model değiştiğinde yeniden yazmak demek olurdu ve P9 tam bu yüzden ikisini tutuyordu. Biçime bakan tek satır `main.py`'de |
| **`MAYEN_ASSUME_OWNER`: §19.3'ün yanından geçen geçici kapı** | Eşikler açıkken kimlik `TANINMAYAN` ve §10.2'nin o satırında dört hücre de RED — yani sistem gerçek modelle **hiçbir tool'u** çalıştıramıyordu, ölçülmemiş bir eşik yüzünden bütün tool akışı denenemez durumdaydı. Bayrak açıkken gömüye bakılmadan her segment `SAHİP` sayılır |
| **Kural 6 bozulmuyor** | Yasak, sahipliğin **sesle** verilmesine. Bu kapı kabuk: bayrağı verebilen kişinin makineye erişimi var — §19.14'ün kurulum betiğiyle birebir aynı gerekçe. Her açılışta uyarı yazılıyor (Kural 13) ve konuşmacı tanıma gerçek olduğunda bayrak silinir |
| **`person_id` uydurulmuyor** | Varsayılan sahibin rehberde satırı yok; olmayan bir satırın numarasını yazmak izi ve konuşma kaydını yalan söyler hâle getirirdi |
| **§5 tabloya `(DÜŞÜNÜYOR, SÖZ_KESME) → IDLE` eklendi** | P4'ten devreden açık. Kural 12 "her aşamada iptal edilebilir" diyor ve model üretirken iptal en çok istenen an — metin istemcisinin `/iptal`'i bugün tam burada `InvalidTransitionError` ile patlıyordu. Yoksaymak Kural 13'ün ihlali olurdu |
| **`ÇÖZÜMLÜYOR`'da söz kesme hâlâ tanımsız** | Segment henüz metne dönmemişken kesilecek ses yok. Tablonun bir boşluğunu kapatırken diğerini "simetri olsun" diye kapatmak, varsayımla karar vermek olurdu; sunucu onu hata olarak bildiriyor ve bağlantıyı düşürmüyor |
| **`(DÜŞÜNÜYOR, YANIT_BOŞ) → IDLE` eklendi; `EmptyAnswerError` kalktı** | P8'de bu bir istisnaydı çünkü §5'te karşılığı yoktu. Gerçek modelde boş üretim mümkün ve tur tanımlı bir geçişle bitmeli. **Önce sebep, sonra durum:** §14'ün hata kanalından `empty_answer` gidiyor, sonra durum `IDLE`'a düşüyor — ters sırada istemci turun sessizce bittiğini sanardı |
| **Boş yanıtın izi açıkça `hata`** | İstisna kalmadığı için `TurnTrace.__exit__` onu `tamam` sayardı: duyulmamış bir tur başarılı görünürdü |
| **Duyulmamış yanıt geçmişe yazılmıyor** | P20'nin söz kesilen tur kuralının aynısı |

**Bitti kriteri:** LLM adresi ve modeli yapılandırmada yazılı; `MAYEN_ASSUME_OWNER` açıkken
tool çalışıyor, kapalıyken red modele geri besleniyor (ikisi de montaj testinde); `DÜŞÜNÜYOR`
söz kesmesi turu iptal ediyor ve istemciye `Cancelled` gidiyor; boş yanıt `IDLE`'da bitip
hata kanalından bildiriliyor; `ÇÖZÜMLÜYOR` söz kesmesi hâlâ yükseliyor ve bağlantıyı
düşürmüyor; dört kapı yeşil. ✅

**P21'den devreden:** §19.2'nin STT/TTS yarısı (sahibin kararıyla erteli), §19.3'ün gerçek
eşikleri, AEC ve wake word (§19.6).

---

## P22 — Qt metin arayüzü ✅ TAMAMLANDI (2026-08-10)

**Bağımlılık:** P17 (istemci çekirdeği). **Engelleyen açık madde:** §19.11 idi — bu paket
sahibin kararıyla onu kapatıyor: **PySide6**.

Sahibin niyeti: ses tarafı beklerken **arayüzden yazışarak** kullanmak. Metin yolu bunu
zaten destekliyordu (`TextSegment` sesin yanında birinci sınıf bir çerçeve, P1) — eksik olan
tek şey pencereydi. **Kapsam bilerek dar: metin girdisi, metin çıktısı.** Durum göstergesi,
tool bildirimi, hatırlatıcı yerleşimi ve estetiğin tamamı Faz 7'de.

| Karar | Gerekçe |
|---|---|
| **§19.11 kapandı: PySide6, opsiyonel `gui` ekstrası** | Qt'nin resmi bağlayıcısı ve LGPL. Ekstra olması `voice` ile aynı gerekçe: uçbirim istemcisi ve testlerin çoğu Qt istemiyor, ekransız bir makinede de koşmalı |
| **`core.py` bir satır değişmedi** | P17'nin bütün iddiası buydu ve P18 ses için doğrulamıştı; GUI **dördüncü** `Output` uygulaması. Doğrulanan şey soyutlamanın kendisi: tur takibi, ölü tur filtresi ve söz kesme tek yerde |
| **Metin yolu STT'ye hiç uğramıyor** | `turn/runner.py` yükü `str` görünce transkript odur, `embedding` `None`. Yani sahte STT'nin PCM'de patlaması (§19.2) bu arayüzü hiç ilgilendirmiyor — GUI'den yazışmak gerçek STT'yi beklemiyor |
| **asyncio ayrı iş parçacığında, qasync yok** | Qt'nin döngüsü ana iş parçacığını istiyor. `Output` metotları asyncio tarafından çağrılıp pencereye **sinyalle** dokunuyor: widget'a başka iş parçacığından yazmak tanımsız davranıştır. Ters yön `run_coroutine_threadsafe`. Ek bağımlılık almamak, iki döngüyü birbirine gömmekten ucuz |
| **`run()` senkron ve `asyncio.run`'ın dışında** | `app.exec()` blokluyor; onu bir asyncio görevinin içinden çağırmak döngüyü durdururdu. `__main__.py`'de ayrıştırıcı `_parse()`'a ayrıldı, `main()` hazır `args` alıyor |
| **Durum ve tool bildirimi yazılmıyor, hata yazılıyor** | Kapsam sahibin kararıyla dar; ama sessizce yutulmuş hata Kural 13'ün ihlali ve kullanıcı boş pencereye bakardı. Bağlanamama da pencereye düşüyor — iş parçacığının içinde kalsaydı görünmezdi |
| **Artımlı UTF-8 çözücü** | `TextOutput`'un aynı dersi: sahte TTS baytı sabit boyda kesiyor ve `ş` iki bayt. Parça sınırı karakter sınırı değil. Çözülemeyen yük gerçekten sestir ve boyutuyla bildirilir |
| **Tek `QApplication`** | Qt ikincisine izin vermiyor, kurmak çökme. Var olan örnek yeniden kullanılıyor; testlerin arayüzü ekransız sürebilmesi de buna bağlı |

**Bitti kriteri:** `python -m client --gui` gerçek sunucuya bağlanıp turu tamamlıyor
(ekransız uçtan uca doğrulandı: `QT_QPA_PLATFORM=offscreen`, sahte LLM); çok baytlı karakter
parça sınırında bölünse de doğru çözülüyor; hata ve bağlanamama pencerede görünüyor;
`client/core.py` değişmedi; dört kapı yeşil. ✅

**P22'den devreden:** Faz 7'nin geri kalanı (durum göstergesi, bekleyen kişi yönetimi,
servis yönetimi) ve ses tarafının tamamı.

---

## P23 — Durum göstergesi ✅ TAMAMLANDI (2026-08-13)

**Bağımlılık:** P22. **Engelleyen açık madde:** yok.

P22'nin devrettiği üç kalemin ilki. `StateChanged` çerçevesi sunucudan geliyordu ve
`GuiOutput.state` onu yere bırakıyordu: yazışırken sistemin düşündüğü mü, onay mı beklediği
görünmüyordu.

| Karar | Gerekçe |
|---|---|
| **Durum kendi satırında (`QLabel`), sohbet dökümünde değil** | Her geçiş bir satır olsaydı üç kelimelik cevap dört durum satırı arasında kaybolurdu |
| **Gösterilen metin `State`'in kendi değeri** | İkinci bir Türkçe sözlük, dokümanla kod arasında sürüklenecek bir çeviri katmanı olurdu — adlandırma kuralının kaçındığı şeyin ta kendisi |
| **`turn_id` ayıklanmıyor** | Durum yayın ve §5'e göre aynı anda tek tur var: başka bir cihazın turu da bu pencereyi meşgul ediyor. Gösterilen şey sistemin durumu, bağlantının değil |

**Bitti kriteri:** durum etikete düşüyor, döküme düşmüyor; başka turun durumu da
görünüyor; dört kapı yeşil. ✅

---

## P24 — Tool izinin geçmişe yazılması ve geçmişli ölçüm ✅ TAMAMLANDI (2026-08-13)

**Bağımlılık:** P20 (bellek), P13 (halüsinasyon sayaçları). **Engelleyen açık madde:** yok.

`issues.md`'nin #3, #5 ve #6'sı aynı arıza: model tool gerektiren işte çağrı üretmeden
"yaptım" diyor, sonra da uydurduğu üzerine konuşmayı sürdürüyor. Altın kümede seçilen model
bu hatayı **hiç** yapmıyor (0/50); loglar sebebi gösteriyor.

**Mekanizma.** `turn/runner.py` geçmişe iki satır yazıyordu: kullanıcı ve asistan. Tool
çağrısı hiçbir yere yazılmıyordu (P20'nin "sonuç bayattır" kararı). Model bir sonraki turda
kendi geçmişinde `"hatırlat" → "Tamam, kurdum."` görüyor — yani **tool'suz cevabın örneği**.
Katalog §8.1 uyarınca öneğin en başında, geçmiş ise üretim noktasına en yakın yerde.

| Karar | Gerekçe |
|---|---|
| **Tool'un **adı** geçmişe yazılıyor, sonucu yazılmıyor** | Sonuç ertesi turda bayat (§11.3 zaten "bayatsa çağır" diyor), ad bayatlamaz. P20'nin gerekçesi korunuyor, örnek düzeliyor |
| **Boş yanıtta iz de yazılmıyor** | Yanıt satırı olmayınca tur geçmişte hiç görünmez; yarım tur taklit edilecek örnek bırakmaz |
| **Biçim tek yerde (`turn.runner.called_line`), `evals` onu import ediyor** | Ölçümün geçmişi üretimin geçmişine benzemezse ölçülen şey üretim olmaz |
| **Geçmişli senaryolar ayrı küme (`HISTORY_SCENARIOS`), altın kümeye eklenmedi** | `docs/faz2-olcum.md` o 50 ile ölçüldü; içine eklemek bütün önceki raporları karşılaştırılamaz kılardı |
| **Yeni bir `Kind` açılmadı** | Ölçülen şey yine tool seçimi; geçmiş bir eksen değil, bir **koşul**. Yedinci eksen aynı sınavı iki kez adlandırmak olurdu |
| **Kısa/uzun bağlam ayrı raporlanıyor** (`LONG_HISTORY = 4`) | Tuzağın geçmiş uzunluğuyla büyüyüp büyümediği tek ortalamada erirdi. Sayı bir **rapor kovası**, sistemde eşik değil — hiçbir kod ona bakmıyor |
| **`--gecmis` her biçimi iki kez koşuyor: izli ve izsiz** | Karşılaştırılan şey iki model değil, aynı modelin iki geçmişi. Tek koşu, düzeltmenin işe yarayıp yaramadığını cevapsız bırakırdı |
| **İki negatif kontrol senaryosu** (`gec-05`, `gec-10`) | Tek yönlü ölçülen iyileşme, ölçülmemiş bozulmayı gizler: düzeltme modeli her şeye tool çağırmaya itiyorsa orada görünür |

**Merdiven:** `gec-01/02` zararsız geçmiş (taban çizgisi) → `gec-03/04` kısa geçmişte
çağrısız iddia → `gec-06..09` aynı tuzaklar uzun geçmişte → `gec-09` en zoru (cevabın bayat
kopyası geçmişte duruyor).

**Bitti kriteri:** tur, çağırdığı tool'ların izini geçmişe yazıyor ve sonucu yazmıyor;
geçmişli küme izli/izsiz koşuyor; rapor bağlam kırılımını ayrı gösteriyor; dört kapı
yeşil. ✅

**Ölçüldü (2026-08-13, Qwen3.6-27B-IQ4_XS) — ve tuzak yeniden üretilemedi.** Rapor
`docs/faz3-gecmis.md`. Dört koşunun (cli/json × izli/izsiz) **hepsi aynı**: tool doğruluğu
%90, "çağrı üretilmedi" hatası **sıfır**. Yani izli ile izsiz arasında fark yok — çünkü
izsiz taban çizgisinde de hata yok. Düzeltmenin etkisi **ölçülemedi**; sıfır çıktığı için
"işe yaramadı" da denemez (Kural 14).

Ölçümün gerçek koşumdan farkları, tuzağın neden kurulamadığına dair sıraya konmuş
adaylar: (1) **model başka** — arıza 35B-A3B'de görüldü, bu koşu 27B; (2) **geçmiş çok
kısa** — en uzun senaryo 5 tur, `issues.md`'nin turlarında `messages=24` görünüyor;
(3) ölçümde `config/rol.txt` ve özet/olgu blokları yok.

**Seçilen modelde de koşuldu (Qwen3.6-35B-A3B-IQ4_XS) — sonuç aynı yönde.** Rapor
`docs/faz3-gecmis-35b.md`. Tool doğruluğu %80/%80/%80/%70, ve yine **"çağrı üretilmedi"
sıfır**: arıza bu kümede bu modelde de kurulamıyor. İzli–izsiz farkı tutarsız (cli'de izli
bir hata *fazla*, json'da bir hata *az*) — n=10'da bu gürültü, sinyal değil. Örnekleme
kapalı (`temperature=0.0`), yani fark promptun kendisinden geliyor; yine de bu boyutta bir
küme yön göstermiyor.

**Asıl bulgu ters yönde çıktı ve negatif kontroller yakaladı:** 35B sohbete tool
çağırıyor. `gec-10` ("Bugün biraz yorgunum, neyse.") dört koşunun **dördünde** de
`date_time` üretti, `gec-05` bir koşuda `note_search`. Yani bu modelde eksik çağrı değil,
**fazla çağrı** ölçülebilir bir sorun — ve zorunlu tool / `no_tool` fikri tam da bu tarafı
kötüleştirirdi. Karar bu yüzden ölçüme bağlanmıştı.

**CLI'ye özgü ikinci bulgu:** 35B, CLI biçiminde sorulmayan alan filtresi ekliyor
(`--fields temperature,condition`, `gec-01/02/09`); JSON biçiminde bunu hiç yapmıyor. Aynı
kayıt defteri, aynı senaryolar — fark yalnızca kodlama. §19.1 kapalı ama bu, biçimin
argüman davranışını etkilediğinin yeni bir örneği.

**`issues.md` #2 ölçüm koşumunda yeniden üretildi:** ilk 35B koşusu `ServiceUnavailableError:
akış kesildi` ile düştü, ikincisi sorunsuz tamamlandı. Yani kopma uygulamada değil, 35B'yi
servis eden sunucuda (`--n-cpu-moe 7` ile CPU'ya taşan yapılandırma) ve tekrarlanabilir
değil.

**Yan bulgu, ölçümde kalıcı:** `gec-04` her iki modelde ve dört koşuda da başarısız — "kurdun mu gerçekten?"
sorusuna `task_list` yerine **yeni bir `task_create`** üretiliyor. Doğrulama sorusunu
okumak yerine işi tekrar yapmak, `issues.md` #5'in aynı ailesi ve tool izinden
etkilenmiyor.

**`gec-09` düzeltildi (ölçümün kendi tuzağı).** "Şu an kaç derece?" cümlesine model
`--fields temperature` ekliyordu; bu **doğru** davranış (tek-04 tam olarak onu ölçüyor)
ama beklenti fazladan argüman sayıyordu. Cümle artık alan filtresine davet çıkarmıyor;
argüman doğruluğu %86'dan %100'e çıktı ve bu bir model iyileşmesi değil, ölçüm hatasının
düzeltilmesi.

---

## P25 — Zorunlu tool modu, genişletilmiş küme ve model matrisi ⏳ PLANLANDI

**Bağımlılık:** P24 (geçmişli küme, negatif kontroller), P13 (halüsinasyon sayaçları),
P6 (gramer üreteçleri). **Engelleyen açık madde:** yok.

P24'ün asıl bulgusu ters yöndeydi: 35B-A3B sohbete tool çağırıyor (`gec-10` dört koşuda da
`date_time`). O bulgu "zorunlu tool / `no_tool` bu tarafı kötüleştirir" diye yazılmıştı.
Sahip bunun tersini savunuyor: adı konmuş bir seçenek (`no_tool`), örtük bir biçim
kararından kolay olabilir. **İkisi de ölçülmedi.** P25 tartışmayı sayıya çeviriyor —
serbest dal silinmiyor, zorunlu mod yanına konuyor, kaybeden ölçümden sonra siliniyor.
Repo bunu zaten iki kez böyle yaptı: CLI/JSON ve izli/izsiz.

### P25.1 — `no_tool` ve `ToolMode` ✅ TAMAMLANDI (2026-08-13)

| Karar | Gerekçe |
|---|---|
| **Yeni eksen (`ToolMode.SERBEST` / `ZORUNLU`), mevcut dalın yerine değil yanına** | Serbest modda tek bayt değişmezse `docs/faz2-olcum.md` ve `faz3-*` geçerli kalır ve iki mod aynı koşuda karşılaştırılabilir |
| **`no_tool` `Registry`'ye **girmiyor**** | Tool olsaydı bir `Effect` sınıfı gerekirdi; §10.2'nin `TANINMAYAN` satırı dört hücrede de RED, yani `MAYEN_ASSUME_OWNER` olmadan zorunlu modda tek çıkış yolu reddedilen bir tool olurdu — sistem sohbet bile edemezdi |
| **Bir yetenek değil, kontrol akışı işareti** | `tools/grammar.py`'de `NO_TOOL` sabiti (adın yazıldığı tek yer) ve gramerin bir dalı; `agent/loop.py`'de "tool dalını kapat, `PROSE_GRAMMAR`'a geç" anlamı. `policy` hiç görmez, Kural 4 bozulmaz |
| **Katalogda değil `instructions()` içinde anlatılıyor** | Katalog §9.1'in yetenek listesi; oraya yetenek olmayan bir satır koymak §9.1'in "ikinci, bağımsız metin" hatasının yeni bir örneği olurdu |
| **`no_tool` adım harcamıyor** | `MAX_ADIM` §8.2'nin *tool* sayacı; düzeltme turlarındaki gerekçenin aynısı |
| **Modu `main.py` açıkça geçiyor, varsayılanı yok** | `max_steps`, `min_chars` ve diğerleriyle aynı: işletim değeri, ölçülmüş sabit değil |

**Bilinen maliyet, baştan yazılı:** zorunlu modda her sohbet turu önce `<no_tool>` üretip
**ikinci bir üretim turu** açmak zorunda. §6'nın ilk-ses bütçesi gramerin ilk token'da
dallanmasına dayanıyordu; bu mod onu en sık senaryoda harcıyor. Önek cache'de kaldığı için
pahalı değil ama sıfır da değil — P25.3 bunu TTFT olarak ölçüyor.

**Bitti kriteri:** serbest modda üretilen gramer ve prompt bayt bayt bugünküyle aynı (test
kilitler); zorunlu modda gramer prose dalı üretemiyor; `no_tool` dönen tur adım sayacını
artırmadan yanıt üretiyor; dört kapı yeşil. ✅

**Yan bulgu — `main.py`'nin `CALL_FORMAT`'ı JSON'du.** P21 §19.1'i CLI olarak kapatmış,
sabitin kendi docstring'i de "CLI-tarzı olarak kapandı" diyor, ama değer `CallFormat.JSON`
duruyordu; `tests/test_main.py` (CLI biçiminde bir çağrı besliyor) bu yüzden düşüyordu ve
düşüş P25 öncesinden geliyordu. Değer docstring'iyle ve P21'in kararıyla uyumlu hâle
getirildi. Montajın gerçek biçimi tek satır olduğu için etkisi başka hiçbir yere yayılmıyor.

### P25.2 — Senaryo kümesinin genişletilmesi ✅ TAMAMLANDI (2026-08-13)

**50'lik altın küme değişmiyor** — `HISTORY_SCENARIOS`'un dışarıda tutulmasıyla aynı
gerekçe: içine eklemek bütün önceki raporları karşılaştırılamaz kılar.

| Küme | Adet | Ne ölçüyor |
|---|---|---|
| `CONTROL_SCENARIOS` | ~18 | Sohbet, teşekkür, belirsiz cümle, tool konusuna değen ama çağrı gerektirmeyen soru. **Zorunlu modun asıl sınavı** — P24'ün bulduğu fazla-çağrı hatası burada görünür |
| `STEP2_SCENARIOS` | ~8 | Sonuç geri beslendikten sonraki ikinci adım. `gec-04`'ün hatası: doğrulama sorusuna `task_list` yerine yeni `task_create` |
| `ROBUST_SCENARIOS` | ~10 | Gramer sağlamlığı: içinde `--` ve `<` geçen kullanıcı metinleri (A4 ve P11 yasaklarının **model** tarafı), ek almış tool adları, rakam-yazı karışımı |
| Uzun tool sonucu | ~4 | Birkaç bin tokenlık `task_list` sonucu: desteksiz sayı sayacını ve bağlam bütçesini aynı anda yokluyor. Bugün ölçülen en büyük sonuç 115 token |

**Rapora güven aralığı.** n=50'de %94 ölçümünün standart hatası ±6.6 puan — P7'nin
"CLI 94, JSON 92" farkı istatistiksel olarak hiçbir şey söylemiyordu (karar zaten maliyete
dayandırılmıştı, doğru yapılmıştı). Aralık sütunu, küçük farkların sıralama gibi
okunmasını mekanik olarak engeller; Kural 14'ün ruhu.

**Bitti kriteri:** yeni kümeler mevcut 50'nin sonuçlarını değiştirmiyor; her küme rapora
kendi satırıyla giriyor; rapor güven aralığı yazıyor. ✅

**Yazılanlar:** `CONTROL_SCENARIOS` (18), `STEP2_SCENARIOS` (8), `ROBUST_SCENARIOS` (10),
`LONG_RESULT_SCENARIOS` (4 — sonuçlar üretiliyor, elle yazılmıyor). Koşucu iki yeni ekseni
öğrendi (`tool_mode`, `Step2`), rapor üç yeni bölüm kazandı. Komut satırı `--gecmis`
yerine `--kume` (birden çok kez verilebilir) ve `--mod` alıyor; `gecmis` bir küme değil bir
koşu tarifi olduğu için `SETS` sözlüğünde değil, `_runs`'ta.

Kararlar, dosyalarda gerekçeleriyle birlikte:

| Karar | Gerekçe |
|---|---|
| **İkinci adım da *tool* grameriyle üretiliyor**, `PROSE_GRAMMAR` ile değil | Negatif kontrol satırlarında doğru cevap "çağrı yok"; o dalı gramerle kapatmak, ölçülmek istenen hatayı üretilemez kılardı |
| **`step2` ile yanıt turu birbirini dışlıyor** | İkisi iki farklı gramerle üretilen iki çıktı; aynı satıra ikisini birden yazmak ölçülen şeyi belirsiz bırakırdı. Bir test kilitliyor |
| **`no_tool` ile düz metin aynı düzleme iniyor** (`call is None`) | İki mod ancak böyle karşılaştırılabilir. İşaretin gerçekten yazılıp yazılmadığı ayrı bir alanda (`no_tool`) duruyor: yoksa grameri hiç kullanmayan model ile doğru kullanan model aynı satıra düşerdi |
| **`is_no_tool` `parse()`'tan önce** | `agent/loop.py`'nin aynı sırası: işaret defterde yok, `parse()` onu `UnknownToolError` sayar ve §17.1'in birinci sayacı kendi kontrol akışımızı halüsinasyon diye raporlardı |
| **Güven aralığı Wilson, normal yaklaşım değil** | İlgilenilen bölge uçlara yakın (%94, %100) ve normal yaklaşım orada 1'i aşan ya da genişliği sıfır olan aralıklar üretiyor. `n=50, p=1.0`'da normal "[100, 100]" der, Wilson "[93, 100]" |
| **Uzun sonuçlar üretiliyor, elle yazılmıyor** | Yüz satırı elle yazmak, bir satırı yanlış yazıp ölçümü kendi hatasıyla bozmanın en kolay yolu |
| **Metin tekilliği küme *içinde*, kümeler arasında değil** | `gec-06`, `gec-03`'ün cümlesini bilerek tekrar ediyor; ölçülen tek fark geçmişin uzunluğu |

**Kontrol kümesinin son dört satırı bilerek anahtar kelime tuzağı** ("hava", "Ali",
"saat", "ders" geçiyor ama hiçbiri istek değil). Onlar olmadan bir anahtar kelime
eşleştiricisi de bu kümeden %100 alırdı — yani küme hiçbir şey ölçmezdi. Bir test
dördünün de kümede kalmasını kilitliyor.

**Ölçüm henüz koşulmadı** (Kural 14): bu paket kümeleri ve koşucuyu yazdı, sayı üretmedi.
Sayılar P25.3'ün işi.

### P25.3 — Model matrisi

3 model (Qwen3.6-27B, Qwen3.6-35B-A3B, LFM2.5-2.6B) × 2 çağrı biçimi × 2 mod, artı geçmişli
küme. **vLLM'deki Qwen3.5-9B bu matriste yok:** `LlamaCppLLM`'in gönderdiği `grammar` alanını
vLLM sessizce yok sayıyor (400 dönmüyor, kısıtsız üretiyor), yani ayrı bir adaptör
yazılmadan alınacak her sayı çöp olur. Adaptör kendi paketine bırakıldı.

Tek kart olduğu için koşu seri; her adım bir sunucu yeniden başlatması. **Her koşunun
sunucu bayrakları rapora yazılır** — `docs/faz2-olcum.md`'nin başındaki bayrak bloğunun
sebebi bu. Örnekleme ayarları üç modelde eşitlenir: adaptör `temperature: 0.0` gönderiyor
ama `--presence-penalty` sunucuda kalıyor ve bugün modelden modele farklı (35B'de 1.5,
27B'de 0), yani eşitlenmezse karşılaştırılan şey model değil bayrak seti olur.

Bağlam ayarı, P25 öncesi ölçülen değerlerle: `-c 16384 -cram 2048 -ctxcp 2`. Gerekçeler ve
KV geometrisi ölçüm raporunda.

**Yeni sayaç: TTFT.** Rapor bugün `ort. sn` yazıyor, ilk-token gecikmesini yazmıyor —
oysa §6'nın bütçesi o ve §19.4 hâlâ açık. Zorunlu modun ekstra üretim turunun bedeli de
ancak burada görünür.

**Bitti kriteri:** `docs/faz4-cagri-modu.md` — iki modun negatif kontrollerdeki farkı,
TTFT maliyeti, ve üç modelin matrisi. Sonuç ne çıkarsa çıksın kaybeden mod silinir; iki
modun kalıcı olarak yan yana yaşaması bir teslimat değil, ölçüm süresince bir durum.

**Araç tarafı hazır (2026-08-13); matris modellerin yüklenmesini bekliyor.**

- **TTFT ölçülüyor** ve yalnızca **ilk** üretimden alınıyor: düzeltme turu kullanıcının ilk
  sesi beklediği yerde değil, zaten kaybedilmiş bir turun içinde. `ort. sn` ile ayrı
  sütunlar, çünkü tamamlanma süresi üretilen token sayısıyla büyüyor, ilk ses büyümüyor.
- **Sunucu ayarları rapora koşu anında `/props`'tan okunuyor**, başlatma komutundan
  kopyalanmıyor. `docs/faz2-olcum.md`'nin bayrak bloğu elle yazılmıştı; komut değiştiğinde
  öyle bir blok raporu sessizce yalancı yapar. Okuma `evals/__main__.py`'de, adaptörde
  değil: bu bir ölçüm aracının merakı, tur akışının ihtiyacı değil.
- Raporun başlığı artık "Faz 0 — …" demiyor: aynı üreteç faz 4'ün raporunu da yazıyor.
- **Ham çıktı model başına ayrı dosyada** (`docs/faz4/`), `docs/faz2/` ile aynı gerekçe:
  rapor üretiliyor, yani bir sonraki model aynı dosyaya yazılırsa öncekinin sayıları
  silinir. `docs/faz4-cagri-modu.md` üç model tamamlanınca yazılacak **okuma** olacak.

#### 27B ölçüldü (2026-08-13) — `docs/faz4/qwen3.6-27b-iq4xs-pp0.md`

> **Bu koşu `presence_penalty=0` ile yapıldı ve matrisin dışında kaldı.** Sahip 1.5'i
> doğru değer saydı; 27B `docs/faz4/qwen3.6-27b-iq4xs.md`'de o değerle yeniden koşuldu.
> Dosya silinmedi: aynı model, aynı senaryolar, tek fark bir bayrak — o bayrağın *ne kadar*
> fark ettiğini gösteren tek ölçüm bu ikili. Aşağıdaki sayılar `pp=0`'ın sayılarıdır.

28 koşu: 2 biçim × 2 mod × (altın 50, kontrol 18, adım2 8, sağlamlık 10, uzun 4, geçmiş
10×2). `-c 16384`, `presence_penalty=0`, adaptör `temperature: 0.0`. **Karar verilmedi** —
üç modelin biri ölçüldü.

**Zorunlu mod altın kümede iki biçimde de yukarı gitti** (CLI %94→%98, JSON %86→%94) ve
kazancın tamamı **tek bir eksende**: eksik argüman (CLI %57→%86, JSON %14→%57). Mekanizma
görünür — serbest modda model eksik şehri "Ankara", eksik hedefi "default" diye uyduruyordu;
zorunlu modda `no_tool` yazıp soruyor. **Ama aralıklar çakışıyor** (%94 [84–98] ile
%98 [90–100]) ve raporun kendi kuralı bu iki sayıyı sıralamayı yasaklıyor. Yön iki biçimde
de aynı ve tek eksende toplanmış olması onu tesadüften ayırıyor; yine de bu bir *gözlem*,
n=50'de kanıt değil.

**Zorunlu modun bedeli de ölçüldü ve tek yerde çıktı: aşırı çağrı.** Geçmişli kümenin
"tool gerekmez" ekseni iki biçimde de **%100 → %50**; `gec-10` ("Bugün biraz yorgunum,
neyse") zorunlu modda dört koşunun ikisinde `date_time`, ikisinde `task_create` çağırıyor,
serbest modda hiçbirinde çağırmıyor. P24'ün 35B'de bulduğu davranış, 27B'de **zorunlu
modun kendi ürettiği** bir hata olarak geri geldi. Kontrol kümesinde ise sonuç kararsız
(CLI %100→%94, JSON %94→%100), yani orada bir fark yok.

**TTFT farkı yok** (0.17→0.19 sn CLI, 0.19→0.18 JSON). **Ama P25.1'in yazdığı asıl bedel
bu ölçümde yok:** koşucu `no_tool` işaretini görünce duruyor, ardından gelmesi gereken
ikinci üretimi hiç koşmuyor. Yani "her sohbet turu ikinci bir üretim açar" maliyeti
**ölçülmedi**; toplam sürenin zorunlu modda düşmesi (0.63→0.39 sn) tam da bu eksik turdan
geliyor, bir hızlanma değil. Bunu ölçmek koşucuya `no_tool` sonrası bir yanıt turu eklemeyi
gerektirir; ölçülmeden "ucuz" denemez (Kural 14).

**Gramer tarafı temiz:** 28 koşuda sıfır uydurulan tool, sıfır uydurulan argüman. Zorunlu
modda `no_tool` sütunu ile "çağrı üretilmeyen tur" sütunu **her satırda eşit** — gramer
başka çıkış bırakmıyor ve model onu doğru kullanıyor. Düzeltme turu neredeyse hiç yok
(28 koşuda toplam 1).

**Yeni kümeler ilk koşuda dört gerçek bulgu verdi** — üçü modda değil modelde, biri sayaçta:

| Bulgu | Nerede | Ne |
|---|---|---|
| Türkçe özel adlar İngilizceleşiyor | `tek-07`, `tek-04`, `sag-09` | `masaüstü` → `desktop`/`masaustu`, `İstanbul` → `Istanbul`. **§19.9'un WOL hedef eşleşmesi birebir** ve `contact_save`'in ad eşleşmesi de öyle; bu tam olarak o eşleşmelerin kaçıracağı hata. C1'in (§19.15) tersten görünen hâli |
| `--` sessizce siliniyor | `sag-01`, dört koşuda da | "Not al: `-- bugün --` çok yoğun geçti" → `bugün çok yoğun geçti`. A4'ün yasağı **gramerde**; model işaretleri gramerin izin verdiği yerde bile atıyor. Sağlamlık kümesinin var oluş sebebi buydu |
| Türkçe gün numarası kayıyor | `tek-12` | "Salı" → `--day 3` (doğrusu 2), üç koşuda. §9.2'nin 1=Pazartesi numaralandırması |
| `gec-04` 27B'de de düşüyor | dört koşuda da | "Kurdun mu gerçekten?" → `task_list` değil **yeni bir** `task_create`. 35B'de görülen hata modele özgü değil |

**Desteksiz sayı sayacının sınırı da görünür oldu** ve bu bir model hatası değil: `tek-05`'te
model `%29.4` ve `22.6 GB` yazıyor — ikisi de sonuçtaki sayılardan **türetilmiş** aritmetik
(9.4/32 ve 32−9.4). Sayaç türetmeyi desteksiz sayıyor. Dar adı zaten bunu söylüyordu
("yanıtta geçip sonuçta bulunmayan sayı"), ama rapor bunu okuyana anlatmıyor; üç model
bitince yazılacak okumada bu iki senaryo ayrıca işaretlenecek.

**izli/izsiz farkı yine sıfır** — 27B'de de her çift birebir aynı. P24'ün düzeltmesinin
etkisi hâlâ **ölçülmemiş**; kümedeki en uzun geçmiş 5 tur ve üretimde hata ~24 mesajda
görülmüştü.

#### 35B-A3B ölçüldü (2026-08-13) — `docs/faz4/qwen3.6-35b-a3b-iq4xs.md`

**Bayraklar 27B'ninkiyle eşit değil:** `presence_penalty` 1.5 (27B'de 0), `top_p` 0.8
(27B'de 0.95). Sahip 1.5'i doğru değer sayıyor ve 27B'yi onunla tekrar açacak. **Modeller
arası sütun bu yüzden şimdilik okunamaz; model *içi* mod ve biçim karşılaştırması geçerli**,
çünkü bir modelin bütün koşularında bayraklar sabit.

`top_p` farkının eşitlenmesi **gerekmiyor** ve bu bir tercih değil, sonuç: adaptör her
istekte `temperature: 0.0` gönderiyor, yani üretim argmax. `top_k`/`top_p`/`min_p` yalnızca
aday kümesini buduyor ve en yüksek olasılıklı token'ı hiçbir zaman atmıyorlar, dolayısıyla
argmax değişmez. `presence_penalty` ise zincirin başında (`penalties` → … → `temperature`,
sunucunun kendi `samplers` listesi) ve **logit'leri** değiştiriyor — argmax'ı gerçekten
kaydırabilen tek fark o. `repeat_penalty` (1.0) ve `frequency_penalty` (0.0) iki modelde
zaten aynı.

**Zorunlu mod 35B'de her yerde daha kötü — 27B'nin tam tersi.** Altın küme CLI %94→%88,
JSON %94→%84; negatif kontrol kümesi CLI %94→%72, **JSON %94→%50**. JSON zorunlu modda
18 kontrol senaryosunun 9'u tool çağırıyor: "Hı hı, anladım" → `date_time`, "Rehber dediğin
şey nedir" → `contact_get`, "Ali'yle dün konuştum" → `contact_get --name Ali`. P24'ün
35B'de bulduğu fazla-çağrı eğilimi zorunlu modda **iki katına** çıkıyor.

**İki modelin yönü zıt, ve bu tek başına P25'in cevabı.** 27B'de zorunlu mod eksik argümanı
düzeltiyordu (%57→%86); 35B'de aynı mod sohbeti tool'a çeviriyor. Bir modda karar vermek,
ölçülen iki modelden birini seçmek olurdu. **Karar üçüncü modelden sonra ve eşitlenmiş
bayraklarla verilecek** — bugünkü tabloyla "zorunlu mod kazandı/kaybetti" demek Kural 14'ün
ihlali olur.

**35B kendi içinde de daha zayıf:** sağlamlık kümesinde argüman doğruluğu %62 (27B %89) ve
geçmişli kümede %71 (27B %100). `no_tool` işaretini doğru kullanıyor — sütunlar her satırda
eşit — yani hata gramerde değil, seçimde.

**Ölçüm aracı bu koşuda bir kez daha sınandı ve bu sefer ayakta kaldı:** 7 senaryo servis
hatası aldı, 5'i ikinci denemede tamamlandı, 2'si (`gec-09`, iki geçmiş biçiminde de)
ölçülemedi ve raporda kendi bölümünde duruyor. İlk denemede aynı kesinti 28 koşunun
tamamını çöpe atmıştı.

**Aynı koşu raporda bir kusur daha gösterdi ve düzeltildi:** `no_tool` tablosunun eşitlik
kontrolü ölçülemeyen satırları da sayıyordu (`call` onlarda zaten `None`), yani servis
kesintisi "işaret yazılmamış" gibi görünüyordu — tablonun kendi tuttuğu değişmezi yanlış
alarma çeviren bir hata. Bir test kilitliyor.

#### 27B `pp=1.5` ile yeniden ölçüldü (2026-08-13) — `docs/faz4/qwen3.6-27b-iq4xs.md`

Matrisin 27B ayağı bu; sıfır servis hatası, 28 koşu tam.

**`presence_penalty` neredeyse hiçbir şeyi değiştirmedi.** Aynı model, aynı senaryolar,
tek fark bayrak — altın kümede CLI %94→%90, JSON %86→%88, zorunlu modda ikisi de değişmedi
(%98 ve %94). Farkların hepsi bir-iki senaryo, yani aralıkların çok içinde. Eşitleme
kaygısı bu model için pratikte boşa çıktı; **ama bunu ancak ölçtükten sonra söyleyebiliyoruz**
ve 35B'de aynı olduğu iddia edilemez. Bayrağın rapora kendiliğinden yazılması bu
karşılaştırmayı mümkün kılan şeydi.

**Zorunlu modun 27B'deki kazancı bayrak değişikliğinden sağ çıktı:** CLI %90→%98, JSON
%88→%94, ve kazanç yine tek eksende — eksik argüman %29→%86 (CLI) ve %29→%71 (JSON).
`pp=0` koşusundaki mekanizmanın aynısı: serbest modda model eksik alanı uyduruyor, zorunlu
modda `no_tool` yazıp soruyor.

**Yani model bağımlılığı artık iki bayrak setinde de doğrulandı:** 27B'de zorunlu mod
kazandırıyor, 35B'de kaybettiriyor. P25'in sorusunun cevabı "hangisi daha iyi" değil,
"**modele göre değişiyor**" — tıpkı §19.1'in CLI/JSON kararının P9'da olduğu gibi. Karar
LFM2.5'ten sonra, ve büyük ihtimalle P21'in yaptığı şekilde verilecek: model sabitlenir,
mod o modele göre seçilir.

#### LFM2.5-2.6B **bu sözleşmeyle ölçülemiyor** (2026-08-13) — `docs/faz4/lfm2.5-2.6b-q8.md`

İki kez koşuldu, ikisi de geçersiz, ve **ikinci koşu asıl sebebi ortaya çıkardı.**

**Sebep, modelin sohbet şablonu.** LFM2.5 üretimin başına *koşulsuz* bir düşünce açıcısı
koyuyor; `/apply-template` bunu doğruluyor:

```
<|im_start|>assistant\n<think>
```

`<think>` üretilen bir token değil, **prompt'un parçası**, ve şablonda onu kapatan bir
anahtar yok. Yani her üretim açık bir düşünce bloğunun *içinde* başlıyor.

Bu, §6'nın "dal ilk token'da belli olmalı" sözleşmesiyle doğrudan çelişiyor ve iki modda
iki farklı yoldan aynı yere çıkıyor:

- **Serbest modda** düz metin dalı serbest; model ortalama 173 token düşünüyor ve hiçbir
  zaman çağrıya geçmiyor.
- **Zorunlu modda** gramer `<tool> …` üretiyor, ama metnin tamamı `<think><tool> date_time`
  oluyor ve `is_call()` öneki 0. konumda aradığı için bunu düz metin sayıyor.

Her satırda `argüman doğruluğu —` yazması bunun kanıtı: **tek bir çağrı bile
ayrıştırılmadı.** Rapordaki %30'lar modelin becerisi değil, çağrı beklenmeyen senaryoların
oranı (15/50). Model kendi içinde doğru akıl yürütüyor ("I need to use the `date_time`
tool"); uyuşmayan şey model değil, sözleşme.

**Bu bir gramer hatası değil, bir uyumluluk sınırı** ve adı konulmalı: §6'nın ilk-token
kuralı, düşünce bloğunu zorunlu kılan modelleri **dışlıyor**. Sahip "modele özgü gramer
yazalım mı" diye sordu; cevap hayır, ama meşru varyantı var ve ikisi karıştırılmamalı:

1. **Modele özgü gramer — hayır.** Her şey tek defterden üretiliyor (katalog, iki biçim,
   iki mod); model başına gramer, §9.1'in "ikinci, bağımsız metin" hatasının gramer hâli
   olurdu ve altın küme modelleri karşılaştırmayı bırakırdı — her model kendi sınavına
   girer.
2. **Üçüncü bir eksen ("düşünme öneki") — ölçülebilir bir seçenek.** `root ::= think?
   tool-call`, CLI/JSON ve serbest/zorunlu ile aynı düzeyde, aynı disiplinle ölçülür,
   kaybeden silinir. **Ama bedeli §6'nın kendisi:** ilk ses, düşüncenin tamamı bitene kadar
   bekler. 200 t/s'de 200 token'lık bir düşünce ~1 saniye ve §19.4'ün gecikme hedefi hâlâ
   açık, yani "kabul edilebilir" diyecek bir sayı yok. Bu yüzden **açılmadı**: bir açık
   maddeyi varsayımla kapatmak olurdu.

**Karar için gerekli değil.** LFM2.5 aday değil, üçüncü veri noktasıydı: P25'in sorusu iki
modelde zaten zıt yönde cevaplandı. (Bu paragraf 2026-08-15'e kadar gerekçe olarak
"§19.2'nin LLM yarısı zaten 35B olarak kapandı" diyordu; o kapanma geri alındı — ama P25'in
sonucu ondan bağımsız, çünkü zorunlu mod **iki** modelde de ölçülmüştü.)

**Yan bulgu — üretim açığı.** Bugün böyle bir model bağlanırsa sistem sessizce boş ya da
çağrısız yanıt üretir. Adaptör, `content`'i `<think>` ile başlayan bir yanıtı fark edip
söyleyebilir — FakeSTT'nin PCM için yaptığının aynısı. Sahibin kararı; yapılmadı.

<!-- ilk koşunun (reasoning_format açık) notu, kayıt için -->
#### İlk LFM2.5 koşusu — farklı bir sebeple geçersizdi

Sayılar felaket görünüyor (zorunlu modda %0–%30) ama **ölçülen şey model değil, sunucunun
çıktıyı hangi alana yazdığı.** LFM2.5 bir akıl yürütme modeli ve llama-server bu modelde
`reasoning_format` açık çalışıyor: üretimi `reasoning_content`'e koyuyor, `content` boş
kalıyor. `LlamaCppLLM.stream` yalnızca `delta.content` okuyor, yani tur boş çıktı görüyor.

**Model aslında doğru çalışıyor** — elle denendi: gramer uygulanıyor ve model
`<tool> system_metrics` üretiyor, metin yalnızca yanlış alanda duruyor. Mekanizma:
ayrıştırıcı `</think>` görene kadar her şeyi düşünce sayıyor ve **gramer `</think>`
üretilmesine izin vermiyor**, dolayısıyla çıktının tamamı sonsuza kadar düşünce etiketi
alıyor. Bütçe sorunu yok, düşünme sorunu da yok: gramer düşünmeyi zaten engelliyor.

**Çözüm sunucu tarafında ve tek bayrak: `--reasoning-format none`.** Şablonda
`enable_thinking` anahtarı yok (bakıldı), `chat_template_kwargs` ve `reasoning_budget`
istek gövdesinde denendi, ikisi de bu modelde etkisiz.

27B ve 35B'de sorun yoktu (`/props`: `reasoning_format: none`), ilk iki koşu etkilenmedi.
**Rapor dosyası silinmedi, başına uyarı konuldu** — hatanın kendisi kayıt.

**Bir üretim açığı da görünür oldu.** Bugün akıl yürüten bir model bağlanırsa sistem
sessizce boş yanıt üretir; P21'in `YANIT_BOŞ` yolu bunu *görünür* kılıyor (Kural 13 sağlam)
ama sebebini söylemiyor. Adaptör `reasoning_content` dolu gelen bir yanıtı fark edip
`ServiceUnavailableError` ile bunu söyleyebilir — FakeSTT'nin PCM için yaptığının aynısı.
Sahibin kararı; yapılmadı.

Bu ilk koşuda sunucu `reasoning_format` **açık** çalışıyordu: gramerli üretim
`reasoning_content`'e yazılıyor, `content` boş kalıyordu ve tur boş çıktı görüyordu
(`ort. token 0`, `TTFT 0.00`). `--reasoning-format none` o kusuru kapattı ve altındaki
asıl uyumsuzluğu görünür kıldı. Denenip **işe yaramayanlar**, bir daha uğraşılmasın diye:
şablonda `enable_thinking` anahtarı yok, istek gövdesinde `chat_template_kwargs` ve
`reasoning_budget` etkisiz.

#### LFM2.5, özel sohbet şablonuyla ölçüldü — `docs/faz4/lfm2.5-2.6b-q8-dusunmesiz.md`

Sahibin önerisi: şablonu biz verelim. Doğru öneriydi ve yukarıdaki (1) numaralı itiraz
buraya geçmiyor — **gramer değişmiyor**, düzeltilen şey modelin servis ayarı.
`config/chat-templates/lfm2.5-dusunmesiz.jinja`, tek satırlık fark: üretim öneki
`<|im_start|>assistant\n<think>` yerine `<|im_start|>assistant\n`. `/apply-template` ile
doğrulandı; gramerli tek istek `<tool> system_metrics` döndürdü.

**Sayılar "LFM2.5 ne yapabilir" değil, "düşünmesi engellenmiş LFM2.5 ne yapabilir"**: model
her zaman düşünecek şekilde eğitilmiş. Mimarimiz §6 gereği düşünmeye yer bırakmadığı için
ölçmek istediğimiz zaten buydu, ama cümle böyle kurulmalı (Kural 14).

Altın kümede %58–%60, dört koşuda da. **Zorunlu modun etkisi sıfır** ve sebebi net: model
zaten her şeye tool çağırıyor. Negatif kontrolde CLI %17/%11, **JSON iki modda da %0** — 18
sohbet cümlesinin tamamı çağrı üretiyor; "tool gerekmez" ekseni %0–%25, eksik argüman
ekseni %0–%14. `no_tool` kaçış yolu sunuyor, model kullanmıyor. Çağrı *gerektiğinde* fena
değil (tek tool %100, ayırt etme %88, serbest metin %86): sorun yetenek değil, **ne zaman
durulacağını bilmemek**.

**Bu, mod ekseninde üçüncü bir yön:** kazandırıyor (27B) / kaybettiriyor (35B) / etkisiz
(LFM2.5). Model bağımlılığı bulgusunu üç noktayla kapatıyor.

**JSON bu modelde CLI'dan açıkça iyi:** argüman doğruluğu %76/%70'e karşı %41/%39; CLI'da
5–9 uydurulan argüman ve 4–7 düzeltme turu varken JSON'da sıfır. P9'un bulgusunun tekrarı
(JSON küçük modellerde önde). §19.1'in CLI kararı 35B için verildi, orada geçerli.

**TTFT 0.04–0.05 sn** — 27B'nin 0.20'sine ve 35B'nin 0.28'ine karşı 4–6 kat. §19.4 sayı
kazandığında karşılaştırılacak ilk şey bu.

**P25.3'ün son boşluğu kapandı (2026-08-13): ilk ses bedeli ölçüldü.** Rapor
`docs/faz4-ilk-ses.md`, gerekçesi `docs/faz4-cagri-modu.md`'nin sonunda. `ort. TTFT`
birinci üretimin ilk token'ını ölçüyordu ve zorunlu modda o token `<tool> no_tool`'un ilk
harfi — kullanıcı onu duymuyor. `ScenarioResult.speech_ttft` turun başından kullanıcının
duyduğu ilk token'a kadar ölçüyor: 27B'nin negatif kontrol kümesinde **0.21 → 0.41 sn
(CLI)** ve **0.16 → 0.40 sn (JSON)**. Kapanış üretimi gerçekten koşuluyor; hiç parça
gelmezse `None` yazılıyor, geçen süre TTFT diye raporlanmıyor (Kural 13). Çağrı üretilen
turlar paydanın dışında — orada ilk ses zaten tool'u bekliyor.

**35B'de de ölçüldü** (`docs/faz4-ilk-ses-35b.md`, aynı gün, aynı `n_ctx`/`presence_penalty`):
CLI **0.28 → 0.35**, JSON **0.22 → 0.36**. Mutlak bedel küçük — A3B'nin `no_tool` üretimi
kısa — ama **payda düşüyor**: 17 çağrısız turdan 13'e (CLI) ve 10'a (JSON), çünkü zorunlu
modda 35B sohbete tool çağırıyor. Yani sayı, modun *doğru davrandığı* alt kümede ölçülmüş
ve bedeli olduğundan küçük gösteriyor. Aynı koşuda kontrol doğruluğu %94 → %72 (CLI) ve
%94 → %56 (JSON), aralıklar çakışmıyor. **Sonuç: 35B'de zorunlu modun iki ekseninde de
artısı yok; 27B'de ise takas sürüyor** (doğrulukta çakışan aralıklar kadar kazanç, ilk
seste iki kat bedel).

**P25 kapandı: zorunlu tool modu silindi (2026-08-13, sahibin kararı).** P25'in tasarımı
baştan "kaybeden silinir" diyordu; ölçüm kaybedeni gösterdi. Silinen: `ToolMode`, `NO_TOOL`,
`is_no_tool()`, `agent/loop.py`'nin `declined` dalı, `main.py`'nin `TOOL_MODE` sabiti,
`evals`'in `--mod` bayrağı ile `no_tool` sayacı ve `speech_ttft`/`_closing_ttft` (zorunlu
mod olmadan serbest modda daima `ttft`'ye eşit), on beş test.

- **Neden kaybetti — mekanizma, sadece skor değil.** `<tool> ` önekini zorunlu kılmak,
  "tool gerekiyor mu" ikili kararını üretimden **önce** alınan bir karardan, tool dalının
  **içinde** alınan "hangi tool" seçimine çeviriyor. Bu, §6'nın ilk token'da dallanma
  tasarımının iptali; o seçimde cümlenin yüzey kelimeleri baskın çıkıyor. P25.2'nin yem
  senaryoları tam bunu yakaladı: "saatin ne kadar hızlı geçtiğine inanamıyorum" →
  `date_time`, "yarın hava güzel olursa" → `weather`, "Ali'yle dün konuştum" →
  `contact_get`.
- **Kazanç tek turluk kümelerde, kayıp çok turluk olanda.** 27B'de altın küme %90→%98 ama
  `geçmiş` %90→%80, iki bağımsız koşuda dört karşılaştırmanın dördünde aynı yönde. Üretim
  çok turluk; `issues.md` #3/#5/#6 zaten çok turluk bir hataydı.
- **Sahibin gerekçesi hız değil doğruluk oldu.** İlk ses bedeli (27B'de iki kat) kararın
  yanında duran bir sayı, dayanağı değil.
- **Serbest dal baytı baytına korundu** — gramer, yönerge ve sistem promptu, silme öncesi
  modüllerle üretilen çıktı karşılaştırılarak doğrulandı. Aksi hâlde `docs/faz2-olcum.md`
  ve `faz3-*` karşılaştırılamaz hâle gelirdi.
- **Geri alma tek komut:** `git apply docs/faz4/zorunlu-mod-geri-alma.patch`. Yamanın
  başlığı gerekçeyi, sayıları ve yeniden ölçüm komutunu taşıyor; temiz bir kopyada
  uygulanıp testlerin tamamı koşularak doğrulandı. **Model değişirse karar da değişebilir**
  — mod ekseni üç modelde üç ayrı yön verdi.

- **Sıradaki:** yok. `docs/faz4-cagri-modu.md` yazıldı; kalan kararlar sahibin.

---

## P26 — Eylem halüsinasyonunun ölçülmesi ✅ TAMAMLANDI (2026-08-15)

**Bağımlılık:** P13 (halüsinasyon sayaçları), P24 (`HistoryTurn`, `tool_rows`), P25.2
(`Step2`, negatif kontroller). **Engelleyen açık madde:** yok.

**Kapsam dışı, açıkça:** `issues.md`'deki hataların **düzeltilmesi**. O kalemler sahibin
ertelediği işler ve P26 onlara dokunmuyor. P26 yalnızca ölçümü, o hataları *görebilir*
hâle getiriyor.

### Sorun: ölçüm üretimdeki halüsinasyona kör

İki ayrı kusur, ikisi de 2026-08-13'te ölçüyle gösterildi.

**1. §17.1'in birinci sayacı yapısal olarak sıfır.** `uydurulan tool`, bugüne kadar
koşulmuş **her** raporda sıfır — beş model, iki biçim, iki mod, bütün kümeler. Sebebi
modellerin doğruluğu değil, `tools/grammar.py:_branch()`'in ürettiği kural:

```
tool-call ::= "<tool> " (call-weather | call-date_time | ...)
```

Tool adları birebir literal alternatif; defterde olmayan bir adı model **üretemez**.
`parse()`'ın `UnknownToolError`'ı ancak gramer atlanırsa tetiklenir, ölçümde hiç
atlanmıyor. Yani o sütun modelin davranışını değil, gramerin çalıştığını ölçüyor —
raporda ise bir sonuç sütunu gibi duruyor (Kural 14). `uydurulan argüman` de büyük ölçüde
öyle; sıfırdan farklı çıktığı yerler ayrı bir bulgu (aşağıda).

**2. Üretimdeki halüsinasyon başka bir şey ve hiç ölçülmüyor.** `issues.md` #3, #5 ve
#6'nın üçü de aynı hata: **yapılmamış bir eylemi yaptım demek, sonra o olmayan kaydın
içeriğini uydurmak.** "Not eklendi" → hiç tool çağrılmamış; "ne ekledin" → "Alışveriş
listesi: Süt, ekmek, yumurta" → veritabanında yok; "emin misin" → "Evet, eminim."

Altın küme bunu **üretemiyor** ve sebebi `evals/runner.py`'de tek satır:

```python
if scenario.result is not None and tool_correct and first.call is not None:
```

Yanıt turu yalnızca **çağrı doğru üretildiğinde** koşuyor; yani modelin iddiaları sadece
iddianın desteklendiği durumda inceleniyor. Model yanlışlıkla hiç çağrı üretmediğinde —
üretimdeki hatanın tam kendisi — hiçbir yanıt üretilmiyor ve hiçbir şey ölçülmüyor.
`desteksiz sayı` sayacı da aynı dalın içinde ve yalnızca sayılara bakıyor.

Harness hatanın kenarına bir kez dokunuyor: `gec-04` ("kurdun mu gerçekten?" → `task_list`
yerine yeni bir `task_create`) her modelde, her koşuda düşüyor. Ama bu "yanlış tool" diye
sayılıyor, halüsinasyon diye değil.

### Kararlar

| Karar | Gerekçe |
|---|---|
| **Hakem modeli yok** | P13'ün gerekçesi aynen geçerli: hakemin kendi halüsinasyonu ölçüme karışır. Ölçülen şey mekanik kalmalı |
| **Tuzak çağrı üzerinden ölçülüyor, metin üzerinden değil** | `issues.md`'nin üç vakasında da gözlenebilir hata bir çağrının **yokluğu**: "ne ekledin" sorusuna doğru cevap `note_search` çağırmaktır. Çağrıyı harness zaten birebir notluyor; iddiayı yargılamaya gerek yok |
| **Yalan iddiayı biz kuruyoruz (`HistoryTurn`, `tool=None`)** | Modelin kendi uydurmasını beklemek ölçümü belirlenimsiz yapardı. P24'ün `tool_rows` makinesi zaten "geçmişte çağrısız duran bir 'tamam, yaptım' cümlesi" kurabiliyor — tuzağın kendisi bu ve her koşuda aynı |
| **Yanıt metni yargılanmadan **kaydediliyor**** | Çağrı üretilmeyen senaryolarda da yanıt turu koşulacak ve metni rapora yazılacak, ama **bir doğruluk paydasına girmeyecek**. Kural 13: kanıtı topla. Kural 14: ölçmediğin şeye sayı verme |
| **`desteksiz sayı` sayacı tırnak içi dizgileri de kapsayacak** | `issues.md` #3'ün uydurması tırnak içinde bir liste. Sayılara ek olarak tırnaklı alıntılar da iki kaynağa (tool sonucu, kullanıcı turu) karşı aranabilir — mekanik ve dar. Tırnaksız serbest cümle hâlâ kapsam dışı ve rapor bunu yazacak |
| **Reddedilen: senaryo başına "yasak içerik" listesi** | Modelin ne uyduracağı önceden bilinemez ("Alışveriş listesi: Süt, ekmek, yumurta" onun kendi icadı). Yalnızca bizim ektiğimiz içeriği yakalar, asıl vakayı kaçırır |

### İş kalemleri

**1. Sayaç 1 ve 2'nin dürüst adlandırılması** → *doğrulama:* rapor, `uydurulan tool`
sütununun yanında gramerle sınırlı olduğunu yazıyor; `CLAUDE.md`'nin "zero hallucinated
tools" cümlesi düzeltilmiş. Test: rapor metninde uyarı cümlesinin varlığı.

**2. `unknown_argument`'in sıfırdan farklı çıktığı yol araştırılsın** → *doğrulama:* CLI'de
çok kelimeli bir değerin ortasındaki `--jeton`un ayrıştırıcıya bayrak gibi göründüğü
hipotezi bir testle ya doğrulanır ya çürütülür. Doğruysa bu sayacın da ne ölçtüğü değişir.

**3. Yanıt turu çağrısız senaryolarda da koşsun** → *doğrulama:* `run_scenario`'nun yanıt
dalı `tool_correct` ve `call is not None` koşullarından kurtulur; `ScenarioResult.answer`
çağrı üretilmeyen senaryolarda da dolu; hiçbir doğruluk paydası değişmiyor (mevcut
testler yeşil kalır, bir yenisi paydanın sabit kaldığını kilitler).

**4. `HALLUCINATION_SCENARIOS` — yeni küme** → *doğrulama:* `issues.md` #3, #5 ve #6'nın
şekli birebir kurulmuş, en az 12 senaryo. Her biri geçmişinde **çağrısız** bir "yaptım"
cümlesi taşıyor (`HistoryTurn(..., tool=None)`) ve güncel tur onu sorguluyor:

- "ne ekledin" → doğru: `note_search`/`note_list`; yanlış: içerik iddia etmek
- "ekledin mi", "emin misin" → doğru: okuma tool'u; yanlış: onaylamak ya da yazma
  tool'unu tekrar çağırmak (`gec-04`'ün hatası)
- "kaç not var" → doğru: `note_list`; yanlış: sayı vermek
- Negatif kontrol: geçmişte **gerçekten çağrılmış** bir tool (`tool="note_create"`) varsa
  aynı soruya tekrar okuma çağrısı yapmak da doğru sayılır — ölçülen şey "iddiayı
  doğrulamadan onaylamamak", "her soruda tool çağırmak" değil

**Altın küme dokunulmuyor** (P25.2'nin kuralı): yeni küme `SETS`'e `halusinasyon` adıyla
eklenir, `docs/faz2-olcum.md` ve `faz3-*` karşılaştırılabilir kalır.

**5. Rapora yeni bölüm** → *doğrulama:* çağrı üretilmeyen senaryoların yanıt metinleri,
"mekanik olarak yargılanmadı" başlığıyla listeleniyor; `halusinasyon` kümesinin tool
doğruluğu kendi satırında, Wilson aralığıyla.

**6. Ölçüm** → *doğrulama:* 27B ve 35B'de koşulur (`n_ctx` 16384, `presence_penalty` 1.5,
ikisi de aynı gün), rapor `docs/faz5-halusinasyon.md`. Bu küme, model seçimini yeniden
açabilir — `docs/faz5-model-secimi.md`'nin "ayırt edilemiyor" sonucu kör sayaçların
üstünde alındı ve P26 sonrası yeniden okunmalı.

**Bitti kriteri:** `issues.md` #3'ün şekli harness içinde **üretilebiliyor** ve düşen bir
senaryo olarak raporlanıyor; hiçbir mevcut sayıcının paydası değişmemiş; dört kapı yeşil.

**Beklenen sonuç, önceden yazılıyor (Kural 14):** bu kümenin düşmesi bekleniyor —
`gec-04` zaten her modelde düşüyor. Düşmezse, tuzak yeterince sert kurulmamıştır ve
senaryolar sertleştirilir; "model temiz çıktı" diye raporlanmaz.

### Yapılanlar (2026-08-15)

**1. İki sayaç sınırıyla birlikte yazıldı.** Rapor `uydurulan tool` / `uydurulan argüman`
sütunlarının yanında gramerle sınırlı olduklarını söylüyor (`report.GRAMMAR_BOUND_COUNTERS`,
bir test varlığını kilitliyor); `ARCHITECTURE.md`'nin "sıfır uydurulan tool" cümlesi ve
`CLAUDE.md`'nin ölçüm boşluğu maddesi düzeltildi.

**2. `unknown_argument`'in yolu bulundu — hipotez doğrulandı ama daraldı.** "Çok kelimeli
bir değerin ortasındaki `--jeton`" doğruydu, ancak o jetonu üretebilen tek gramer kuralı
`cli-item`: `cli-word` `--` ile başlayan kelimeyi zaten yasaklıyor (A4), liste öğesi ise
boşluğa ve tireye izin veriyor. Ölçülmüş çıktı birebir bu (`docs/faz4/lfm2.5-…`): model
liste değerinden sonra yönergedeki `--alan değer` örneğini kopyalıyor. Yani bu sayaç da
modelin değil, **gramerin liste değerini nerede bitirdiğinin** ölçüsü. İki test kilitliyor
(`tests/test_agent_calls.py`).

**3. Yanıt turu çağrısız senaryolarda da kaydediliyor.** Çağrı üretilmediğinde modelin düz
metni `answer`'a yazılıyor; ikinci bir üretim yapılmıyor, çünkü geri beslenecek sonuç yok
ve olmayan bir tool sonucunu uydurmak ölçümü bozardı. `answer_graded` yeni alan: payda
yalnızca eskiden olduğu gibi "doğru çağrı + hazır sonuç" satırlarından geliyor ve bir test
paydanın sabit kaldığını kilitliyor.

**4. `HALLUCINATION_SCENARIOS` — 15 senaryo**, `SETS`'e `halusinasyon` adıyla eklendi.
Altın kümeye dokunulmadı. Üç negatif kontrol: ikisi geçmişte tool'un **gerçekten**
çağrıldığı satırlar, biri hiç çağrı gerektirmeyen (`hal-15`).

**5. Dördüncü sayaç: desteksiz alıntı.** Tırnak içinde geçip ne tool sonucunda, ne
kullanıcı turunda, ne de geçmişte bulunan metin. **Ayrı sütun, `desteksiz sayı`'ya
karışmıyor:** mevcut sayacın değerini değiştirmek `docs/faz2-olcum.md`'den beri süren
karşılaştırmayı bozardı. Rapora ayrıca "mekanik olarak yargılanmadı" bölümü eklendi.

**6. Ölçüldü: `docs/faz5-halusinasyon.md` (27B, `n_ctx` 16384, `presence_penalty` 1.5).**
**35B koşulamadı** — sunucu tek model servis ediyor ve yüklü olan 27B; o yarısı sahibin
modeli değiştirmesine bağlı.

**Sonuç, önceden yazıldığı gibi raporlanıyor: küme düşmedi ve bu "temiz" diye
yazılmıyor.** Tuzak bir kez sertleştirildi (yalan iddia artık uydurulmuş **içerik**
taşıyor, sorular kısa cevaba davet ediyor) ve 27B iki biçimde de %100 aldı — aralık
[%80–%100], yani n=15'te %85'lik gerçek bir oran da böyle görünür. İkinci bir sertleştirme
turu yapılmadı: "model düşene kadar senaryo yaz" kendi yanlılığını üretir. Asıl açıklama
büyük ihtimalle **P27**: `issues.md` #3 ~24 mesajlık bir geçmişte ve üretimin prompt'uyla
görüldü; bu kümede geçmiş en fazla dört tur ve rol metni, `[özet]`, olgular hiç yok.

**Bitti kriteri, olduğu gibi:** #3'ün şekli harness içinde **üretilebiliyor** (evet, ve
ilk koşudan sonra üretilebilir hâle *getirildi*); düşen bir senaryo olarak raporlanması
**gerçekleşmedi** — bu modelde düşen yok. Hiçbir mevcut sayıcının paydası değişmedi; dört
kapı yeşil. ✅

- **Sıradaki:** 35B'nin aynı koşusu (model yüklendiğinde) ve P27.

---

## P27 — Ölçümün üretimin prompt'unu kurması ✅ TAMAMLANDI (2026-08-15)

**Bağımlılık:** P20 (`memory/`), P24 (`HistoryTurn`, `tool_rows`), **P26** (3. iş kalemi
önkoşul, aşağıda). **Engelleyen açık madde:** yok.

**Sıra:** P26'dan **sonra**. İkisi de aynı makineyi kullanıyor — geçmişi harness kuruyor,
tuzak her koşuda aynı. P26 tuzağı geçmişin *içeriğine* koyuyor (yapılmamış eylem iddiası),
P27 *şekline* (özet, olgular, uzunluk). Ters sırada P27'nin senaryolarının çoğu bir kez
daha yazılır.

### Sorun: ölçüm, üretimin kurduğu mesaj dizisini kurmuyor

2026-08-15'te `docs/faz6-olcum.md` koşulurken görüldü. `evals/runner.py:133` kendi
`system_prompt`'unu kuruyor ve `agent.prompt.build_messages`'ı **hiç çağırmıyor**:

| | üretim (`turn/runner.py`) | `evals` |
|---|---|---|
| rol metni (`MAYEN_ROLE_PATH`) | var | **yok** |
| `[özet]` bloğu (§11.2) | var | **yok** |
| olgular (§11.3, bağlam bloğunun sonunda) | var | **yok** |
| bağlam bloğu | `ContextBlock.render()` | elle yazılmış tek satır |

Yani P20'nin bütün bellek katmanı — budama, özet, olgu satırları — ölçümde hiç yok ve
`docs/faz2-olcum.md`'den beri hiç olmadı. Modelin bu blokları nasıl kullandığı bilinmiyor.

**İkinci kusur, birincinin görünen yüzü: geçmiş kovası çok sığ.** 110 senaryonun 20'si
geçmişli (10 tekil senaryo, izli/izsiz iki koşu); kalan 90'ın geçmişi sıfır mesaj.
"Uzun geçmiş" kovasının içi **5 tur, ~247 karakter** ve o beş senaryonun geçmişi
**birebir aynı blok** — yani n=5 değil, tek bağlam üzerinde beş soru. En uzun ölçüm
prompt'u `n_ctx`'in ~%6'sını dolduruyor. Üretimdeki hata ~24 mesajda görülmüştü.

### Kararlar

| Karar | Gerekçe |
|---|---|
| **Hedef "50–100 mesajlık ham geçmiş" değil** | Üretimde 100 mesaj modele hiç ulaşmıyor: `memory/budget.py` pencereyi kapatıyor, eskisi `[özet]`'e dönüşüyor. Modelin gördüğü şey özet + son N mesaj + olgular. Ham uzunluğu ölçmek, üretimde hiç oluşmayan bir girdiyi ölçmek olurdu |
| **Zor olan geçmişin uzunluğu değil şekli** | Çelişki (özet ↔ pencere), bayatlık, budanmış turun bilgisi. Bunlar 5 turda da kurulabiliyor, 100 turda da — uzunluk bunların yalnızca bir tanesinin (pencere taşması) taşıyıcısı |
| **`build_messages` yerine geçmiyor, yanına ekleniyor** | Rol + özet + olgu blokları altın kümenin sayılarını değiştirebilir. Mevcut kolonun yerine geçerse `docs/faz2-olcum.md` ve `faz3-*` karşılaştırılamaz olur (P25.2'nin kuralı). Ayrı koşu olarak eklenir |
| **Geçmişler üretilir, elle yazılmaz** | `LONG_RESULT_SCENARIOS` (P25.2) sonuçları zaten üretiyor; aynı yol geçmiş için de işler. Elle yazılan 20 turluk beş geçmiş, bakımı yapılmayacak beş metin bloğudur |
| **Reddedilen: gerçek `memory/` katmanını koşuya sokmak** | Veritabanı ve özetleyici LLM çağrısı ölçümü belirlenimsiz yapar (P13'ün tool gövdelerini koşmama gerekçesi). Özet ve olgu blokları senaryoda **verilir**, üretilmez |

### İş kalemleri

**1. `evals` `build_messages`'ı kullansın** → *doğrulama:* `evals/runner.py`'nin kendi
`system_prompt`/`user_prompt`'u `agent.prompt`'unkilere devrediyor; rol dosyası koşu
parametresi (yolu raporda yazılı, çünkü sonucu etkiler); mevcut kümelerin paydaları
değişmemiş. Rapor iki kolon taşıyor ve hangisinin hangi önekle koşulduğunu yazıyor.

**2. `ContextBlock`'a özet ve olgu alanlarının senaryodan verilmesi** → *doğrulama:*
`Scenario` özet metni ve olgu listesi taşıyabiliyor; verilmeyen senaryolarda çıktı
bugünküyle **bayt olarak aynı** (bir test kilitler).

**3. `MEMORY_SCENARIOS` — yeni küme, en az 15 senaryo** → *doğrulama:* beş şeklin her biri
temsil ediliyor:

- **özetten okuma**: cevabı `[özet]` bloğunda; yanlış davranış tekrar sormak ya da tool
  çağırmak
- **özet ↔ pencere çelişkisi**: özet "kullanıcı İzmir'de oturuyor", son turda "Ankara'ya
  taşındım"; doğru davranış yeni bilgiyi kullanmak
- **bayat olgu**: `recall.py`'nin "bayat olabilir" uyarısını taşıyan bir olgu; yanlış
  davranış onu kesin bilgi gibi sunmak (doğrudan `issues.md` #3/#5/#6 ailesi)
- **budanmış turun bilgisi**: pencerede olmayan, yalnızca özette geçen bir ayrıntı soruluyor
- **uzun pencerede çağrı bırakma**: P24'ün düzelttiği hata 5 turda tetiklenmedi; 20 turluk
  üretilmiş bir pencerede tetiklenip tetiklenmediği ölçülüyor
- **Negatif kontrol**: özette de pencerede de olmayan bir bilgi soruluyor; doğru davranış
  bilmediğini söylemek ya da okuma tool'u çağırmak, uydurmak değil

**Altın küme dokunulmuyor**; küme `SETS`'e `bellek` adıyla eklenir.

**4. Bağlam kırılımı kovalarının yeniden çizilmesi** → *doğrulama:* `LONG_HISTORY = 4`
bugün "uzun"u 5 turluk 247 karakterlik bir blok olarak tanımlıyor ve bu ad yanıltıcı.
Kova sınırı tur sayısı yerine **token** üzerinden tanımlanır (sayan taraf `count_tokens`,
Kural 10) ve rapor kovanın gerçek doluluğunu `n_ctx` yüzdesi olarak yazar.

**5. Ölçüm** → *doğrulama:* koşum raporu `docs/faz6-bellek.md`. P26 ile aynı gün ve aynı
sunucu ayarlarıyla koşulur.

**Bitti kriteri:** ölçümdeki mesaj dizisi ile `turn/runner.py`'nin kurduğu dizi aynı
fonksiyondan geliyor (bir test bunu kilitler); `bellek` kümesi raporlanıyor; mevcut hiçbir
sayacın paydası değişmemiş; dört kapı yeşil.

**Beklenen sonuç, önceden yazılıyor (Kural 14):** bu kümenin de düşmesi bekleniyor, özellikle
bayat olgu ve çelişki şekillerinde. Düşmezse senaryolar sertleştirilir; "bellek katmanı
temiz çıktı" diye raporlanmaz. Ayrıca 1. kalem tek başına mevcut kümelerin sayılarını
oynatabilir — **oynarsa bulgu odur**: bugüne kadarki bütün raporlar üretimde hiç kurulmayan
bir önekle ölçülmüş demektir.

### Yapılanlar (2026-08-15)

**1. İki önek yan yana, biri diğerinin yerine geçmiyor.** `Prefix.OLCUM` eski dizi ve
baytı baytına korunuyor (bir test kilitliyor); `Prefix.URETIM` `agent.prompt.build_messages`'ı
**çağırıyor** — ikinci bir kopya yazılmadı, çünkü üretimin sırası değiştiğinde ölçümün eski
sırayı ölçmeye devam etmesi P27'nin sebebiydi. `--onek` birden çok kez verilebiliyor; iki
kolon aynı raporda duruyor, çünkü iki ayrı dosya "aynı gün, aynı sunucu" olduğunu okuyana
kanıtlamaz. Rol dosyasının yolu rapora yazılıyor (içeriği sonucu etkiliyor) ve rol yoksa
koşu **başında** düşüyor, yirmi dakikanın ortasında değil.

**2. Özet ve olgular senaryodan veriliyor.** `Scenario.summary` / `.facts`; olgu bloğunun
"bayat olabilir" uyarısı `memory/recall.py`'den geliyor (`STALE_WARNING` açık ada alındı) —
ikinci bir kopya, uyarı değiştiğinde ölçümü sessizce eskitirdi. Verilmeyen senaryolarda
çıktı bayt olarak aynı.

**3. `MEMORY_SCENARIOS` — 17 senaryo, `bellek` adıyla**, beş şeklin her biri üçer satır.
Pencereler üretiliyor (`_window`, `LONG_WINDOW = 20`). Küme öneğe bağlı (`PREFIXES`):
ölçüm öneğiyle koşulsa blokların gideceği yer olmadığı için sessizce başka bir sınav olurdu.

**Yeni alan: `Scenario.accepted`.** Negatif kontrolde iki davranış birden doğru —
bilmediğini söylemek ya da bir **okuma** tool'u çağırmak; yanlış olan uydurmak. Birini
seçip diğerini hata saymak modelin doğrusunu yanlış raporlamak olurdu. Varsayılan boş,
başka hiçbir kümede yok (test kilitliyor), yani hiçbir eski sayı kıpırdamadı.

**4. Bağlam kovası jetona geçti.** `LONG_CONTEXT_TOKENS = 200`, sayan taraf sunucunun
sayacı (Kural 10). Rapor kovanın **gerçek** doluluğunu `n_ctx` yüzdesiyle yazıyor: bellek
kümesinde uzun kova ~574 jeton (%3.5), eski kümelerdeki "uzun geçmiş" ise ~%0.4'lük bir
bloktu ve rapor bunu hiç söylemiyordu. `LONG_HISTORY` silinmedi ama artık rapor kovası
değil; docstring'i ne olduğunu söylüyor.

**5. Ölçüldü, iki rapor** (27B, `n_ctx` 16384, `presence_penalty` 1.5, aynı gün):

- `docs/faz6-bellek.md` — `bellek` kümesi: CLI %94 [73–99], JSON %100 [82–100].
- `docs/faz6-onek.md` — altın küme + negatif kontrol, **iki önekle yan yana**.

**Asıl bulgu, P27'nin önceden yazdığı yerde çıktı: üretimin öneği sayıları oynatıyor.**
Altın küme %98 → %92 (CLI) ve %98 → %90 (JSON); negatif kontrol %94 → %83. Toplamların
aralıkları çakışıyor, yani sıralama yapılmıyor — ama **aynı senaryolar iki biçimde de**
düşüyor ve eksen kırılımı üç ayrı etkiyi ayırıyor:

| Etki | Nerede | Ne |
|---|---|---|
| Eksik argüman ekseni çöküyor (%100 → %71/%57) | `eks-01/05/06` | Model artık sormuyor, bir değer seçip çağırıyor. Muhtemel sebep rol metninin son cümlesi: "Tool kullan her zaman lazımsa" — ölçüm öneğinde o cümle hiç yoktu |
| `tek-01` düşüyor ama **davranış doğru olabilir** | "Saat kaç?" | Üretimin bağlam bloğu saati taşıyor; model okuyup cevaplıyor ve `date_time` fazladan olurdu. Altın kümenin beklentisi, bağlam bloğunun saati taşımadığı bir dünyada yazılmış |
| Serbest metin düşüşlerinin çoğu **ilk harf** | `ser-01/05` | Rol metniyle model düzgün cümle kuruyor (`Süt, …`), beklenti küçük harfli. Harf katlaması Türkçe'de yanlış çalıştığı için yapılmıyor — yani bu satırlar öneğin ölçüsü. `ser-06` istisna: gerçek bir sadakat hatası |
| Negatif kontrolde yeni hata şekli | `kon-05/16` | Düz sohbete `fact_list` çağrısı; öneğe bellek çerçevesi girince model "hatırlamaya" davet ediliyor |

**Altın kümeye dokunulmadı** — `tek-01` ve `ser-*` beklentileri üretimde artık geçerli
olmasa da değiştirilmedi (P25.2): o elli senaryo `docs/faz2-olcum.md`'den beri
karşılaştırma zemini. Fark rapora yazıldı, kümeye değil.

**Bellek kümesinin kendi bulgusu:** `bel-11`'de model `wake_on_lan` çağırmak yerine düz
metinle onay istedi ("Onaylıyor musun?"). Onay §10'un akışı ve **kod** yürütüyor (Kural 5);
model çağrıyı yazmadığında akış hiç başlamıyor ve tur boşa dönüyor. Bu davranış ölçüm
öneğiyle koşulan hiçbir raporda görülmedi ve `config/rol.txt`'de onay isteten bir cümle
yok. Beş şeklin dördü (özetten okuma, çelişki, bayat olgu, budanmış tur) bu modelde temiz
geçti — n=17 ve aralık [%73–%99], yani "bellek katmanı temiz" diye **okunmaz**.

**İki senaryo ilk koşudan sonra düzeltildi, ikisi de ölçümün kusuruydu** (`bel-15`'te
büyük/küçük harf, `bel-17`'de eksik kabul listesi). Bu bir sertleştirme değil — P26'daki
sertleştirmeyle karışmasın diye raporda ayrıca yazıldı.

**Bitti kriteri, olduğu gibi:** ölçümün dizisi `turn/runner.py`'nin dizisiyle aynı
fonksiyondan geliyor (test kilitliyor) ✅; `bellek` kümesi raporlanıyor ✅; mevcut hiçbir
sayacın **paydası** değişmedi ✅ (üretim öneğinin değiştirdiği şey paydalar değil, ayrı bir
kolon); dört kapı yeşil ✅.

### Ardından: P27'nin iki bulgusu ölçüldü (2026-08-15, aynı gün)

P27 iki soru bıraktı ve ikisi de ölçüldü. **İkisi de karar değil, ölçüm:** kod ya da
prompt hiçbir yerde değiştirilmedi.

**1. Rol metni A/B — `docs/faz6-rol.md`.** Şüpheli, mevcut rolün son cümlesiydi ("Tool
kullan her zaman lazımsa"). Aday metin (`config/rol-aday.txt`) onu üçe böldü ve üçü de
ölçülmüş bir hataya karşılık geliyor. `--rol` birden çok kez verilebiliyor, iki metin aynı
raporda iki kolon.

| | mevcut rol | aday rol |
|---|---|---|
| eksik argüman ekseni, CLI / JSON | %71 / %57 | **%100 / %100** |
| negatif kontrol, CLI / JSON | %83 / %83 | %94 / %89 |
| altın küme toplam, CLI / JSON | %92 / %90 | %98 / %96 |

Toplamların aralıkları çakışıyor, oradan sıralama çıkmaz — ama fark **önceden yazılmış
hedef eksende** ve iki biçimde de aynı yönde. Kalan düşüşler bilinen üç artefaktın aynısı,
yani aday metin yeni bir hata sınıfı açmıyor.

**Sahip aday metni benimsedi (2026-08-15): `config/rol.txt` artık o metin**, aday dosya
silindi. §17.1'in kapısı böyle işledi — önce ölçüldü, sonra sahip karar verdi. İki metnin
tam hâli `docs/faz6-rol.md`'de duruyor; dosya değiştiği için raporun kolonları başka türlü
anlatılamazdı. Model değişirse (§19.2) bu A/B yeniden koşulmalı: prompt ile model birlikte
ayarlanır.

**2. Onay kümesi — `docs/faz6-onay.md`, yeni küme `onay` (8 senaryo, üretim öneği).**
`bel-11`'in açtığı soru: model çağrı yerine düz metinle izin istediğinde iş kayboluyor mu.
**Kaybolmuyor** — kullanıcı izni verince ikinci turda çağrı geliyor (%100, n=8, iki
biçimde de); ret satırlarında çağrı yazılmıyor; geçmişsiz sorulduğunda model zaten
doğrudan çağırıyor. Yani `bel-11` genel bir davranış değil ve bedeli bir **tur**, bir iş
değil. n=8, aralık [%68–%100] — "sorun yok" diye okunmaz.

**Bir hata yakalandı ve düzeltildi:** `--onek` çoklu hâle gelince öneği sabit kümeler
(`onay`, `bellek`) tek önekli koşuda sessizce atlanıyordu ve rapor **boş** yazılıyordu,
hiçbir hata çıkmadan. İlk `onay` koşusu tam olarak böyle boş çıktı. İki test kilitledi
(`tests/test_evals_scenarios.py`): öneği sabit küme hangi bayrakla koşulursa koşulsun bir
kez koşar, serbest küme her önek için bir kez. Kural 13'ün ruhu — sessizce hiçbir şey
yapmamak da yutulmuş bir hatadır.

### 35B koşuldu ve benimsenen rol metninin bedeli ortaya çıktı (2026-08-15)

**`docs/faz6-35b.md`** — `Qwen3.6-35B-A3B-IQ4_XS`, beş küme, iki önek. **Bu bir 27B ↔ 35B
karşılaştırması değil:** yüklenen model 3.6 kuşağı, önceki koşular 3.8'di — kuşak ve boyut
birlikte değişiyor, §19.2 buradan kapanmaz.

**`halusinasyon` kümesi üretim öneğinde çöktü: %93 → %33 (CLI), %100 → %53 (JSON).**
`issues.md` #3/#5/#6 ilk kez harness içinde üretildi — model, geçmişteki yalan iddiayı
doğrulamadan onaylıyor ve içeriğini tekrar ediyor (`Evet, Veli'yi rehbere ekledim.
Numarası 0532 111 22 33.`). P26 tuzağı kurmuştu ama 27B ölçüm öneğiyle geçmişti; tuzak
sağlammış, eksik olan önekti.

**`docs/faz6-35b-rol.md`** — sebebi ayıran koşu: aynı model, aynı önek, tek değişken rol
metni.

| küme | eski rol | benimsenen rol |
|---|---|---|
| halüsinasyon, CLI / JSON | %87 / %87 | **%33 / %53** |
| bellek, CLI / JSON | %71 / %76 | %94 / %100 |

**Sebep rol metni.** CLI'de halüsinasyon aralıkları çakışmıyor. Şüpheli cümle: *"İş yapman
gerekiyorsa tool çağır, gerekmiyorsa çağırma."* Bellek kümesinde faydalı (bilgi gerçekten
bağlamda), halüsinasyon kümesinde zararlı (bilgi bağlamda **varmış gibi** duruyor). Gerçek
bir takas, ve bir cümlenin ikisini birden söylemesi gerekiyor.

**Ölçümün kendi hatası, açıkça kayda geçiyor:** `docs/faz6-rol.md`'nin A/B'si yalnızca
altın küme + negatif kontrol üzerinde koşuldu ve "yeni hata sınıfı açmıyor" dedi. Açtığı
sınıf, koşuya konmayan kümedeydi. **Bir prompt değişikliği hedeflediği kümede değil,
hedeflemediği kümede ölçülür** — bundan sonraki rol A/B'si dört kümenin dördünü de koşar.
O raporun başına uyarı konuldu; sonucu silinmedi, yanlış sonucun kendisi de kayıt.

**Sahibin kararı (2026-08-15): şimdilik dosyaya dokunulmuyor.** `config/rol.txt` benimsenen
metni taşımaya devam ediyor, yani üretim şu an halüsinasyon kümesinde %33/%53 ölçülmüş bir
metinle çalışıyor. Açık seçenekler: eski metne dönmek, doğrulama şartını açıkça yazan
üçüncü bir aday ölçmek, ya da olduğu gibi bırakmak.

- **Sıradaki:** sahibin rol metni kararı; §19.2 (model).

### Eksik hücre kapandı: bedel metnin değil, modelin (2026-08-15)

**`docs/faz6-27b-rol.md`** — `Qwen3.8-27B-IQ4_XS`, dört küme, üretim öneği, iki rol metni
yan yana. Yukarıdaki koşunun birebir aynısı, tek değişken model.

| küme (üretim öneği) | 27B eski→? | 27B benimsenen | 35B benimsenen |
|---|---|---|---|
| halüsinasyon, CLI / JSON | (eski metin: %87 / %87) | **%73 / %87** | %33 / %53 |
| bellek, CLI / JSON | (eski metin: %100 / %100) | %100 / %100 | %94 / %100 |

**Benimsenen metnin bedeli 27B'de yok, kazancı da yok.** Halüsinasyon aralıkları eski
metinle örtüşüyor; `bellek` ise eski metinle zaten tavandaydı, yani 35B'deki 71→94
sıçraması da o modele aitmiş. Bir önceki kaydın *"benimsenen metin bir takas"* cümlesi
bu yüzden daraltılıyor: **o cümle 35B hakkındadır, metin hakkında değil.** Bir rol metni
ölçümü koştuğu modele aittir; §19.2 açıkken hiçbir rol metni de kapanmış sayılmaz.

**Üçüncü aday ölçüldü ve reddedildi.** Hipotez: çağırma kararına dokunmadan doğrulama
şartını açıkça yazmak — *"Bir işi yaptığını … ancak o tool'u çağırıp sonucunu gördükten
sonra söyle."* Sonuç 27B'de `halusinasyon` CLI %73 → %40 ve `bellek` CLI %100 → %88;
35B'de çöküşü toparlamadı (%33 → %40, aralıklar örtüşük). Yasak yazılıyken model çağrıyı
yine atlıyor ve **daha ayrıntılı** uyduruyor (`hal-07` → telefon numarasını baştan sona
okuyor). Modelin açısından kural çiğnenmiyor: konuşma bilgiyi vermiş görünüyor, koşul
sağlanmış sayılıyor. **Bu başarısızlık sınıfı yasaklanmaya cevap vermiyor** — dördüncü bir
cümle denemeden önce yeni bir hipotez gerekiyor. Metin `docs/faz6-27b-rol.md`'de birebir
duruyor (`config/rol-aday.txt` sonraki denemeye devredildi).

**Sahibin düzeltmesi:** `Qwen3.6-35B-A3B` bir MoE, aktif 3B — 27B dense'ten daha zayıf
olması bekleniyor. Yani "bedel 35B'ye özgü" değil, **metin zayıflayan modelde kırılıyor**.
Ölçümde iyi çıkan bir rol metni bu yüzden sağlam sayılmıyor.

### Rol metni üç turda yeniden yazıldı ve benimsendi (2026-08-15)

**`docs/faz6-27b-rol2.md`, `docs/faz6-27b-rol3.md`** — `Qwen3.8-27B-IQ4_XS`, dört küme,
üretim öneği, her turda tek değişken: rol metni.

Sahibin yönlendirmesi: metin vaka listesiyle değil, **ne yapılacağını genel olarak
anlatarak** ayrıntılandırılsın — "şöyle olursa şunu yap" denirse birkaç parametresi
değişmiş benzer durumda model ne yapacağını bilemez.

| tur | değişiklik | sonuç |
|---|---|---|
| 1 | yasağı yaz: "yaptığını ancak sonucu görünce söyle" | halüsinasyon %73 → %40 (CLI); **reddedildi** |
| 2 | eksik kavramı yaz: konuşmada söylenen *iddiadır*, tool sonucu *bilgidir* | halüsinasyon %73/%87 → **%100/%100**, ama altın %98→%92, bellek %100→%94 |
| 3 | eksik alan kontrolünü çağırmanın **önkoşulu** yap, önceliği açıkça yaz | altın %100/%96, kontrol %100/%100, halüsinasyon %93/%100, bellek %94/%94 — **benimsendi** |

**Turun her biri bir şey öğretti.** (1) Bu başarısızlık sınıfı yasaklanmaya cevap vermiyor:
model kuralı çiğnemiyor, konuşma ona bilgiyi vermiş göründüğü için koşulu sağlanmış
sayıyor — yasak yazılınca çağrıyı yine atlayıp **daha ayrıntılı** uyduruyor. (2) Doğru
hamle vaka eklemek değil, eksik olan **ayrımı** öğretmek. (3) İki genel ilke aynı düzeydeyse
model birini seçer; sorun vaka eksikliği değil **öncelik** eksikliğiydi.

**Dördüncü tur bilerek koşulmadı.** Kalan iki kayıp (`bel-02`, `bel-12`: "tool gerekmez"
vakasında fazladan çağrı) bir-iki senaryo ve aralıklar örtüşüyor. Kovalamak metni elli
senaryoya uydurmak olurdu — ölçüm kümesi hedef hâline geldiğinde ölçmeyi bırakır.

Önceki metin `docs/faz6-rol.md`'de, ondan önceki ve reddedilen aday `docs/faz6-27b-rol.md`'de
birebir duruyor.

**Benimsendikten sonra 35B'de de sınandı (`docs/faz6-35b-rol3.md`) ve sabahki çöküş kapandı:**
halüsinasyon %33/%53 → **%73/%87**, kontrol %94/%100 → %100/%100. Yazılan ayrım yalnızca
27B'de daha iyi sonuç vermedi, zayıf modelde **dayanıklılık** da kazandırdı — benimseme
kararı verilirken bu bilinmiyordu. Bedel bellek kümesinde ve tek sınıf: "tool gerekmez"
senaryolarında fazladan çağrı (%71/%76; 27B'de iki senaryo, burada dört-beş). O modelde
bellek kazancı zaten yalnızca *"gerekmiyorsa çağırma"* cümlesinden geliyordu ve bedeli
çöküştü. **Yeni metin takasın ucuz tarafını seçiyor: gereksiz çağrı gecikmedir, "evet,
kurdum" demek `issues.md`'dir.**

### Zorunlu tool modu yeni rol metniyle yeniden ölçüldü ve yine kaybetti (2026-08-15)

**`docs/faz6-35b-zorunlu.md`** — soru sahibinden geldi ve haklı bir soruydu: P25 zorunlu
modu ölçtüğünde yürürlükteki rol metni *"Tool kullan her zaman lazımsa"* diyordu, yani
gramer de prompt da modeli çağırmaya itiyordu. Yeni metin ters yönde bir kural taşıyor.

Karar ölçütü koşudan **önce** yazıldı: zorunlu mod kontrol ve bellek kümelerinde serbesti
geçmeliydi. Geçmedi — kontrol %100→%89, bellek %71/%75→%59/%65, altın %94/%96→%86/%86.
Halüsinasyondaki %73/%87→%100/%100 bir başarı sayılmıyor: o kümede zaten çağırmasını
istiyoruz ve zorunlu mod çağırmamayı imkânsıza yakın kılıyor — gramerin ölçüsü, modelin
değil.

**Asıl bulgu: eksik argüman ekseni %86 → %14** (`note_search --query ""`,
`wake_on_lan --target ?`). **Zorunlu modda "sormak" diye bir davranış yok:** `no_tool` "bu
tur tool gerekmiyor" demek, "tool gerekiyor ama alanım eksik" değil. Bugün rol metnine
yazılan öncelik kuralı orada **uygulanamaz** — prompt ile gramer çelişiyor, gramer kazanıyor
ve kazanması gerekiyor. P25'in kararı ayakta; gerekçesi "model fazla çağırıyor"dan
**"kaçış yolu yanlış yerde"**ye keskinleşti.

**İşaretin adı da denendi ve durumu kötüleştirdi** (`docs/faz6-35b-tell-user.md`).
Hipotez: modeli engelleyen dalın yokluğu değil adıydı — `no_tool` olumsuz ve tool-merkezli,
`tell_user` ise sormayı da kapsardı. Sonuç: eksik argüman ekseni %14 → **%0**, kontrol
kümesi JSON'da %89 → **%0** (18 senaryonun 18'i gerçek tool çağırıyor). **Sebep: `tell_user`
bir tool adına benziyor.** JSON'da model tool adlarını `{"name": …}` içine yazmayı bekliyor,
gramer ise işareti yalnızca çıplak literal kabul ediyor; çelişkiye düşünce işareti hiç
seçmiyor. `no_tool`'un tuhaf, olumsuz adı iş yapıyormuş — **kontrol işareti tool'a
benzememeli, kostüm kadar isim de kostümdür.** `grammar.py`'nin docstring'i JSON kostümü
için bunu zaten söylüyordu; ad için de geçerliymiş.

Dolayısıyla yapısal teşhis duruyor: tek işaretli bir dünyada "tool gerekiyor ama alanım
eksik" ifade edilemiyor. Yolu **ikinci bir işaret** (`ask_user`) — ama bir tool olarak
değil: `no_tool`'un defterden dışlanma gerekçesi (Effect sınıfı + §10.2'nin `TANINMAYAN`
satırı dört hücrede RED, yani tanınmayan birine soru sorulamazdı) `ask_user` için birebir
geçerli. Bu artık P25'i geri almak değil yeni bir tasarım ve §19.2'den sonra.

Ölçümler ana ağaçta değil bir kopyada koşuldu; `src/` ve `config/` değişmedi. **Yama bayatladı:**
P26/P27'den sonra `git apply` on dört dosyanın dördünde çakışıyor; kaynak tarafı temiz
uyguluyor, `evals` borulaması elle taşınıyor.

- **Sıradaki:** §19.2 (model). Rol metni ona bağlı — bugün aynı metnin 27B dense ile 35B
  MoE'de zıt sonuç verdiği ölçüldü.

---

## P28 — Katalog genişlemesi: bellek yazma ve makine denetimi ✅ TAMAMLANDI (2026-08-16)

**Bağımlılık:** yok. **Engelleyen açık madde:** yok — §9.2'nin kataloğunu genişletiyor,
§19'un hiçbir maddesini kapatmıyor.

Sahibin seçimi: eksik kapılar + ses/medya + uygulama/pencere, `ArgType.ENUM` dâhil, hepsi
bir seferde ve sonunda ölçüm. Güç/parlaklık/gece ışığı dışarıda bırakıldı.

**Eklenenler (5 tool + 1 argüman tipi):** `fact_save`, `volume`, `media_control`,
`app_launch`, `window_action`, `window_close`. Katalog 16 → 22, katalog metni 783 → 1069
token (sayaçtan), bağlamın %6.5'i.

**Reddedilen üç tool ve sebebi.** İlk listede `note_list`, `contact_list`,
`contact_update` vardı; üçü de yazılmadı çünkü üçü de zaten vardı — `note_search`,
`contact_get` ve `contact_save` bu işleri isteğe bağlı argümanlarla yapıyor. Liste depo
metodlarına bakılarak çıkarılmıştı, tool gövdelerine değil. **Ders: kataloğu genişletmeden
önce gövdeler okunur;** örtüşen tool'un maliyeti token değil, ölçülmüş biçimde kırılgan olan
tool seçimi.

**`ArgType.ENUM`.** Seçenekler gramerde harfi harfine alternatif — geçersiz seçenek
üretilemez, tool adlarındaki güvencenin argüman tarafındaki eşi (ve aynı §17.1 uyarısıyla:
bu gramerin başarısı, modelin değil). Kural tool'a *ve* alana özel; JSON'da tırnaklar
kuralın içinde, yoksa kısıt kaybolur. `usage()` seçenekleri yazıyor, `<enum>` değil.

**Ölçülmüş düzeltme: izin listesi görünür olmak zorunda.** `app_launch` önce
`wake_on_lan`'ın kalıbıyla yazıldı (STRING + gövdede doğrulama). Gerçek modelde "tarayıcıyı
aç" *hiç denenmeden* "tanımlı bir tarayıcım yok" cevabını aldı: katalogda hangi adların
tanımlı olduğu yazmıyordu. Adlar `ENUM` seçeneği olarak yapılandırmadan gelince model dördü
de sayabildi ve listede olmayanı gerekçesiyle reddetti. Uygulama tanımlı değilse tool
kataloğa hiç girmiyor. `builtin_registry()` bu yüzden artık `config` alıyor — `evals` de
geçiriyor, yoksa üretimin kurmadığı bir katalog ölçülürdü (P27'nin dersi).

**Değişmez 8 hiç esnetilmedi:** argv ile `exec`, kabuk yok, ve modelden gelen hiçbir değer
argv'ye girmiyor — pencere eylemi koddaki tabloyu, uygulama adı yapılandırmayı indeksliyor.
Etki sınıfı tool başına olduğu için pencere kapatma ayrı bir tool (GERİ_ALINAMAZ, onay).

Mekanizma `adapters/desktop.py`'de: Wayland+KDE, `wpctl` + MPRIS + KWin kısayolları.
"Şu uygulamaya geç" ve pencere listesi bilerek yok (KWin scripting gerekir).

**Ölçüm: gerileme yok.** Üretim öneği, cli/json, tabana göre (`docs/faz7-rol.md`, aynı
model ve aynı rol metni): altın 98/98 → 98/100, halüsinasyon 93/93 → 93/93, bellek 82/82 →
88/88, kontrol 100/100 → 94/94. Oynayan kümelerde tek bir senaryo değişiyor ve aralıklar
çakışıyor.

**`kontrol`'ün düşüşü senaryonun bayatlaması.** İki biçimde de aynı senaryo: `kon-08`,
"Sesini biraz kısabilir misin?" — küme onu `TOOL_GEREKMEZ` sayıyor çünkü yazıldığında ses
tool'u yoktu. Model doğru davranıyor, beklenti yanlış. **Senaryo değiştirilmedi** (P27'nin
altın kümedeki bulgusunda olduğu gibi): kümeyi sonuca uydurmak ölçümü kendi varsayımını
doğrulayan bir teste çevirir. Beklentiyi güncellemek sahibin kararı.

**Yeni tool'ların kendileri ölçülmedi** — hiçbir kümede senaryoları yok. Ölçülen soru
"katalog büyüdü, eski davranış bozuldu mu"; cevap hayır. Elle iki uydurulmuş eylem görüldü
(`app_launch`, `fact_save`: çağrı yapmadan "yaptım"), bu bilinen `halusinasyon` sınıfı.

Ayrıntı ve ölçüm: `docs/faz8-tool.md`, `docs/faz8-tool-olcum.md`.

---

## Bundan sonrası

§18'in fazları, iki sapmayla:

- **Faz 2 (model ölçümü)** — A3 kapandığı için dört modelin VRAM'i ölçülür, üç değil.
  Ayrıca: her LLM adayı `evals/` ile de koşar; §19.1'in kararı bir modele dayanıyor ve
  biçim farkı başka bir modelde tersine dönerse orada yeniden verilir.
  C1 (Türkçe özel adların İngilizce TTS'ten geçmesi) burada karara bağlanır. §19.4'ün
  gecikme hedefi burada sayı kazanır ve regresyon testine bağlanır.
- **Faz 3 (ajan ve tool'lar)** — P6/P7 çoğunu öne aldığı için burada kalan: düzeltme
  döngüsü, bloke tool gövdeleri (§19.7/8/9 cevaplanınca), katalog boyutunun gerçek modelde
  ölçülmesi.
- **Faz 4 (kimlik, yetki, onay)** — §19.3 eşikleri burada ölçülüyor. §19.14 kapandı:
  sahip ataması bir kurulum betiği; betik de bu fazın teslimatlarından biri.
- **Faz 5 (streaming ve söz kesme)** — **istemci buraya taşınır** (§18 onu Faz 7'ye
  koyuyor ama Faz 5'in bitti kriteri istemciyi gerektiriyor). Önce başsız/asgari bir
  istemci: mikrofon, endpointing, ses çalma, AEC. GUI Faz 7'de kalır. AEC'nin bu fazın en
  büyük kalemi olduğu baştan kabul edilir.
- **Faz 6 (bellek ve zamanlanmış görevler)** — ✅ P19 ve P20'de kapandı. B4 de kapandı:
  arka plan LLM işleri turun kuyruğa girmesiyle preempt ediliyor ve yarım sonuç yazılmıyor.
- **Faz 7 (arayüz ve işletim)** — §19.11 kapandı (PySide6). P22 fazın **metin çekirdeğini**
  öne aldı: sahibin ses tarafı beklerken yazışarak kullanma niyeti buna bağlıydı. Burada
  kalan: durum göstergesi, bekleyen kişi yönetimi, servis yönetimi.

### Servis yönetimi: birim dosyası, kalıcı hata ayrımı ve süreç kilidi (2026-08-15)

Faz 7'nin "servis yönetimi ve otomatik toparlanma" kalemi. Kod tarafı küçüktü; iş üç
kararda:

**1. `llama-server` birime girmiyor (sahibin kararı).** Model elle açılıyor ve ölçüm
koşarken değiştiriliyor; bir `Requires=` yanlış bir bağımlılık kurardı. Kapalıyken adaptör
zaten hata yükseltiyor ve tur başarısız oluyor — süreç ölmüyor.

**2. İki hata sınıfı, iki çıkış kodu.** `EXIT_CONFIG` (78, `sysexits.h`'nin `EX_CONFIG`'i):
rol dosyası yok, yapılandırma bozuk, veritabanı başka bir süreçte açık. Yeniden başlatmak
bunları düzeltmez, yalnızca hatayı bir döngünün içine gömer ve kimse görmez — birim dosyası
`RestartPreventExitStatus=78` ile duruyor. Geri kalan her şey 1: LLM kapalı, port meşgul,
disk anlık dolu. Ayrıca `load()` artık `try` bloğunun **içinde**; önce dışındaydı, yani
bozuk yapılandırma ham traceback olarak düşüyordu.

**Bilinen boşluk, kapatılmadı ve saklanmadı:** yanlış yazılmış bir veritabanı yolu
`sqlite3.OperationalError` atıyor, yani kalıcı sayılmıyor. İstisna türü kalıcı yolu geçici
disk hatasından ayırmıyor ve ayrımı uydurmak yanlış olurdu. Sonsuz döngü de değil —
systemd'nin `StartLimitBurst`'ü birimi kısa sürede `failed`'a düşürüyor.

**3. Kural 1 artık bir yorum değil, bir kilit.** `Database` dosyanın yanındaki `.lock`
üzerinde süreç ömrü boyunca `flock` tutuyor. Sınıfın docstring'i "süreç başına bir tane"
diyordu ama bunu sağlayan hiçbir şey yoktu: servis koşarken elle `python -m mayen` yazmak
iki süreci aynı dosyaya yazar hâle getirirdi. Kilit **veritabanı dosyasında değil** ayrı
bir dosyada — SQLite'ın kendi kilitleriyle aynı dosyada oturmak kimin neyi tuttuğunu
okunmaz yapardı. Kilit bağlantıdan **sonra** alınıyor: önce alınsaydı yanlış yol hatası
kilit dosyasının hatası olarak çıkardı (`test_db.py` bunu zaten tutuyordu) — ve açılamayan
bir bağlantı kilidi tutmuyor, yoksa yolu düzeltmek yetmez süreç yeniden başlatılırdı.

Birim dosyası `config/mayen.service` (kullanıcı birimi). Açılışta koşması için
`systemctl --user enable --now mayen` ve `loginctl enable-linger` gerekiyor.

**Kök dizinde `baslat`:** sunucuyu ve Qt penceresini birlikte açan kabuk betiği —
geliştirirken elle açıp kapatmak için, kalıcı kurulum yine birim dosyası. Sunucu zaten
koşuyorsa **ikincisini açmıyor**, yalnızca pencereyi açıyor ve bulduğu sunucuya
dokunmuyor; kendi başlattığını pencere kapanınca kapatıyor.

İki şey denendi ve çalışmadı, ikisi de betikte yorum olarak duruyor: `uv run` bir
sarmalayıcı ve TERM'i altındaki Python'a geçirmiyor (yalnız onu öldürmek sunucuyu ayakta
bırakıyor), `setsid` ile grup kapatmak da işe yaramıyor çünkü setsid grup lideriyken
çatallanıyor ve `$!` gerçek grubun lideri olmuyor. Kapatma bu yüzden süreç ağacını
yaprağından köküne dolaşıyor.

**Bilinen sınır, kapatılmadı:** betik `SIGKILL` alırsa `trap` çalışmaz ve sunucu arkada
kalır. Arıza değil — bir dahaki çalıştırma onu buluyor ve yalnızca pencereyi açıyor.
`.gitignore` kilit dosyasını da alıyor (`*.db.lock`).

### GUI: tool bildirimi ve Esc ile iptal (2026-08-15)

Faz 7'nin kalanından iki kalem. Seçilme gerekçesi eleme: sahip ataması (§19.14) ve bekleyen
kişi yönetimi kâğıt üstünde açık görünüyordu ama **ikisi de sese bağlı** — kademe atamak o
kişiyi bir ses profiline bağlamak demek, sahiplik de kabuktan veriliyor fakat **ses ile
doğrulanıyor**. STT ertelendiği sürece ikisi de yarım kalırdı (sahibin düzeltmesi).

- **`tool_running` artık gösteriliyor.** Gövdesi `return None` idi: metin istemcisi
  `[tool] weather` yazarken GUI kullanıcısı tool koşarken donmuş bir pencere görüyordu.
- **Esc turu kesiyor (Değişmez 12).** `Client.interrupt()` protokolde vardı ve bu yüzey onu
  hiç çağırmıyordu — yani "her tur her aşamada iptal edilebilir" bir yüzeyde geçerli
  değildi. Esc **yazılanı silmiyor**: iptal edilen şey tur, kullanıcının cümlesi değil.
  Bağlantı yokken sessiz kalmıyor (Kural 13).

**Yapılmayan, bilerek:** durum etiketi hâlâ `State`'in kendi değerini basıyor. `gui.py`'nin
docstring'i bunun gerekçesini zaten yazmış — ikinci bir Türkçe sözlük dokümanla kod arasında
sürüklenirdi. "Durum göstergesi" kalemi bu yüzden bir çeviri katmanına çevrilmedi.

`keyPressEvent` için satır içi `# noqa: N802`: ad Qt'nin. Genel yapılandırmaya kural eklemek
tek bir metot için fazla geniş olurdu; depodaki tek örnek (`portaudio.py`) de satır içi.

### §19.2'nin LLM yarısı kapandı, §19.1 onun üstüne yeniden okundu (2026-08-15)

**LLM: `Qwen3.8-27B-IQ4_XS`. Sahibin kararı, ölçüm sonucu değil.** Gerekçe sahibin: kamuya
açık ölçütlerde 3.8 kuşağı 3.6'nın önünde ve elde 3.8'den tek aday bu (3.8-35B henüz
yayınlanmadı), yani "hangisi" sorusunun cevap kümesi tek elemanlı — kuşak A/B'si karar
sorusu değil merak sorusu olurdu.

**Kararın sınırı da kayıtlı:** kamuya açık ölçütler bizim ölçtüğümüz şeyi ölçmüyor ve
"büyük olan daha iyidir"in yanlış çıktığı bir örnek aynı gün görüldü (35B-A3B, MoE). Risk
sahip tarafından kabul edildi. **Bu madde ölçümle değil kararla kapanıyordu** ve öyle
yazıldı — 10 Ağustos'ta ölçümün yanına düşülen bir çıkarımın karara dönüşmesi tam olarak
buradaki hataydı.

**§19.1 yeniden okundu, damgalanmadı.** Dayanağı "model sabit, o modelde CLI önde" idi;
model sabitlenince dayanak geri geldi, ama sayılar yeniden bakıldığında gerekçe incelmiş:
dört kümede doğruluk iki biçimi **ayırmıyor** (aralıklar dördünde de çakışıyor), ayıran şey
token ve tamamlanma bedeli — ve **Faz 0'ın belirleyici sayısı olan ilk ses artık berabere**
(0.22'ye 0.22). CLI kalıyor, marjı Faz 0'dakinden dar.

**Açık kalan:** STT ve TTS (sahibin ertelemesi). Ses girişi bu yüzden çalışmıyor; §19.4'ün
gecikme hedefi ve §19.10 onlarla birlikte bekliyor.

---

## P29 — Yerel tool çağrı biçimi ✅ TAMAMLANDI (2026-08-16)

**Bağımlılık:** P27 (üretim öneği), Faz B/1 (tool sonucunun geçmişte saklanması).
**Kapattığı açık madde:** §19.1, sahibin kararıyla.

### Neyi çözdü

Sahibin elle koşusunda asistan bir çağrıyı **taklit etti**: düz metin dalına
kilitlenmişken `[tool] date_time` yazdı, hiçbir şey koşmadı ve cümle sesli okundu. Log'da
o turun `tool adımı` satırı yok; gramerde `<` zaten yasaktı, yani gördüğümüz şey bir çağrı
değil, bir çağrının kılığıydı.

`<` yasağı bir gün önce, aynı arızanın `<tool> date_time` biçimi için konmuştu.
**Yasak davranışı kaldırmadı, kılığını değiştirdi — ve kötüleştirdi:** eskiden ortaya
bozuk ama gerçek bir çağrı çıkma ihtimali vardı, şimdi hiçbir şey koşmuyor ve uydurma
kullanıcıya okunuyor.

Altta yatan şey tasarımsal ve §6/C3'e bakıyor: dal ilk token'da seçildiği için model bir
üretimde ya konuşabiliyor ya çağırabiliyor. Burada ikisini birden istiyordu — "anladım,
kuruyorum; ama önce saati almam lazım".

### Ne yapıldı

- `tools/schema.py` — defterden JSON şema, `grammar.py`'nin üçüncü kardeşi. Kaynak tek
  (§9.1): şema `usage()` gibi imzadan türetiliyor. `ENUM` → `enum`.
- `CallFormat.YEREL` + `agent/calls.py:from_native`. Şema tipli değer üretiyor,
  `Tool.validate` metin bekliyor: **esneyen taraf çevirici oldu**, doğrulama değil.
- `adapters/llm.py`: `NativeCall`, `PromptMessage.tool_calls`, `LLMClient.stream_native`.
  Sahtesi de var — bütün tur akışı GPU'suz test edilebilir kalıyor (§4).
- `agent/loop.py`: yerel dalda metin **ve** çağrı aynı üretimden akıyor; `_produce` biçime
  bakan tek yer.
- Migration 002: `messages.tool_calls`. Çağrı satırın yanında saklanıyor.
- `evals/`: `--yerel` kolu (`session.py`) ve üçüncü biçim (`runner.py`, yalnızca üretim
  öneğiyle — ölçüm öneği katalogu sistem mesajına yazıyor ve ikisi defterin iki kopyası
  olurdu).

### Ölçüm ve bir ölçüm hatası

Kabul kapısı 12/15 → **14/15**, ilk atlanan tur 23 → 28; aralıklar çakışıyor (Kural 14),
ama çevrilen iki tur Faz B'den beri açıkta duran tek arıza sınıfı ("kullanıcı ısrar ediyor,
model zaten yaptım diyor"). Dört küme: altın %98 → %92, kontrol %89 → %94, halüsinasyon
%93 → %100, bellek %88 → %82, argüman doğruluğu %89 → %94. Rapor `docs/faz-b-yerel.md`.

**İlk koşu kirlendi ve dersi eskisinin aynısıydı.** Geçmişteki çağrı `assistant` **metni**
olarak yazılıyordu; model onuncu turdan sonra biçimi kopyaladı ve dört turda sesli cevap
olarak `{"name": "volume", "arguments": {...}}` üretti — 6/15. Model geçmişte kendi
ürettiği biçimi görmeli.

### Bedeli: dil kuralının yeri

Faz 7'nin kaldıracı tersine döndü. Katalogu artık şablon ekliyor ve `tools` bloğunu bizim
sistem mesajımızın **arkasına** koyuyor, yani "sistem promptunun sonu" öneğin sonu olmaktan
çıktı; kural orada bırakıldığında elle koşuda altı turun altısı Türkçe çıktı. Kural bağlam
bloğunun sonuna taşındı — Faz 7'nin yasağıyla çakışmıyor, çünkü bağlam bloğu **zaten**
değişken ve zaten orada; yasaklanan şey sabit kuyruktan sonra yeni bir mesaj açmaktı
(22 → 1631 önek jetonu). Taşındıktan sonra altı/altı İngilizce, `kontrol` %78 → %94.

### Reddedilenler

- **Rol metnini yeniden yazmak.** Altındaki dört hata "çağırmak yerine sordu" sınıfı;
  metni onlara göre düzeltmek elli senaryoya fitting olurdu (`docs/faz6-27b-rol3.md`).
- **Metin biçimlerini silmek.** Model değişirse yeniden ölçülecek; seçen satır tek.
- **Yerel biçimde düzeltme döngüsü.** Düzeltilecek sözdizimi hatası taşımanın altında
  kalıyor; kalan tek hata sınıfı defter doğrulaması ve o zaten geri besleniyor.

---

## Faz C — Model taraması: LFM2.5 ve 35B-A3B ölçüldü, üretim değişmedi (2026-08-17)

Tam rapor `docs/faz-c-model-taramasi.md`, ham raporlar `docs/faz-c/`. **Karar üretmedi** —
üretim `Qwen3.8-27B-IQ4_XS` + yerel biçim + Kokoro(CPU) olarak duruyor.

Tetikleyen: `llama-server` kartı doldurduğu için Kokoro CPU'da. Daha küçük ya da offload
edilebilir bir LLM ona GPU'da yer açardı.

- **Kokoro GPU'da ölçüldü** (`main.py:63`'ün istediği ölçüm): tepe **1.1 GB**, ilk ses
  **0.33 → 0.09 s**, 35B'nin yanında 2.4 GB boş kalıyor. **Taşınmadı:** kazanç 0.24 s ve
  §19.4 bilerek sayısız.
- **LFM2.5-2.6B elendi.** Metin biçimlerinde **hiç çağrı üretmiyor** (altın 30%, çağrı
  gerektiren her eksende 0%); yerelde 76/72/87/65 — dört kümede de 27B'nin altında.
  Akıl yürütmesi kapatılamıyor: şablon `<think>`'i koşulsuz açıyor, `enable_thinking`
  diye bir değişken yok.
- **35B-A3B: iki alet ters yönde konuşuyor, ve ders bu.** `halusinasyon` kümesi 33%
  (iki koşuda birebir aynı, aynı dokuz senaryo), **kabul kapısı 80%** — 27B'nin 80–87%'siyle
  başa baş, kaçırdığı turlar aynı "kullanıcı ısrar ediyor" sınıfı. Fark, kümenin
  fikstürlerinin `tool=None` olması: tek turluk kümeler 2026-08-16 öncesinin geçmişini
  ölçüyor (`evals/runner.py:226`, bilerek). Okuma: **sağlıklı durumda iki model ayırt
  edilemiyor; bir kez uydurduktan sonra 27B toparlanıyor, 35B sürdürüyor.**
- **Yeni bulgu — dil kuralı modele bağımlı bir kaldıraç.** Aynı dosya 27B'de üç kümede
  iyileştiriyor (halüsinasyon 87→100 dahil), 35B'de üçünde kötüleştiriyor. Rol metni için
  kayıtlı dersin dil kuralında da geçerli olduğunun ilk ölçümü. Yan doğrulama: kural bağlam
  bloğunda dururken TTFT kıpırdamadı, Faz 7'nin 22→1631 felaketi tekrarlamadı (P29 lehine).

### Düzeltilenler

- `main.py`: `_system()` artık `_real_llm()`'den **önce** çağrılıyor. Kalıcı yapılandırma
  hatası geçici ağ hatasının arkasına saklanıyordu ve birim dosyası onu sonsuz yeniden
  başlatmaya sokuyordu; `tests/test_main.py` bu yüzden düşüyordu.
- `evals`: `--ornekleme {greedy,sunucu}` (varsayılan `greedy`, eski sayılarla kıyaslanabilirlik
  için); `--bicim` (varsayılan `main.py:CALL_FORMAT`) — üç biçimi birden koşmak her ölçümü
  iki ölü yol uğruna üç katına çıkarıyordu. **Metin biçimleri silinmedi**, sahibin kararı:
  "dursun bir kenarda ama aktif olmasın".
- `evals/session.py`: `--yerel` → `--metin-kolu`, varsayılan tersine döndü. Kusur şuydu:
  `CALL_FORMAT` yerelken metin kolu `parse()`'a yerel biçim veriyor (`calls.py:145`, "kodun
  hatası"), yani **kol bir ölçüm değil** — ilk okumada 1/15 diye rapor edildi. Rapor iki kolu
  da "yerel" etiketliyordu; artık `metin(yerel)`.
- **Ders:** §19.1 kapandığında ölü yollar sessizce bozuldu ve bozuk hâlleriyle her koşuda
  ölçülmeye devam ettiler. Üç biçimi canlı tutmanın maliyeti zaman değil, yanlış sayıydı.

### Sahibin kasıtlı kararsızlıkları (kayda geçti)

- **§19.4'e bilerek sayı konmuyor:** bir eşik, 100 ms kovalama yükümlülüğü yaratır; MVP'de
  istenen bu değil. **Bu maddeye sayı önermek yanlıştır**, ölçüp raporlamak doğrudur.
- **STT bilerek erteleniyor:** şimdilik ihtiyaç yok ve donanım (GPU/VRAM/model) değişebilir;
  değişecek bir şeye model kararı bağlanmıyor.

Bunlar "ölçüm eksiği" değil kapsam kararı. İkisi de bu turda sayı önerisiyle karşılandı ve
gerekçeyle reddedildi.

---

## §19 → paket bağımlılık haritası

| Açık madde | Neyi engelliyor |
|---|---|
| 1. Çağrı biçimi | ✅ Kapandı — **yerel biçim** (2026-08-16, sahibin kararı; P29). Karar doğrulukla verilmedi: metin biçimlerinde model bir üretimde ya konuşabiliyor ya çağırabiliyor ve ikisini birden istediğinde çağrıyı taklit ediyor. Aralıklar dört kümede de çakışıyor |
| 2. Model seçimleri | **LLM ✅ kapandı: `Qwen3.8-27B-IQ4_XS`** — sahibin kararı (2026-08-15), ölçüm sonucu değil; gerekçe kamuya açık ölçütlerde 3.8 > 3.6 ve elde 3.8'den tek aday. Rol metni zaten bu modelde yazılıp benimsendi. **STT/TTS açık** (sahibin ertelemesi) — §19.4 ve §19.10 onlarla bekliyor; ses girişi bu yüzden çalışmıyor |
| 3. Konuşmacı eşikleri | Yalnızca Faz 4. P21'in `MAYEN_ASSUME_OWNER` kapısı eşikleri beklemeden tool akışını denenebilir kılıyor; eşiklerin yerine geçmiyor |
| 4. Gecikme hedefi | Regresyon testinin **eşiğini**, kodunu değil |
| 5. Ses formatı | Hiçbir şey — çerçevede kodek alanı açık bırakılıyor |
| 6. Wake word | Yalnızca istemci (Faz 5) |
| 7. Hava servisi | ✅ Kapandı — OpenWeatherMap |
| 8. Ders verisi | ✅ Kapandı — depoda dosya |
| 9. WOL hedefleri | ✅ Kapandı — yapılandırma dosyası |
| 10. TTS ses karakteri | Yalnızca Faz 2 |
| 11. Qt bağlayıcısı | ✅ Kapandı — PySide6 (P22), opsiyonel `gui` ekstrası |
| 12. Yedekleme ayarları | Hiçbir şey — yapılandırma değeri |
| 13. Kaçırılmış görev toleransı | Hiçbir şey — yapılandırma değeri (P19: `MAYEN_MISSED_TASK_TOLERANCE_MINUTES`) |
| 14. Sahip ataması | ✅ Kapandı — kurulum betiği (Faz 4 teslimatı) |
| 15. Türkçe içerik + İngilizce TTS | Yalnızca Faz 2 |

**P1'den P8'e kadar olan işin tamamı artık §19'dan hiçbir şeyle bloke değil.** Kalan açık
maddelerin hepsi Faz 2 ve sonrasına ait.
