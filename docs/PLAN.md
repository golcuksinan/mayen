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

## P3 — Sözleşmeler: protokol, adaptör arayüzleri, fake'ler

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
yazılıp geri okunabiliyor; el sıkışma sürüm uyuşmazlığı testi yeşil.

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
onay okunurken söz kesme.

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
dört etki sınıfı = on altı hücre, hepsi ayrı ayrı.

---

## P6 — Tool kayıt defteri, katalog, gramer

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
testi yeşil; bloke olmayan tool'ların testleri yeşil.

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

---

## P8 — Tur akışı ve ajan döngüsü (Faz 1'in bitişi)

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

---

## Bundan sonrası

§18'in fazları, iki sapmayla:

- **Faz 2 (model ölçümü)** — A3 kapandığı için dört modelin VRAM'i ölçülür, üç değil.
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
- **Faz 6 (bellek ve zamanlanmış görevler)** — B4 burada kapatılır: arka plan LLM işleri
  iptal jetonu taşır ve tur başlar başlamaz preempt edilir.
- **Faz 7 (arayüz ve işletim)** — §19.11 Qt bağlayıcısı burada gerekiyor.

---

## §19 → paket bağımlılık haritası

| Açık madde | Neyi engelliyor |
|---|---|
| 1. Çağrı biçimi | Hiçbir şey — adaptör zaten iki biçimi de yazdırıyor, P7 seçiyor |
| 2. Model seçimleri | Yalnızca Faz 2 |
| 3. Konuşmacı eşikleri | Yalnızca Faz 4 |
| 4. Gecikme hedefi | Regresyon testinin **eşiğini**, kodunu değil |
| 5. Ses formatı | Hiçbir şey — çerçevede kodek alanı açık bırakılıyor |
| 6. Wake word | Yalnızca istemci (Faz 5) |
| 7. Hava servisi | ✅ Kapandı — OpenWeatherMap |
| 8. Ders verisi | ✅ Kapandı — depoda dosya |
| 9. WOL hedefleri | ✅ Kapandı — yapılandırma dosyası |
| 10. TTS ses karakteri | Yalnızca Faz 2 |
| 11. Qt bağlayıcısı | Yalnızca Faz 7 |
| 12. Yedekleme ayarları | Hiçbir şey — yapılandırma değeri |
| 13. Kaçırılmış görev toleransı | Hiçbir şey — yapılandırma değeri |
| 14. Sahip ataması | ✅ Kapandı — kurulum betiği (Faz 4 teslimatı) |
| 15. Türkçe içerik + İngilizce TTS | Yalnızca Faz 2 |

**P1'den P8'e kadar olan işin tamamı artık §19'dan hiçbir şeyle bloke değil.** Kalan açık
maddelerin hepsi Faz 2 ve sonrasına ait.
