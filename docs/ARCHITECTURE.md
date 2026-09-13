# Mayen — Mimari

Sesli asistan. Türkçe konuşma girer, İngilizce konuşma çıkar. Tek makinede çalışır,
yerel modeller kullanır, kendi verisini kendi tutar.

Bu doküman uygulamanın temelidir. İçindeki her karar açıkça verilmiştir; verilmemiş
olanlar §19'da **AÇIK** olarak işaretlidir. Açık bir madde, cevaplanmadan uygulanmaz —
yerine varsayım konmaz.

---

## 1. Kapsam

**Kullanıcı:** Tek sahip. Ek olarak, sistemle konuşabilen ama sınırlı yetkili başka
kişiler olabilir.

**Cihaz:** Masaüstü (native GUI) birincil istemci. Telefon istemcisi ileride
eklenebilir; protokol ve oturum modeli bunu dışlamayacak şekilde tasarlanır, ancak
telefon kodu bu kapsamda yazılmaz.

**Yetenekler (ilk sürüm):** hava durumu, tarih/saat, kişiler, notlar, ders programı,
sistem metrikleri, Wake-on-LAN, hatırlatıcı/zamanlanmış görev.

**Kapsam dışı:** Çoklu kullanıcı hesap sistemi, uzaktan/internet üzerinden erişim,
bulut model kullanımı.

---

## 2. Kararlar

| Konu | Karar |
|---|---|
| Donanım | Tek makine, tek GPU (16 GB) |
| Ayrılabilirlik | Kod ileride iki makineye bölünebilecek şekilde sınırlandırılır; ilk sürümde bölünmez |
| Uygulama dili | Python (asyncio) |
| Model yerleşimi | LLM, STT, TTS, konuşmacı tanıma ayrı süreçlerde; uygulama süreci model yüklemez |
| Süreçler arası | HTTP (akış destekli) |
| LLM | Yerel GPU |
| STT / TTS | Yerel |
| Dil | Giriş Türkçe, çıkış İngilizce |
| Aktivasyon | Wake word, sürekli dinleme; istemci sorumluluğunda |
| Gecikme | Streaming birinci sınıf hedef; ilk sürümde barge-in dahil |
| Kimlik | Ses profiliyle konuşmacı tanıma; tek doğrulama kanalı |
| Yetki | 4 kademe: sahip / kayıtlı kişi / bekleyen / tanınmayan |
| Yeni kişi | Otomatik kaydedilir, `bekleyen` olarak işaretlenir; yetkisi kapalı |
| Onay | Geri alınamaz işlemlerde sesli onay adımı zorunlu |
| Oturum | Oturum sınırı yok; tek sürekli konuşma akışı |
| Eşzamanlılık | Tüm sistemde aynı anda tek tur; ikinci cihazın segmenti sıraya girer |
| Özetleme | Açılışta; ayrıca bağlam kırpması olduysa boştaki ilk fırsatta |
| Bağlam taşması | Sert kırpma — kırpılan mesaj silinmez, özetlenene kadar bağlam dışında kalır |
| Bellek | Kalıcı, ortak havuz; her kayıt kimin söylediğiyle etiketli |
| Veri | SQLite + otomatik yedek |
| İşletim | Elle açılır/kapanır; açıkken sürekli ayakta, çökerse yeniden başlar |
| Hata | Hem sesli hem arayüzde bildirim + otomatik toparlanma |
| Tool çağırma biçimi | **Yerel** — modelin kendi şablonu; 2026-08-16'da seçildi (§19.1) |
| Çıktı kısıtı | Yerel biçimde `tools` şeması; metin biçimlerinde GBNF grameri |
| İstemci ses formatı | **Ölçümle belirlenecek** (PCM vs Opus) |
| Model seçimleri | **Ölçümle belirlenecek** |

---

## 3. Topoloji

```
┌──────────────────────────────────────────────────────────────────┐
│ Tek makine                                                       │
│                                                                  │
│  ┌────────────────┐        ┌──────────────────────────────────┐  │
│  │ İstemci (GUI)  │◄──WS──►│  mayen-core                      │  │
│  │ ─────────────  │        │  ──────────────────────────────  │  │
│  │ wake word      │        │  oturum · tur · ajan · tool'lar  │  │
│  │ mikrofon       │        │  politika · bellek · zamanlayıcı │  │
│  │ ses çalma      │        │  SQLite (tek sahip)              │  │
│  │ durum ekranı   │        └─┬────────┬────────┬──────────┬───┘  │
│  └────────────────┘          │HTTP    │HTTP    │HTTP      │HTTP  │
│                              ▼        ▼        ▼          ▼      │
│                          ┌───────┐┌───────┐┌───────┐┌───────────┐│
│                          │  LLM  ││  STT  ││  TTS  ││ KONUŞMACI ││
│                          │  GPU  ││  GPU  ││  GPU  ││    CPU    ││
│                          └───────┘└───────┘└───────┘└───────────┘│
└──────────────────────────────────────────────────────────────────┘
```

**Kural:** `mayen-core` model kodu içermez, model ağırlığı yüklemez. Modeller
kendi süreçlerinde yaşar ve HTTP arkasındadır. Bu, üç şeyi aynı anda verir:

- Bir model çökerse uygulama ayakta kalır ve o modeli yeniden başlatabilir.
- Model değiştirmek uygulamayı yeniden başlatmayı gerektirmez.
- İleride bir modeli başka makineye taşımak yalnızca adres değişikliğidir.

**Konuşmacı tanıma da bu kuralın istisnası değildir.** O da kendi sürecinde ve HTTP
arkasındadır, ama **CPU'da** çalışır. Yukarıdaki üç gerekçe onun için de aynen geçerlidir.
Gömü çıkarma GPU gerektirmeyecek kadar ucuzdur ve §6'da zaten STT ile paralel koştuğu için
kritik yolda değildir; karşılığında 16 GB VRAM bütçesi tamamen LLM/STT/TTS üçlüsüne kalır.
Yani sistemde dört model süreci vardır, üç değil.

**Kural:** SQLite dosyasının tek sahibi `mayen-core`'dur. Başka hiçbir süreç dosyayı
açmaz. Veriye ihtiyacı olan her şey core üzerinden geçer.

---

## 4. Katmanlar

```
transport/   WebSocket, çerçeve biçimi, protokol sürümü, backpressure
session/     Oturum aktörü ve durum makinesi
turn/        Tek turun akışı: ses segmenti → metin → ajan → ses
agent/       LLM döngüsü, tool seçimi, yanıt üretimi
tools/       Tool kayıt defteri; tool başına tek modül
policy/      Kimlik → yetki. Onay akışı. Tek yetkilendirme noktası.
memory/      Bağlam penceresi, özetleme, kalıcı olgu deposu
adapters/    llm, stt, tts, speaker, wakeword(istemci tarafı sözleşmesi) — hepsi arayüz arkasında
data/        Repository'ler, şema, migration, yedekleme
scheduler/   Zamanlanmış görevler ve proaktif ses kanalı
obs/         Trace, metrik, olay kaydı, replay
```

Bağımlılık tek yönlüdür: `transport → session → turn → agent → tools → adapters`.
Alt katman üst katmanı import etmez. Bir alt katmanın üst katmana ihtiyaç duyması,
sınırın yanlış çizildiğinin işaretidir; import eklenerek değil, sınır düzeltilerek
çözülür.

**Ports & adapters:** LLM, STT, TTS ve konuşmacı tanıma birer arayüz (`Protocol`)
arkasındadır. Her birinin sahte (fake) uygulaması vardır. Bu sayede tüm tur akışı,
politika ve ajan mantığı GPU'suz ve saniyeler içinde test edilebilir.

---

## 5. Oturum ve Durum Makinesi

Oturumun bitişi yoktur. Sistem açık olduğu sürece tek bir sürekli konuşma akışı vardır.
"Yeni oturum" kavramı yerine **açılış** kavramı vardır: uygulama her başlatıldığında
bir açılış kaydı oluşur.

Her bağlı cihaz için bir aktör görevi çalışır ve her aktörün kendi mesaj kuyruğu vardır.
Ama **aktif tur tutamacı globaldir**, aktör başına değil (aşağıya bakınız).

**Sunucunun durumları istemcinin durumları değildir.** §7 gereği konuşma başı/sonu tespiti
istemcide yapılır ve sunucuya yalnızca tamamlanmış segmentler gider. Dolayısıyla sunucuda
`DİNLİYOR` diye bir durum yoktur: sunucu segment gelene kadar `IDLE`'dadır ve segment
geldiğinde doğrudan `ÇÖZÜMLÜYOR`'a geçer. `DİNLİYOR` istemcinin durumudur; sunucu onu
yalnızca söz kesme sinyalinden ve durum bildiriminden bilir (§13).

Sunucunun geçiş tablosu:

| Durum | Olay | Sonraki durum |
|---|---|---|
| `IDLE` | segment geldi | `ÇÖZÜMLÜYOR` |
| `ÇÖZÜMLÜYOR` | STT ve konuşmacı tanıma bitti | `DÜŞÜNÜYOR` |
| `DÜŞÜNÜYOR` | ilk ses parçası hazır | `KONUŞUYOR` |
| `DÜŞÜNÜYOR` | onay gerekli | `ONAY_BEKLİYOR` |
| `DÜŞÜNÜYOR` | ses profili kaydı gerekli | `KAYIT` |
| `DÜŞÜNÜYOR` | söz kesme sinyali | `IDLE` — tur iptal; üretim sürerken iptal en çok istenen andır (Kural 12) |
| `DÜŞÜNÜYOR` | yanıt boş | `IDLE` — hiç ses üretilmedi; sebep §14'ün hata kanalından bildirilir |
| `KONUŞUYOR` | ses bitti | `IDLE` |
| `KONUŞUYOR` | söz kesme sinyali | `IDLE` — tur iptal, o `turn_id`'nin parçaları düşer |
| `ONAY_BEKLİYOR` | onay cümlesi okunuyor | `ONAY_BEKLİYOR` — okuma bu durumun içindedir, ayrı durum değil |
| `ONAY_BEKLİYOR` | okuma sırasında söz kesme | `ONAY_BEKLİYOR` — ses durur, plan yaşar |
| `ONAY_BEKLİYOR` | onay | `DÜŞÜNÜYOR` — askıya alınmış ajan döngüsü kaldığı yerden devam eder |
| `ONAY_BEKLİYOR` | red | `DÜŞÜNÜYOR` — red, §8.2'deki gibi tool sonucu olarak modele geri beslenir |
| `ONAY_BEKLİYOR` | zaman aşımı | `IDLE` — plan düşer; karşıda kimse olmadığı için konuşulmaz |
| `KAYIT` | yeterli örnek toplandı veya iptal | `DÜŞÜNÜYOR` |

Kurallar:

- **Söz kesme (barge-in):** `KONUŞUYOR` veya `DÜŞÜNÜYOR` durumunda istemciden söz kesme
  sinyali gelirse aktif tur iptal edilir, **o tura ait** bekleyen ses parçaları atılır, istemciye iptal
  bildirimi gider. Bu yüzden turdaki her aşama iptal edilebilir olmak zorundadır —
  sonradan eklenemez, baştan tasarlanır. İptalin kapsamı **turdur, TTS kuyruğunun tamamı
  değil** (§12). `ÇÖZÜMLÜYOR`'da söz kesme **tanımlı değildir**: segment henüz metne
  dönmemişken kesilecek bir ses de yoktur, sinyal hata olarak bildirilir.
- **Boş yanıt sessizce bitmez.** Ajan hiç metin üretmezse `ilk ses parçası hazır` olayı hiç
  olmaz, dolayısıyla kapanacak bir `KONUŞUYOR` da yoktur. Tur `yanıt boş` olayıyla `IDLE`'a
  döner; sebep §14'ün ayrı hata kanalından gider (**önce sebep, sonra durum** — istemci
  `IDLE`'ı hatadan önce görürse turun sessizce bittiğini sanar) ve iz `hata` ile kapanır.
  Duyulmamış yanıt konuşma geçmişine yazılmaz.
- **Aynı anda tek tur — kapsamı globaldir.** Sistem genelinde aynı anda yalnızca bir tur
  koşar; ikinci bir cihazdan segment gelirse sıraya girer. Gerekçe: konuşma tek sürekli
  akıştır (§11.1) ve tek GPU vardır. Paralel tur ne bağlam ne kaynak açısından kazandırır,
  yalnızca iki turun aynı geçmişe yazma yarışını doğurur.
- **`ONAY_BEKLİYOR`'a, onay cümlesi OKUNMADAN ÖNCE girilir.** Asistan ne yapacağını
  okurken durum zaten `ONAY_BEKLİYOR`'dur. Kullanıcı cümle bitmeden söze girerse — ki bu
  en olası davranıştır — ses durur ama **durum değişmez ve bekleyen plan yaşar**; gelen
  segment doğrudan onay çözümleyicisine gider. Bu güvenlidir, çünkü çözümleyici kısıtlı
  çıktılıdır ve serbest metinde anahtar kelime aramaz (Kural 5).
- **`ONAY_BEKLİYOR` kapalı bir durumdur:** Bu durumdayken gelen metin ajan katmanına
  hiç ulaşmaz; yalnızca onay çözümleyicisine gider (§8.5).
- **`KAYIT` kapalı bir durumdur:** Ses profili kaydı sırasında gelen segmentler normal
  tur akışına girmez.
- Cihaz kimliği zorunludur. Kimliksiz bağlantı reddedilir.

**Varlık (presence) takibi:** Aktör, o cihazdan gelen son kullanıcı etkileşiminin
zamanını tutar. Zamanlanmış bildirimler bu bilgiye göre en son kullanılan cihaza
yönlendirilir (§12).

---

## 6. Tur Akışı ve Streaming

```
ses segmenti
   │
   ├─► konuşmacı tanıma ─► güven seviyesi ──┐
   │                                        │
   └─► STT (Türkçe) ─► metin ───────────────┤
                                            ▼
                                   ajan döngüsü (§8)
                                            │
                             token akışı ───┤
                                            ▼
                                    cümle bölücü
                                            │
                                            ▼
                                   TTS kuyruğu (sıralı)
                                            │
                                            ▼
                              istemciye parça parça ses
```

- Konuşmacı tanıma ve STT paralel çalışır; ikisi de aynı ses segmentini kullanır ve
  birbirini beklemez.
- LLM akış (streaming) modunda çağrılır. Tool çağrısı yoksa token'lar doğrudan cümle
  bölücüye akar.
- **Dallanma ilk token'da belli olmalıdır.** Hangi dala girildiği ancak üretim başlayınca
  anlaşılır; o ana kadar çıktı tamponlanmak zorundadır ve o tampon doğrudan ilk ses
  gecikmesinden yenir. Bu yüzden GBNF grameri (§8.3), tool çağrısı dalını sabit ve zorunlu
  bir önekle başlatacak şekilde yazılır — tampon tek token'da boşalır. Bu bir gramer
  tasarım kısıtıdır, sonradan yapılacak bir iyileştirme değil.
- **Cümle bölücü:** cümle sonu noktalaması, minimum uzunluk ve maksimum bekleme
  eşiğiyle parçalar. Amaç ilk TTS parçasını mümkün olan en erken anda üretmek.
- **TTS kuyruğu sıralıdır:** parça N+1, parça N gönderilmeden gönderilmez. Sıra
  bozulması kabul edilemez bir hatadır.
- Tool çağrısı gerekiyorsa ses üretimi tool sonucu dönene kadar başlamaz; bu sırada
  istemciye "çalışıyor" durumu ve hangi tool'un çalıştığı bildirilir.

**Hedef:** İlk sesin çıkışına kadar geçen süre ölçülür ve regresyon testine bağlanır.
Somut hedef değeri, model seçimi ölçümü tamamlandıktan sonra belirlenir (§19).

---

## 7. Ses Girişi ve Aktivasyon

- **Wake word istemcide çalışır.** Hazır bir motorun sabit kelimelerinden biri
  kullanılır (motor ve kelime seçimi: §19).
- **Konuşma başı/sonu tespiti (endpointing) istemcide çalışır.** Sunucuya sürekli ses
  akışı değil, tamamlanmış konuşma segmentleri gider. Bunun üç sonucu var: bant
  genişliği düşer, sunucuda ikinci bir ses işleme katmanı olmaz, ve tespit mantığının
  tek bir sahibi olur.
- **Yankı yönetimi istemcinin sorumluluğudur.** Barge-in çalışabilmesi için istemci,
  kendi hoparlöründen çıkan sesi mikrofonda konuşma sanmamalıdır.
- Sunucu, istemcinin gönderdiği segmenti olduğu gibi kabul eder ve tekrar tespit yapmaz.

---

## 8. Ajan Katmanı

### 8.1 Tek sistem promptu, sabit önek

Tur boyunca sistem promptu değişmez. Mesaj sırası, LLM sunucusunun KV önbelleğinin
yeniden kullanılabilmesi için sabittir:

```
[sistem promptu (sabit)] [özet (varsa)] [konuşma geçmişi] [bağlam bloğu] [güncel tur]
```

Değişken içerik — tarih/saat, konuşmacı kimliği, getirilen olgular — **daima en sona**,
`bağlam bloğu` içine yazılır. Önekin bir baytı bile değişirse önbellek düşer.
Bu kural pazarlığa kapalıdır.

Tek istisna `[özet]` bloğudur: önekin ikinci sırasındadır, yani her güncellendiğinde
sistem promptu hariç tüm önbellek düşer. Bu kaçınılmazdır ama **seyrek olmak zorundadır** —
özet yalnızca açılışta ve bağlam kırpması sonrası boşta güncellenir (§11.2), tur içinde
asla.

### 8.2 Döngü

```
adım = 0
döngü (adım < MAX_ADIM):
    LLM'i akış modunda çağır
    tool çağrısı yoksa → metni cümle bölücüye akıt, bitir
    her tool çağrısı için:
        politika kontrolü → izin | red | onay gerekli
        onay gerekliyse → ONAY_BEKLİYOR durumuna geç, döngüyü askıya al
        red ise → gerekçeyi tool sonucu olarak geri besle
        izin ise → çalıştır (zaman aşımıyla)
    sonuçları bağlama ekle, adım += 1
```

- `MAX_ADIM` sonlu ve küçüktür. Sınıra ulaşılırsa döngü durur ve model eldeki
  sonuçlarla yanıt üretir; sessizce devam etmez.
- Tool sonucu eklendikten sonraki çağrı **aynı prompt ve aynı önekle** yapılır. Bu
  ayrı bir "ikinci çağrı" değil, döngünün bir sonraki adımıdır.
- Her tool çağrısının kendi zaman aşımı vardır. Zaman aşımı bir hata değil, modele geri
  beslenen bir sonuçtur — model bunu bilerek yanıt üretebilmelidir.

### 8.3 Tool çağırma biçimi — ✅ Yerel biçim (2026-08-16, sahibin kararı)

**Seçilen: Aday C, modelin kendi tool-calling şablonu** (§19.1, ölçüm
`docs/faz-b-yerel.md`). Katalog isteğin `tools` alanında JSON şema olarak gidiyor
(`tools/schema.py`), çağrıyı sunucu ayrıştırıyor, gramer yok.

**Kararı getiren şey bir puan değil, bir arıza sınıfı.** Metin biçimlerinde dal ilk
token'da seçiliyor (§6/C3), yani model bir üretimde ya konuşabiliyor ya çağırabiliyor.
İkisini birden istediğinde — "anladım, kuruyorum; ama önce saati almam lazım" — çağrıyı
düz metnin içinde **taklit ediyor**: hiçbir şey koşmuyor ve taklit sesli okunuyor.
Gramerde `<` yasaklandığında model aynı şeyi köşeli parantezle yazdı; karakter yasaklamak
sınıfı değil kılığını değiştiriyor. Yerel biçimde çakışma yok — `content` ile `tool_calls`
aynı yanıtta durur ve iki adımlı zincir (`date_time` → `task_create`) üretimde ilk kez
çalıştı.

**Aday A (CLI-tarzı) 2026-08-16'ya kadar seçiliydi** (Faz 0, `docs/faz0-olcum.md`) ve iki
metin biçimi hiçbir kümede birbirinden ayrışmadı. Üç biçim de kodda duruyor: iki gramer
üreticisi, iki ayrıştırıcı ve şema. Karar ölçülen modele bağlıdır; model değişirse
yeniden verilir ve değişecek tek satır `main.py:CALL_FORMAT`.

İki aday vardır ve seçim ölçümle yapılacaktır (§18, Faz 0). Ajan katmanı, çağrı biçimini
bir **adaptör** arkasına alır; her iki adaptör de aynı iç temsili üretir:

```
ToolCall(ad: str, argümanlar: dict)
```

Böylece kararın ajanın geri kalanına, politikaya veya tool'lara hiçbir etkisi olmaz;
ve model değiştiğinde karar yeniden verilebilir.

**Aday A — CLI-tarzı.** Model kabuk komutuna benzeyen tek satır üretir:

```
contact --get Ali
contact --update Ali --email ali@gmail.com
weather --city Denizli --fields temperature,condition
note --create --title Alışveriş --body süt, ekmek ve yumurta al
```

Kuralları:

- **Her alan çok kelimeli olabilir; bir sonraki bilinen bayrağa kadar okunur.** Tırnak
  gerekmez. `--title Alışveriş listesi --body süt ve ekmek al` doğru ayrışır, çünkü
  `--body` gramerde sabit bir jetondur.
- **En fazla bir alan, içinde bayrak gibi görünen metin barındırabilir; ve o alan imzada
  en sonda durur.** Bu son bayraktan sonrası satır sonuna kadar tek parça metin sayılır ve
  hiçbir jeton bayrak olarak yorumlanmaz. Türkçe kesme işareti ve noktalama yüzünden
  bozulan ayrıştırma sorunu böylece ortadan kalkar. Karşılığı: o bayraktan sonra başka
  argüman gelemez.
- Listeler virgülle ayrılır.
- **Hata durumunda tool kullanım metnini döndürür** (`--help` çıktısı). Model bunu
  okuyup kendini düzeltebilir. Bu düzeltme turları sayılır ve sınırlanır.
- **Üretilen metin asla kabukta çalıştırılmaz.** Yalnızca ayrıştırılıp yapılandırılmış
  bir çağrıya dönüştürülür. Bu, sözdiziminin kabuk benzemesinden doğan tek gerçek
  tehlikedir ve kod düzeyinde imkânsız kılınır.

**Aday B — JSON.** LLM sunucusunun standart tool çağrısı biçimi.

**Ortak:** Her iki adayda da çıktı **GBNF grameriyle kısıtlanır.** Model dilbilgisel
olarak geçersiz bir çağrı üretemez; tool adları da gramerde sabit listedir. Yani
"geçersiz çıktı" ihtimali her iki yolda da ortadan kalkar ve karşılaştırma yalnızca
*doğru* tool ve *doğru* argüman seçimi üzerinden yapılır. Faz 0 bunu doğruladı: iki
biçimde de sıfır uydurulan tool, sıfır uydurulan argüman. **O sıfır gramerin ölçüsüdür,
modelin değil** (P26): defterde olmayan bir ad gramerce üretilemediği için bu sayaç
yapısal olarak sıfırdır ve modelin halüsinasyonu hakkında hiçbir şey söylemez. Üretimdeki
halüsinasyon — yapılmamış bir eylemi yaptım demek — ayrı bir kümeyle, çağrının **yokluğu**
üzerinden ölçülüyor.

**Faz 0'ın kararla ilgisi olmayan iki bulgusu, ikisi de biçimden bağımsız:**

- **Eksik bilgi sorulmuyor, uyduruluyor.** Kullanıcı şehri/hedefi/adı söylemediğinde model
  düz metinle sormak yerine yer tutucu bir değerle çağrı üretiyor (`--target <cihaz_adı>`,
  `--name "Yeni Kişi"`). Ölçülen: bu eksende doğruluk %57. Argüman doğrulaması (§8.5 adım 1)
  ve §19.9'un "yalnızca yapılandırmadaki adlar" kuralı bu yüzden gevşetilemez; düzeltme
  döngüsünün asıl işi de budur (Faz 3).
- **CLI'de tırnak açığı.** Model bir alanı `--message "…"` diye tırnak içinde yazabiliyor
  ve tırnaklar değerin parçası oluyor. Gramerde kapatılabilir bir açık; kapatan değişiklik
  §17.1'in değerlendirme kapısından geçmelidir.

### 8.4 Tool kataloğu promptta

Tüm tool'lar ve argümanları sistem promptunda bulunur. Model çalışma anında keşif
yapmaz. Gerekçe: keşif turu gecikme ekler ve bu sistemde gecikme birinci sınıf hedeftir.
`--help` yalnızca hatalı çağrıdan sonra devreye giren bir düzeltme mekanizmasıdır.

Bunun bedeli, tool sayısı arttıkça promptun büyümesidir. Bu bedel ölçülür; prompt,
bağlam bütçesinin belirlenen payını aşarsa keşif modeli yeniden değerlendirilir.

### 8.5 Onay akışı

Geri alınamaz bir işlem istendiğinde:

1. Argümanlar önce doğrulanır. Geçersizse kullanıcıya hiç sorulmaz — hata modele geri
   beslenir ve model kendini düzeltir. Kullanıcıdan bozuk bir işlemi onaylaması asla
   istenmez.
2. Oturum `ONAY_BEKLİYOR` durumuna geçer ve bekleyen plan tutulur. **Bu adım okumadan
   öncedir**; sıra pazarlığa kapalıdır (§5).
3. Asistan yapacağı işlemi ve argümanlarını açıkça okur. Kullanıcı okuma bitmeden söze
   girerse ses durur, ama durum ve bekleyen plan korunur; gelen segment doğrudan 4. adıma
   gider. Onay cümlesinin sonuna kadar dinlenmiş olması şart değildir.
4. Sonraki konuşma segmenti **yalnızca onay çözümleyicisine** gider. Çözümleyici
   kısıtlı bir çıktıyla üç sonuçtan birini üretir: onay / red / belirsiz.
5. Belirsizse bir kez daha sorulur, yine belirsizse işlem iptal edilir.
6. Zaman aşımında **varsayılan red**'dir.

Serbest metin üzerinde anahtar kelime araması yapılmaz. "Tamam ama önce hava durumu"
gibi bir cümlenin onay sayılması, tasarımın kabul etmediği bir hatadır.

---

## 9. Tool'lar

### 9.1 Tanım — bir tool, bir dosya

Bir tool'un şeması, gövdesi ve politika sınıfı aynı dosyada, tek yerde durur. Yeni tool
eklemek tek dosya oluşturmak ve kayıt defterine kaydolmaktır; başka hiçbir dosyaya
dokunulmaz. Dağıtılmış tanım, dokümantasyonun koddan sapmasının başlıca sebebidir.

Her tool şunları bildirir:

- **Ad ve açıklama** — prompt kataloğunda görünen metin.
- **Argümanlar** — tipli ve doğrulanmış. Alanlar çok kelimeli olabilir; ama en fazla biri
  bayrak gibi görünen metin barındırabilir ve o alan imzada en sonda durur (§8.3).
- **Etki sınıfı** — `OKUMA` | `YAZMA` | `DIŞ` | `GERİ_ALINAMAZ`. Onay ve yetki kararları
  bu alandan türetilir; ayrıca "hassas tool listesi" tutulmaz.
- **Zaman aşımı.**
- **Kullanım metni** — hatalı çağrıda modele dönen `--help` çıktısı.

Tool'lar veriye yalnızca kendilerine verilen bağlam nesnesi üzerinden erişir; genel
veritabanı bağlantısına doğrudan erişmez.

Tool sonucu yapılandırılmıştır: başarı durumu, veri, kullanıcıya okunacak biçim ve hata
alanı ayrı ayrı taşınır. "Her şey metindir, JSON'u iki kere ayrıştır" düzeni kurulmaz.

### 9.2 İlk sürüm kataloğu

| Tool | Etki | Not |
|---|---|---|
| Tarih/saat | OKUMA | Sistem saati |
| Hava durumu | DIŞ | OpenWeatherMap; anahtar yapılandırmadan (§19.7) |
| Kişiler — listele/getir | OKUMA | |
| Kişiler — oluştur/güncelle | YAZMA | |
| Kişiler — sil | GERİ_ALINAMAZ | Onay ister |
| Notlar — ara/listele | OKUMA | |
| Notlar — oluştur | YAZMA | Serbest metin gövdesi |
| Notlar — sil | GERİ_ALINAMAZ | Onay ister |
| Ders programı | OKUMA | Kaynak: depodaki program dosyası (§19.8) |
| Sistem metrikleri | OKUMA | |
| Wake-on-LAN | GERİ_ALINAMAZ | Fiziksel etki; onay ister. Hedefler yapılandırmada (§19.9) |
| Zamanlanmış görev — oluştur | YAZMA | |
| Zamanlanmış görev — listele/iptal | OKUMA / YAZMA | |
| Ses profili — kaydet/sil | GERİ_ALINAMAZ | §10 |

### 9.3 İlk sürümden sonra eklenenler (Faz 8)

Bellek yazma kapısı ve makine denetimi. §9.2 ilk sürümün kapsamıydı; bunlar onu genişletiyor
ve aynı kurallara tabi.

| Tool | Etki | Not |
|---|---|---|
| Bellek — kaydet | YAZMA | §11.3'ün eksik kapısı: görme ve silme vardı, yazma yoktu |
| Ses seviyesi — oku/ayarla | DIŞ | Tek tool; seviye verilmezse okur |
| Medya — oynat/duraklat/atla | DIŞ | MPRIS; eylem sayılı seçenek |
| Uygulama aç | DIŞ | Ad → argv yapılandırmada; ham komut kabul edilmez (Kural 8) |
| Pencere — geri alınabilir eylemler | DIŞ | Küçült/büyüt/tam ekran/genel bakış |
| Pencere — kapat | GERİ_ALINAMAZ | Kaydedilmemiş iş geri gelmez; onay ister |

**Sayılı seçenek (`ArgType.ENUM`).** Bir alanın değeri sabit bir listeden geliyorsa, liste
gramerde harfi harfine yazılır ve geçersiz bir seçenek **üretilemez** — tool adlarındaki
güvencenin argüman tarafındaki eşi. Katalogda tipin adı değil seçeneklerin kendisi görünür.

**Etki sınıfı tool başınadır, seçenek başına değil.** Aynı tool'un bir seçeneği geri
alınabilir, bir başkası değilse tool ikiye ayrılır (pencere eylemleri ile pencere kapatma).
Aksi hâlde ya zararsız eylem her seferinde onay isterdi ya da yıkıcı olan onaysız geçerdi.

**Makine denetimi bir adaptörün arkasındadır** (§4): tool *ne* istendiğini bilir, *nasıl*
yapıldığını değil. Mekanizma masaüstüne özeldir ve değişebilir; tool tanımı değişmez.

---

## 10. Kimlik, Yetki ve Kayıt

### 10.1 Kimlik

Her konuşma segmentinden bir ses gömüsü (embedding) çıkarılır ve kayıtlı profillerle
karşılaştırılır. Sonuç bir **skordur**, bir iddia değil. Skor bir güven seviyesine
çevrilir. Eşik değerleri ölçümle belirlenir (§19).

**Kural:** Kimlik bilgisi kullanıcının metnine yazılmaz. Kullanıcı metni ve kimlik
ayrı alanlarda taşınır; prompt'a yalnızca sistemin kontrol ettiği `bağlam bloğu`
içinde girer. Kullanıcının söyleyebildiği hiçbir şey kimlik alanını taklit edemez.

### 10.2 Kademeler

| Kademe | Kim | Yetki |
|---|---|---|
| **Sahip** | Ses profili eşleşen sahip | Tümü (geri alınamazlar onay ister) |
| **Kayıtlı kişi** | Rehberde kayıtlı ve onaylanmış | Yalnızca `OKUMA` ve `DIŞ` |
| **Bekleyen** | Rehberde kayıtlı ama onaylanmamış | Yok — yalnızca sohbet ve kayıt akışı |
| **Tanınmayan** | Profili olmayan | Yok — yalnızca sohbet ve kayıt teklifi |

Politika tablosu koddadır ve tek zorlayıcı katmandır. Sistem promptu modele
kademelerden ve sınırlardan bahseder, ama bu bir kolaylıktır: modelin bu bilgiyi
yok sayması bir güvenlik olayı değildir, çünkü kararı model vermez.

### 10.3 Tanınmayan kişi akışı

Model, karşısındakinin tanınmadığını **bilir** ve buna göre davranır: kendini tanıtır,
ismini sorar, kayıt teklif eder. Kişi ismini verirse rehbere `bekleyen` olarak yazılır
ve ses profili oluşturulur. `bekleyen` durumunda hiçbir yetki açılmaz.

### 10.4 Yetki verme

Sahip, bekleyen bir kişiyi `kayıtlı kişi` seviyesine sesle yükseltebilir. Bu bir
geri alınamaz işlemdir ve onay adımından geçer.

**Sınır:** Sesle verilebilecek en yüksek kademe `kayıtlı kişi`dir. **Sahip kademesi
sesle asla verilemez.** Sahip yalnızca kurulum betiğiyle atanır (§19.14): betik birkaç ses
örneği toplar, profili sahip olarak işaretler ve sahip zaten tanımlıysa çalışmayı reddeder.
Fiziksel makine erişimi gerektirir.

Gerekçe — ve bu bilinçli kabul edilmiş bir risktir: kimlik tek kanaldan, sesten
doğrulanıyor. Ses kaydı çalınabilir. Bu sınır olmasa, bir kaydı çalan biri kendini
sahip seviyesine yükseltebilirdi. Sınırla birlikte en kötü senaryo salt-okuma yetkisiyle
sınırlı kalır. Sahip kademesine giden yolun sesli bir kapısı yoktur.

### 10.5 Ses profili kaydı

Kayıt ayrı bir durumdur (`KAYIT`), tur akışının içine serpiştirilmiş koşullar değil.
Birden fazla ses örneği toplanır, birleştirilir ve profil olarak saklanır. Örnek sayısı
ve kalite eşiği ölçümle belirlenir (§19).

---

## 11. Bağlam ve Bellek

### 11.1 Konuşma bağlamı

- Oturum sınırı yoktur; konuşma tek sürekli akıştır.
- Bağlam penceresi token bütçesiyle sınırlanır. **Token sayısı tahmin edilmez** — LLM
  sunucusunun kendi sayaç ucundan alınır ve mesaj başına önbelleklenir.
- Bütçe, modelin gerçek bağlam boyutundan türetilir ve tek bir yerde tanımlanır.
  İki farklı bileşenin bağlam boyutu hakkında farklı fikri olamaz.
- **Bütçe konuşmanın ortasında aşılırsa sert kırpma uygulanır:** en eski mesajlar bağlam
  penceresinden çıkarılır. Veritabanından **silinmezler** — yalnızca pencerenin dışında
  kalır ve "özetlenmemiş" olarak işaretlenirler. Özetleme o anda çalışmaz (§11.2).

### 11.2 Özetleme

Özetleme iki anda çalışır ve **ikisi de aktif turun dışındadır:**

1. **Açılışta:** son açılıştan bu yana özetlenmemiş konuşma varsa özetlenir ve özet kalıcı
   olarak saklanır.
2. **Boştaki ilk fırsatta:** §11.1'deki sert kırpma yüzünden özetlenmemiş mesaj birikmişse,
   sistem boşa düşer düşmez özetlenir ve özet devreye girer.

Konuşma sırasında özetleme yapılmaz — böylece aktif tur sırasında LLM'in kaynağına rakip
olan bir arka plan işi bulunmaz (Kural 11).

**Kabul edilen bedel:** kırpma ile özetin hazırlanması arasında bir pencere vardır ve o
pencerede model kırpılan mesajları hatırlamaz. Bu pencereyi asıl kapatan şey özet değil,
kalıcı olgu deposudur (§11.3): konuşmadan çıkarılmış olgular kırpmadan etkilenmez ve
bağlam bloğunda getirilmeye devam eder.

**Ve asıl kural şu: kırpma istisnai bir olaydır, rutin değil.** Bütçe, normal bir günün
kırpmaya hiç dokunmayacağı şekilde boyutlandırılır. Her kırpma kaydedilir ve sıklığı
ölçülür; sık kırpılıyorsa çözüm daha iyi bir kırpma stratejisi değil, bütçenin yanlış
olduğunu kabul etmektir.

### 11.3 Kalıcı bellek

Konuşmalardan çıkarılan olgular kalıcı olarak saklanır ve sonraki turlarda ilgili
olanlar getirilir.

- **Tek ortak havuz, kişi etiketli.** Her olgu kimin söylediğini taşır. Böylece
  asistan "arkadaşın bu konuda şöyle demişti" diyebilir — bilgi ortak, kaynağı belli.
- Olgu çıkarımı **aktif tur sırasında çalışmaz.** Boşta veya açılışta çalışır. Gerekçe:
  çıkarım LLM'i kullanır ve konuşma sırasında modelin sırasına girmek, ölçülmemiş bir
  gecikme vergisidir.
- **Başlamış bir arka plan işi, tur başlar başlamaz preempt edilir.** "Tur sırasında
  başlamaz" demek yetmez: boşta başlamış bir çıkarım, tur geldiğinde hâlâ üretim yapıyor
  olabilir ve tek GPU'nun tek slotunu tutar — kullanıcının ilk token'ı onu bekler. Bu
  yüzden bütün arka plan LLM işleri bir iptal jetonu taşır, tur kuyruğa girdiği anda iptal
  edilir ve bir sonraki boşlukta baştan başlar. Yarım kalmış çıkarımın sonucu yazılmaz.
- Getirilen olgular `bağlam bloğu` içinde, kaynağı ve tarihi belirtilerek verilir; ve
  bunların bayat olabileceği, gerçek zamanlı veri için tool çağrılması gerektiği açıkça
  yazılır.
- Olgular listelenebilir ve silinebilir olmalıdır. Kullanıcının göremediği ve
  silemediği bir bellek, hata ayıklanamaz bir bellektir.

---

## 12. Zamanlanmış Görevler

- Görevler kalıcı saklanır; uygulama kapanıp açıldığında kaybolmaz.
- Kaçırılan görev davranışı açıkça tanımlıdır: uygulama kapalıyken vakti geçmiş bir
  görev, açılışta belirlenen tolerans içindeyse çalıştırılır, değilse düşürülür ve
  düşürüldüğü kaydedilir.
- **Proaktif ses kanalı:** Zamanlanmış bir görev, kullanıcı bir şey sormadan ses
  üretebilir. Bu kanal tur akışından ayrıdır ama aynı TTS kuyruğunu kullanır.
- **İptal turun kapsamındadır, kuyruğun değil.** Kuyruktaki her parça bir `turn_id` taşır
  (§13) ve söz kesme yalnızca o `turn_id`'ye ait parçaları düşürür. Aksi halde kullanıcının
  asistanı kesmesi, kuyrukta bekleyen bir hatırlatıcıyı da sessizce çöpe atardı — ve kimse
  fark etmezdi. Proaktif bildirimler kendi `turn_id`'lerini alır, söz kesmeden etkilenmez
  ve sıradaki yerlerini korur.
- Hedef cihaz: **en son etkileşimde bulunulan cihaz** (§5, varlık takibi). Hiçbir cihaz
  bağlı değilse bildirim kuyruklanır ve ilk bağlanan cihaza verilir.
- Proaktif ses, kullanıcı konuşurken veya asistan konuşurken araya girmez; sıraya girer.

---

## 13. İstemci Protokolü

WebSocket üzerinden, tipli çerçevelerle.

**İstemci → Sunucu:** konuşma segmenti (ses), kontrol mesajları (söz kesme sinyali,
bağlantı canlılığı), cihaz kimliği ve protokol sürümünü taşıyan el sıkışma.

**Sunucu → İstemci:** çözümlenen metin, durum değişikliği, çalışan tool bildirimi,
**cevabın metni**, ses parçası (`turn_id` + sıra numaralı), ses sonu, iptal, hata,
**proaktif bildirim**.

Kurallar:

- El sıkışmada protokol sürümü doğrulanır; uyuşmazlıkta bağlantı açık bir hatayla
  reddedilir. Sessizce farklı davranmaz.
- **Cevabın metni sesin yanında ayrı bir çerçeveyle gider**, cümle başına bir tane ve o
  cümlenin sesinden önce. Sesin yerini tutmaz: ikisi de aynı `turn_id`'yi taşır. Bu
  çerçeve olmadan istemci cevabı yalnızca sesten öğrenebilirdi ve bir metin arayüzünde
  hiç gösteremezdi — kullanıcı kendi sorusunu görüp cevabını göremez. `Transcript`'in
  kullanıcı için yaptığının aynısı, konuşan taraf için.
- **Her ses parçası `(turn_id, seq)` taşır.** İstemci kendi bildiği aktif `turn_id`
  dışındaki her parçayı sessizce atar, `seq` ile de sırayı doğrular. Bunsuz söz kesme
  bozuktur: iptal bildirimi gittikten sonra ağda ve istemci tamponunda hâlâ ölü turun
  parçaları vardır, ve `seq` tek başına onları yeni turun ilk parçasından ayırt edemez —
  iptal edilmiş cevabın kırıntısı yeni cevabın üstüne çalar. `turn_id` tel formatının
  parçasıdır; sonradan eklenemez.
- **Proaktif bildirim, sesinden önce kendi turunu duyurur.** Zamanlanmış bir görevin ürettiği
  ses de kendi `turn_id`'sini taşır (§12) — ama o turu kullanıcı açmadığı için istemci onu
  hiçbir yerden bilmez ve yukarıdaki filtre gereği parçalarını atardı. Bu yüzden ses
  başlamadan önce `turn_id` ve metni taşıyan bir bildirim çerçevesi gider; istemci turu
  ondan öğrenir. `Transcript`'in yerini tutmaz: transkript kullanıcının konuşmasını tura
  bağlar, burada konuşan kullanıcı değildir. Durum değişikliğiyle de duyurulamaz: proaktif
  ses bir tur değildir ve §5'in tablosunda karşılığı yoktur.
- Ses formatı: yerelde ham PCM, uzak bağlantıda sıkıştırma. **Karar ölçüme bağlıdır** —
  PCM ile sıkıştırmalı taşımanın bant genişliği farkı ölçülür; fark küçükse uzakta da
  PCM kullanılır ve kodek katmanı hiç yazılmaz. Taşıma katmanı bu seçimi opsiyonel
  bırakacak şekilde tasarlanır.

---

## 14. Hata Yönetimi ve Toparlanma

- Her model servisinin bir sağlık kontrolü vardır. Core, servisleri düzenli yoklar.
- Bir servis yanıt vermezse: kullanıcıya hem sesli (mümkünse) hem arayüzde bildirilir,
  servis yeniden başlatılır, geri çekilmeli (backoff) yeniden deneme uygulanır.
- **TTS çöktüğünde sesli bildirim mümkün değildir.** Bu yüzden arayüz bildirimi ikinci
  ve bağımsız bir kanaldır; ses kanalına yedek olarak değil, ona paralel çalışır.
- Uygulama süreci çökerse dışarıdan yeniden başlatılır (işletim sistemi servis
  yöneticisi). Uygulama kendi kendini yeniden başlatmaya çalışmaz.
- Kısmi çalışma açıkça desteklenir: LLM ayakta ama TTS yoksa, yanıt arayüzde metin
  olarak gösterilir. Sistem "ya hep ya hiç" davranmaz.
- Hiçbir hata sessizce yutulmaz. Bir işlem başarısız olduysa bu, hem kayda hem
  kullanıcıya yansır.

---

## 15. Gözlemlenebilirlik

- Her turun bir kimliği ve aşama aşama süreleri vardır: konuşmacı tanıma, STT, bağlam
  hazırlama, LLM ilk token, LLM toplam, her tool, ilk TTS parçası, ilk sesin çıkışı,
  toplam.
- Tur izleri kalıcı yazılır ve **yeniden oynatılabilir**: aynı girdi, sahte adaptörlerle
  tekrar çalıştırılabilir. Ses kaydetmeden hata ayıklama bunu gerektirir.
- Kayıtlar yapılandırılmıştır ve seviyelidir. Tüm konuşma geçmişini her turda diske
  yazan kayıtlar hata ayıklama seviyesinde kalır, normal çalışmada üretilmez.
- Arayüz, sistemin o anki durumunu (hangi durumda, hangi tool çalışıyor, hangi kimlik
  tanındı) canlı gösterir.

---

## 16. Veri Katmanı

- SQLite, tek dosya, tek sahip. WAL kipi.
- Erişim repository modülleri üzerinden. SQL, modüller arasına dağılmaz.
- Şema sürümlenir; migration'lar sıralı ve idempotenttir. Migration hatası sessizce
  yutulmaz — sessiz yutma, şema sapmasını gizler.
- **Otomatik yedek:** periyodik ve tutarlı (SQLite'ın kendi yedekleme mekanizmasıyla,
  dosya kopyalayarak değil). Yedek sayısı sınırlı tutulur, eskiler döndürülür.
  Kişiler, notlar ve ses profilleri geri getirilemez veridir; yedek bu yüzden
  opsiyonel değildir.
- Saklanan veri: konuşma geçmişi, özetler, olgular, kişiler ve ses profilleri, notlar,
  ders programı, zamanlanmış görevler, açılış kayıtları, tur izleri.

---

## 17. Test ve Ölçüm

Bu bölüm isteğe bağlı değildir. Bu sistemde en sık bozulan şey tool seçimidir ve
prompt'a atılan her el, ölçülmediği sürece kör bir değişikliktir.

1. **Tool seçim değerlendirmesi.** Türkçe ifadelerden oluşan golden set: beklenen tool
   ve beklenen argümanlar. Doğruluk oranı ve halüsinasyon oranı raporlanır. Prompt,
   tool açıklaması veya model değişikliği bu kapıdan geçmeden kabul edilmez.
2. **Halüsinasyon ölçümü.** Üç ayrı sayaç: olmayan tool uydurma, olmayan argüman
   uydurma, tool sonucunda bulunmayan bir bilgiyi yanıtta iddia etme. Üçü ayrı ayrı
   raporlanır; tek bir "doğruluk" sayısında eritilmez.
3. **Tur akışı testleri** sahte adaptörlerle: GPU'suz, saniyeler içinde.
4. **Politika testleri:** her (etki sınıfı × kademe) hücresi için bir test.
5. **Durum makinesi testleri:** söz kesme, zaman aşımı, onay sırasında konu değiştirme,
   eşzamanlı segment, kayıt sırasında kesinti. Ayrıca: **onay cümlesi okunurken söz kesme**
   (plan yaşamalı, segment çözümleyiciye gitmeli), **iptalden sonra gelen eski `turn_id`'li
   ses parçası** (atılmalı), **söz kesme sırasında kuyrukta bekleyen proaktif bildirim**
   (düşürülmemeli).
6. **Gecikme regresyonu:** sahte adaptörlerle ölçülen aşama ek yükü tavanı aşarsa test
   kırılır.

---

## 18. Fazlar

Ayrıntılı iş paketleri ve bitti kriterleri `docs/PLAN.md`'dedir. Sıralamada iki düzeltme
yapılmıştır:

- **Faz 0 tool kataloğunu gerektiriyordu**, katalog ise Faz 3'teydi — yani Faz 0
  çalıştırılamıyordu. Tool *bildirimleri* (şema, etki sınıfı, katalog metni, GBNF üretimi)
  Faz 0'ın önüne alındı; gövdeler ve düzeltme döngüsü Faz 3'te kaldı.
- **Faz 5'in bitti kriteri istemciyi gerektiriyordu**, istemci ise Faz 7'deydi. Asgari
  başsız istemci Faz 5'e alındı; GUI Faz 7'de kaldı.

### Faz 0 — Çağrı biçimi kararı (ajan kodundan önce) ✅

**Koşuldu; karar o gün CLI-tarzı** (§19.1). Sonuç raporu `docs/faz0-olcum.md`, araç
`evals/`. Ölçüm bir aday model üzerinde koştu; diğerleri Faz 2'de aynı araçla ölçüldü.

**Bu karar 2026-08-16'da değişti: üretim yerel biçime geçti** (§8.3, `docs/faz-b-yerel.md`).
Aşağıdaki tasarım ve ölçüm düzeni olduğu gibi geçerli; değişen, iki metin adayının
yanına üçüncü bir adayın eklenmesi ve seçimin ona kayması.

Amaç tek bir soruyu yanıtlamak: **CLI-tarzı mı, JSON mu?**

- 50 Türkçe test senaryosu. Her senaryo: girdi metni, beklenen tool, beklenen argümanlar.
- Senaryolar tool seçimini gerçekten zorlayacak şekilde dağıtılır: tek tool, birden
  fazla tool gerektiren, eksik argümanlı, hiç tool gerektirmeyen, benzer iki tool
  arasında ayrım gerektiren, ve serbest metin argümanı içeren durumlar.
- İki çağrı biçimi de GBNF grameriyle kısıtlanmış olarak ölçülür.
- Eldeki modellerin her biri için çalıştırılır.
- **Ölçülenler:** tool seçim doğruluğu, argüman doğruluğu, halüsinasyon oranı (üç
  sayaç), üretilen token sayısı, çağrı başına süre, kendini düzeltme turu sayısı.
- **Ölçülmeyenler:** STT ve TTS. Bu karar için ilgisizdirler.
- **Çıktı:** ölçüm sonuçları ve gerekçeli bir karar. Proje bu kararla başlar.

Bu ölçüm aracı atılmaz; Faz 1'de tool seçim değerlendirmesinin (§17.1) temeli olur.

### Faz 1 — İskelet ✅

**Tamamlandı** (P1–P8, `docs/PLAN.md`). Katmanlar, arayüzler, sahte adaptörler, veri katmanı
ve migration'lar, uçtan uca test. GPU'suz çalışan bir sistem. Bitti kriteri: sahte
adaptörlerle uçtan uca test yeşil. — Karşılandı; tur akışı segmentten sese kadar sahtelerle
koşuyor ve kaydedilmiş bir tur yeniden oynatılıp aynı sonucu veriyor (§15).

### Faz 2 — Model ölçümü ve seçimi

Tam pipeline ölçümü: eldeki LLM/STT/TTS adaylarının gerçek VRAM tüketimi, aşama
gecikmeleri, Türkçe STT doğruluğu. 16 GB bütçeye hangi kombinasyonun sığdığı burada
**ölçülerek** belirlenir. Bitti kriteri: seçilmiş model üçlüsü ve ölçülmüş gecikme
temel çizgisi.

### Faz 3 — Ajan ve tool'lar

Faz 0'da seçilen çağrı biçimi, düzeltme döngüsü, Faz 0'da bildirilmiş ama gövdesi
yazılmamış tool'ların tamamlanması, katalog boyutunun gerçek modelde ölçülmesi.
Bitti kriteri: tool seçim değerlendirmesi Faz 0 temel çizgisini tutturuyor.

### Faz 4 — Kimlik, yetki, onay

Konuşmacı tanıma, kademeler, kayıt akışı, onay durumu. Eşik değerleri ölçülür.
Bitti kriteri: politika testlerinin tamamı yeşil.

### Faz 5 — Streaming, söz kesme ve asgari istemci

Token akışı, cümle bölme, TTS kuyruğu, iptal edilebilirlik. Asgari başsız istemci:
mikrofon, wake word, endpointing, ses çalma ve **yankı yönetimi (AEC)**. AEC bu fazın en
büyük iş kalemidir — yarım-dubleks kaçış yolu (asistan konuşurken mikrofonu kapatmak) söz
kesmeyi tamamen öldürdüğü için gerçek bir AEC gerekir.
Bitti kriteri: ilk ses süresi ölçüldü ve regresyon testine bağlandı.

### Faz 6 — Bellek ve zamanlanmış görevler

Olgu deposu, açılışta özetleme, zamanlayıcı, proaktif ses kanalı, cihaz varlık takibi.

### Faz 7 — Arayüz ve işletim

Native GUI, durum göstergesi, bekleyen kişi yönetimi, otomatik yedekleme, servis
yönetimi ve otomatik toparlanma.

---

## 19. Açık Maddeler

Bunlar karar verilmemiştir. Uygulanmadan önce cevaplanır; yerlerine varsayım konmaz.
Numaralandırma çapraz referanslar için sabittir: kapatılan maddeler listeden çıkarılmaz,
✅ ile işaretlenip kararı yazılır.

**Ölçüme bağlı olanlar:**

1. ✅ **Tool çağırma biçimi: YEREL — modelin kendi tool-calling şablonu** (2026-08-16,
   sahibin kararı; ölçüm `docs/faz-b-yerel.md`). Katalog `tools` alanında JSON şema,
   çağrıyı sunucu ayrıştırıyor, gramer yok.

   **Kararı getiren şey doğruluk değil, metin biçimlerinin mümkün kıldığı bir arıza
   sınıfı.** Dal ilk token'da seçildiği için (§6/C3) model bir üretimde ya konuşabiliyor
   ya çağırabiliyor; ikisini birden istediğinde çağrıyı düz metnin içinde taklit ediyor,
   hiçbir şey koşmuyor ve taklit sesli okunuyor. Gramerde `<` yasaklanınca model
   `[tool] date_time` yazdı — **karakter yasaklamak sınıfı değil kılığını değiştiriyor.**
   Sayılar (üretim öneği, dil kuralı açık): kabul kapısı 12/15 → 14/15, altın %98 → %92,
   kontrol %89 → %94, halüsinasyon %93 → %100, bellek %88 → %82, argüman doğruluğu
   %89 → %94. **Bütün aralıklar çakışıyor, yani sıralama değil** (Kural 14); altındaki
   altı hatanın dördü tek sınıf — model çağırmak yerine eksik alanı sordu.

   **Bunun bir bedeli var ve ölçüldü:** dil kuralının yeri. Katalogu şablon ekliyor ve
   `tools` bloğunu sistem mesajımızın **arkasına** koyuyor, yani Faz 7'nin bulduğu yer
   (öneğin sonu) artık orası değil; kural bırakıldığı yerde tutmadı (elle koşuda altı
   turun altısı Türkçe). Kural bağlam bloğunun sonuna taşındı ve tuttu (altı/altı
   İngilizce, `kontrol` kuralsız %78 → kurallı %94).

   Aşağıdaki Faz 0 gerekçesi tarihsel olarak duruyor:

   ✅ **CLI-tarzı** (2026-08-16'ya kadar). Faz 0'da 50 Türkçe senaryo, iki biçim de GBNF
   ile kısıtlanmış olarak ölçüldü; sonuçlar `docs/faz0-olcum.md`'de. Tool seçimi %94'e
   %92, argüman doğruluğu berabere (%94); belirleyici olan bedel: CLI **%22 daha az token
   ve %13 daha hızlı** — §6'nın ilk ses gecikmesinde doğrudan karşılığı olan tek fark.
   İki biçimde de sıfır uydurulan tool ve sıfır uydurulan argüman: gramer görevini yapıyor.
   **Karar modele bağlıdır ve yeniden açılabilir:** ölçüm ilkin yalnızca bir aday
   üzerinde (Qwen3.6-35B-A3B-IQ4_XS) koştu. Diğer dört aday Faz 2'de aynı kapıdan geçti
   (`docs/faz2-olcum.md`) ve **fark gerçekten tersine döndü:** büyük modellerde CLI,
   9B'nin iki niceliğinde JSON önde (9B-Q4'te %60'a %84), gemma-4-12B ise ikisini
   ayırmıyor. **Karar CLI'de duruyor ama dayanağı 2026-08-15'te zayıfladı:** kapanma
   gerekçesi "LLM adayı Qwen3.6-35B-A3B'de sabitlendi" idi ve madde 2 o gün geri alındı,
   yani biçim kararı artık verilmemiş bir model kararına yaslanıyor. CLI çalışan seçim
   olarak kalıyor — `docs/faz6-olcum.md` sunucuda koşan modelde de CLI'yi önde ölçtü
   (106/110'a 104/110, aralıklar çakışıyor).

   **Yeniden okundu (2026-08-15), madde 2'nin LLM yarısı kapandıktan sonra, seçilen
   modelde: karar CLI'de kalıyor ama gerekçesi incelmiştir.** Dört küme, üretim öneği,
   benimsenen rol metni (`docs/faz6-27b-rol3.md`): altın %100'e %96, halüsinasyon %93'e
   %100, kontrol ve bellek berabere — **doğrulukla ayrılmıyorlar**, dört kümenin dördünde
   aralıklar çakışıyor. Ayıran şey yine bedel: ortalama token dört kümenin üçünde CLI'de
   daha düşük (15/11/10'a 22/19/21) ve tamamlanma süresi üçünde daha kısa. **Ama Faz 0'ın
   belirleyici sayısı olan ilk ses artık berabere** (0.22'ye 0.22, 0.13'e 0.13): §6'nın
   bütçesinde iki biçim aynı yerde duruyor, fark tamamlanmada ve token bedelinde kaldı.
   Yani CLI'nin üstünlüğü sürüyor fakat marjı Faz 0'daki kadar geniş değil. Ayrıştırıcı ve gramer iki biçimi de
   üretmeye devam ediyor: model değişirse ölçüm yeniden koşar ve §8.3'ün adaptörü tam da
   bunun için var — sistemin başka hiçbir yeri biçime bakmıyor.
2. **KISMEN KAPANDI — LLM: `Qwen3.8-27B-IQ4_XS`. STT ve TTS açık.** LLM `llama-server`
   arkasında `localhost:8080`; hangi modelin koştuğu bir çalıştırma tercihidir, mimari
   karar değil. Bağlam boyutu yapılandırmaya yazılmıyor, sunucudan soruluyor (§11.1).

   **LLM kararı sahibindir ve 2026-08-15'te verildi (gerekçe: kamuya açık ölçütlerde 3.8
   kuşağı 3.6'nın önünde ve elde 3.8 kuşağından tek aday bu; 3.8-35B henüz yayınlanmadı).**
   **Bu bir ölçüm sonucu değildir** ve öyle yazılmıyor — 10 Ağustos'ta tam olarak o hata
   yapılmıştı. Kararın kendi sınırı da kayıtlı: kamuya açık ölçütler bizim ölçtüğümüz şeyi
   (Türkçe, GBNF ile kısıtlanmış tool seçimi, bu rol metni) ölçmüyor ve "büyük olan daha
   iyidir"in yanlış çıktığı bir örnek aynı gün görüldü (`Qwen3.6-35B-A3B`, MoE, aktif 3B —
   `docs/faz6-35b.md`). Risk kabul edildi.

   **Karar bugünkü işi geçerli kılıyor:** rol metni üç turda bu modelde yazıldı ve bu
   modelde benimsendi (`docs/faz6-27b-rol3.md`), yani yeniden koşulacak bir şey yok.
   **Model değişirse rol metni yeniden ölçülür** — prompt ve model birlikte ayarlanıyor,
   bu da aynı günün ölçülmüş dersi.

   **STT ve TTS açık kalıyor (sahibin ertelemesi).** Sahte STT ham PCM'i çözemez ve bunu
   sessizce yutmaz — açık maddeyi adıyla söyleyen bir hata yükseltir. Madde 4'ün gecikme
   hedefi ve madde 10 onlarla birlikte bekliyor.

   **Geri alma kaydı (2026-08-15):** bu madde 2026-08-10'dan beri "kapandı: Qwen3.6-35B-A3B"
   diyordu, ama sahip böyle bir kararı hiç vermemişti — ölçümlerin yanına yazılan bir
   çıkarım, kaydedilirken karara dönüşmüş. Ölçümler duruyor ve geçerli
   (`docs/faz2-olcum.md`, `docs/faz5-model-secimi.md`, `docs/faz6-olcum.md`); **iptal edilen
   şey ölçüm değil, ölçümden karar üretilmiş olması.** `faz5-model-secimi.md`'nin kendi
   sonucu da zaten "doğruluk karar veremedi" idi.

   **Bu madde hiçbir kodu engellemiyor** ve §19'un meta-kuralı burada bir istisna
   gerektirmiyor: sistemin hiçbir yeri model adına bakmıyor, adaptör `localhost:8080`'e
   konuşuyor ve model adı yalnızca rapora yazılıyor. Yani madde açık kalırken geliştirme
   sürebilir; kapanması için gereken şey bir ölçüm değil, sahibin kararıdır.

   **Karar verilmeden önce bilinmesi gerekenler:** VRAM gözlemleri (27B tek başına
   15628 MiB, 35B-A3B ancak `--n-cpu-moe 7` ile) STT/TTS seçilmeden anlamını kazanmıyor;
   ve `docs/faz6-olcum.md` sunucuda artık **Qwen3.8-27B-IQ4_XS** koştuğunu gösteriyor, yani
   ölçümlerin bir kısmı artık kurulu olmayan bir modele ait. **STT bilinçli olarak sahtede
   bırakıldı**: sistemin geri kalanı bitene kadar ses girişi ölçülmeyecek, dolayısıyla
   madde 4'ün gecikme hedefi ve madde 10 da onunla birlikte bekliyor. Sahte STT ham PCM'i
   çözemez ve bunu sessizce yutmaz — açık maddeyi adıyla söyleyen bir hata yükseltir.
3. Konuşmacı tanıma modeli, güven eşikleri, kayıt için gereken örnek sayısı (Faz 4).
   **Geçici kapı:** eşikler yokken kimlik `TANINMAYAN`'dır ve §10.2'ye göre hiçbir tool
   çalışmaz — yani sistem eşikler ölçülene kadar denenemez hâle gelirdi. Bu yüzden
   `MAYEN_ASSUME_OWNER` yapılandırma bayrağı var: açıkken gömüye bakılmadan her segment
   `SAHİP` sayılır ve her açılışta uyarı yazılır. **Kural 6 bozulmuyor**, çünkü yasak
   sahipliğin *sesle* verilmesine; buradaki kapı kabuktur ve fiziksel makine erişimi ister
   (madde 14'ün kurulum betiğiyle aynı gerekçe). Bayrak, konuşmacı tanıma gerçek olduğunda
   silinir — kalıcı bir yetki yolu değil, ölçüm beklerken açılmış geçici bir kapıdır.
4. İlk ses gecikmesi hedef değeri (Faz 2 sonrası).
5. İstemci ses formatı: PCM mi sıkıştırma mı (bant genişliği ölçümü).

**Karar bekleyenler:**

6. Wake word motoru ve kelime.
7. ✅ **Hava durumu sağlayıcısı: OpenWeatherMap.** Geliştirici anahtarı mevcut. Anahtar
   ortam değişkeninden/yapılandırmadan okunur ve **depoya girmez**; sistemdeki ilk sır
   budur, dolayısıyla sır yönetimi P1'de bir kez kurulur. Kullanılan uç ve plan
   yapılandırmada açıkça yazılır. Kota aşımı ve anahtar hatası §14 gereği sessizce
   yutulmaz — kullanıcıya bildirilir.
8. ✅ **Ders programı: depoda bir dosya** (YAML/TOML). Açılışta okunup veritabanına
   yüklenir. Dönemde bir kez değişir; sürümlenebilir olması yeterlidir, çalışma anında
   düzenlenebilir olması gerekmez.
9. ✅ **Wake-on-LAN hedef listesi: yapılandırma dosyası.** Ad → MAC eşleşmesi. Yeni cihaz
   eklemek bir satırdır; ayrı bir tablo ve CRUD tool'ları yazılmaz.
10. İngilizce TTS ses karakteri.
11. ✅ **Qt bağlayıcısı: PySide6** (LGPL, Qt'nin resmi bağlayıcısı — kapalı dağıtım
    zorunluluğu doğurmuyor). Opsiyonel bir kurulum ekstrası (`gui`): uçbirim istemcisi ve
    testler onu istemez. Qt'nin olay döngüsü ana iş parçacığında kalır, asyncio ayrı bir
    iş parçacığında koşar ve iki yön sinyal/`run_coroutine_threadsafe` ile bağlanır; ek bir
    köprü bağımlılığı (qasync) alınmaz. İlk sürüm yalnızca metin girdisi ve metin
    çıktısıdır — durum göstergesi ve bekleyen kişi yönetimi Faz 7'de kalır.
12. Yedekleme sıklığı, saklanacak yedek sayısı ve hedef konum.
13. Zamanlanmış görevlerde "kaçırılmış sayılma" toleransı.
14. ✅ **Sahip ataması: kurulum betiği (CLI).** Betik birkaç ses örneği toplar, profili
    sahip olarak işaretler ve sahip zaten tanımlıysa çalışmayı reddeder. GUI'ye bağımlı
    değildir, Faz 4'ten itibaren kullanılabilir. Kural 6 korunur: sahip kademesine giden
    yolun sesli kapısı yoktur; kabuk kapısı vardır ve o kapı fiziksel makine erişimi ister.
15. **Türkçe içeriğin İngilizce TTS'ten geçmesi.** Kişi isimleri, not gövdeleri ve ders
    adları kaçınılmaz olarak Türkçe kalacak; §2'nin "çıkış İngilizce" kararı bunları
    kapsamıyor ve İngilizce bir ses onları telaffuz edemez. Seçenekler: özel adlar için
    fonetik dönüşüm, ikinci bir Türkçe ses, ya da bilinçli kabul edilen bir kusur.
    Faz 2'de karara bağlanır.

Hangi maddenin hangi iş paketini engellediği `docs/PLAN.md`'nin sonundaki tablodadır.
Özetle: 7, 8 ve 9 birer tool gövdesini, 14 ise Faz 4'ü engeller. Geri kalanı iskeleti,
veri katmanını, politikayı, durum makinesini veya tool kayıt defterini engellemez.

---

## 20. Değişmez Kurallar

1. Veritabanının tek sahibi vardır; başka hiçbir süreç dosyayı açmaz.
2. Uygulama süreci model yüklemez; modeller kendi süreçlerinde ve arayüz arkasındadır.
3. Sistem promptu tur içinde değişmez. Değişken içerik daima önekin sonundadır.
4. Yetkilendirme koddadır. Prompt bir güvenlik sınırı değildir.
5. Onay serbest metinden anahtar kelimeyle çıkarılmaz. Zaman aşımı reddir.
6. Sahip kademesi sesle verilemez.
7. Kullanıcıya ait metin alanına sistem verisi (kimlik, politika) yazılmaz.
8. Model çıktısı asla kabukta çalıştırılmaz.
9. Bir tool tek dosyada tanımlanır.
10. Token sayısı tahmin edilmez, sayaca sorulur.
11. Bellek ve özetleme işleri aktif tur sırasında modelin sırasına girmez.
12. Her tur, her aşamasında iptal edilebilir. İptalin kapsamı turdur, kuyruğun tamamı değil.
13. Hiçbir hata sessizce yutulmaz.
14. Ölçülmemiş bir performans iddiası dokümana yazılmaz.
15. Aynı anda tek tur koşar; kapsam globaldir, cihaz başına değil.
16. Onay durumuna, onay cümlesi okunmadan önce girilir.
17. Her ses parçası bir `turn_id` taşır; istemci başka tura ait parçayı çalmaz.
18. Arka plan LLM işleri preempt edilebilir; tur kuyruğa girdiği anda iptal edilirler.
