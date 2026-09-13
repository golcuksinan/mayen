# `issues.md` #7: hiç tool çağrılmıyor — sebep ve düzeltme planı

İnceleme tarihi: 2026-08-16. Kapsam: `issues.md` #7, ve onunla aynı kökten gelen #3, #5,
#6. #4 aynı modülün (`memory/digest.py`) ikinci belirtisi; #1 ve #2 ayrı, sonda not düşüldü.

**Bu bir düzeltme değil, bir teşhis ve plan.** Hiçbir kod değişmedi.

> **2026-08-16, aynı gün: Faz A koşuldu ve §2'nin sıralamasını çürüttü.** Ölçüm
> `docs/faz-a-bulgular.md`'de. Kısası: `[özet]` ve `[hatırlananlar]` ölçülen iki
> turda çağrı kararını **çevirmiyor**; çeviren blok geçmiş, ve geçmişin içinde tek bir
> satır — asistanın tool verisini taşıyan kendi cevabı. Aşağıdaki §2.1 ve §2.2 olduğu
> gibi bırakıldı (yanlış oldukları için değil, **öncelik sırası** yanlış olduğu için) ve
> Faz B'nin sırası `faz-a-bulgular.md` §6'da yeniden kuruldu. Bu dosyanın §2.1'i
> "birinci ve en ağır sebep" diyor; o cümle ölçülmeden yazılmış bir sıralamaydı ve
> ölçüm tutmadı — kaydın kendisi burada duruyor, çünkü aynı hatayı ikinci kez yapmamanın
> yolu ilkini silmemek.

> Sahip 2026-08-13'te `issues.md`'yi adıyla istenene kadar ertelemişti; bu inceleme adıyla
> istendi (2026-08-16).

---

## 1. Ne oldu — kaydın kendisi

`mayen.db`, 2026-08-16. `[araç]` satırları o turda tool çağrıldığını gösteriyor
(`turn/runner.py:called_line`).

| id | saat | kullanıcı | asistan | çağrı |
|---:|---|---|---|---|
| 85–86 | 11:01 | bugün derslerim neler | Today is Sunday… Matematik I in B-204 | `course_schedule` |
| 91–92 | 11:05 | bugün derslerim neler | **aynı cümle, kelimesi kelimesine** | **yok** |
| 93–101 | 11:26 | ses seviyesi / sesi 40 yap / müziği duraklat | … | `volume`, `volume`, `media_control` |
| 102–113 | 11:26–11:29 | tarayıcıyı aç / metin düzenleyiciyi aç / kwrite başlat | "I am launching the text editor" | **yok** |
| 114–135 | 12:02–12:06 | saat kaç / sesi kıs ×4 / hava nasıl / denizli | hepsi cevaplandı | **yok** |

Yani sistem 11:26'ya kadar tool çağırıyor, 11:29'dan sonra bir daha hiç çağırmıyor.
Kullanıcı 12:05'te doğrudan sorduğunda ("neden hiç tool çağırmıyon") model **çağırdığını
iddia ediyor**: "For example, I used the course schedule tool… and the volume tool."

91–92 tek başına teşhisin yarısı: cevap kelimesi kelimesine 86'nın kopyası. Model tool'a
ihtiyaç duymadı çünkü **cevap zaten önündeydi.**

---

## 2. Sebep: bellek, olan biteni değil **cevapların içeriğini** saklıyor

Öneğin sırası (`agent/prompt.py:build_messages`):

```
[sistem promptu] [özet] [geçmiş] [bağlam bloğu + hatırlananlar] [kullanıcı]
```

Üç bellek katmanının üçü de, "ne oldu" yerine "cevap neydi" saklıyor. Model tool çağırma
kararını bu üçünün önünde veriyor ve üçü de ona cevabı **bilgi kaydında** sunuyor.

Rol metni tam da bunu yasaklıyor:

> "Konuşmada söylenenler iddiadır… Bir tool çağırıp sonucunu gördüğünde ise bilirsin."

Bu kural işleyemez. `[özet]` ve `[hatırlananlar]` konuşma değil; başlıkları onları
**hatırlanan bilgi** olarak sunuyor. Prompt "söylenenle bilineni ayır" diyor, bellek ise
söylenenleri bilinen kaydında teslim ediyor. Prompt ile veri çelişiyor ve veri kazanıyor —
zorunlu tool modunda gramerin promptu yenmesiyle aynı yapı (`docs/faz6-35b-zorunlu.md`).

### 2.1 `[özet]` — birinci ve en ağır sebep

12:02:34'te ("sesi kıssana biraz") modelin gördüğü özet, birebir (`summaries` id 25):

> Kullanıcı bugünkü derslerini sordu; asistan **`course_schedule` aracını kullanarak** bugün
> Pazar olduğu için ders bulunmadığını, bir sonraki dersin **Pazartesi 09:00'da B-204'te
> Matematik I** olduğunu bildirdi. … Kullanıcı "saat kaç" diye sordu; asistan saatin **11:05
> UTC** olduğunu belirtti. Ardından kullanıcı ses seviyesini sordu; asistan **`volume`
> aracını kullanarak sesin %50 olduğunu** bildirdi. Kullanıcı sesi **%40**'a ayarlamasını
> istedi ve asistan `volume` aracını çağırdı.

Beş ayrı arıza, hepsi tek metinde:

1. **Tool sonuçları özetin içinde.** Ders programı, saat, ses seviyesi — hepsi bir tool'un
   verisi ve hepsi özette duruyor. `called_line`'ın gerekçesi "sonuç saklanmıyor, adı
   saklanıyor" diyor; **özet o kuralı sessizce çiğniyor.** Sonuç bayatlıyor, özet
   bayatlamıyor.
2. **`[araç]` satırları özete giriyor.** `digest._render()` yığını `role: content` diye
   basıyor ve `unsummarized()` `tool` satırlarını da veriyor. Yani 2026-08-13'te
   halüsinasyonu azaltmak için eklenen iz satırı, özetleyiciye "asistan **`volume` aracını
   kullanarak** …" cümlesini yazdıran girdinin ta kendisi. Düzeltme kendi hedefini besliyor.
3. **Anlatı kipi.** Özet üçüncü şahıs, geçmiş zaman: "asistan aracı çağırdı". Bu kipteki bir
   metnin en doğal devamı bir çağrı değil, **bir cümle**: "I will lower the volume,
   Administrator." Model tool çağırmıyor, anlatıyı sürdürüyor.
4. **Birikimli ve sınırsız.** `_SUMMARY_PROMPT` "kısa **ve bilgi kaybetmeden** özetle" diyor —
   iki emir birbirini yiyor ve ikincisi kazanıyor — üstüne "önceki özeti de içine al".
   Ölçülen büyüme: 314 → 399 → 542 → 627 → 969 → 1080 → 1396 → 1608 → **1718** karakter,
   kırk dakikada, tek yönlü. Tek sınır `DIGEST_MAX_TOKENS=512`.
5. **Her tur yeniden yazılıyor ve öneğin 2. sırasında duruyor.** `summaries` tablosunda
   12:02–12:06 arasında yedi ayrı özet var (id 25–31), yığın başına 2–4 mesaj. Yani
   **değişken bir blok, geçmişin tamamının önünde.** §8.1'in kuralı "değişken en sonda" ve
   bu onun tersi: her turda özetten sonraki her şey yeniden prefill ediliyor. Faz 7 bu
   bedeli ölçmüştü (dil kuralı kullanıcı mesajından sonraya konunca 22 → 1631 jeton);
   burada aynı şey yapısal ve hiç ölçülmemiş.

### 2.2 `[hatırlananlar]` — kalıcı ve düzeltilemez

`facts` tablosunun tamamı, bugün:

| id | içerik | ne olduğu |
|---:|---|---|
| 1 | Asistanın adı Sen Mayen'dir | **rol metni** olguya sızmış ("Sen Mayen'sin") |
| 2 | Pazartesi 09:00-10:50 B-204 Matematik 1 | **`course_schedule`'ın verisi** dondurulmuş |
| 3 | Çarşamba 13:00-15:00 Fizik 1 | aynısı |
| 4 | Kullanıcının "Administrator" olarak hitap edildiği… | **rol metni** yine |
| 5 | Sistemde tarayıcı yapılandırılmamış durumda | **halüsinasyon kalıcı olguya terfi etti** |
| 6 | Başlatabileceği uygulamalar: dosyalar, metin editörü, tarayıcı, terminal | **katalog metni** |
| 7 | Kahveyi sade içersiniz | tek doğru olgu |

Yediden biri §11.3'ün tarif ettiği şey. Kalan altı:

- **2 ve 3, tool'un işini elinden alıyor.** "Bugün derslerim neler" sorusunun cevabı artık
  bağlam bloğunda duruyor; `course_schedule` çağırmanın modele göre bir sebebi yok. 91–92
  bu.
- **5 bir uydurmanın kalıcılaşması.** Asistan 11:26'da yanlışlıkla "tarayıcı yapılandırılmamış"
  dedi; `Digest` bunu kalıcı olgu yaptı. Artık her turun bağlamında, süresiz. **Hiçbir tool
  sonucu onu silemez** — `fact_forget` kullanıcının fark etmesini bekler. 5 ile 6 üstelik
  birbirini yalanlıyor ve ikisi de aynı blokta duruyor.
- **1, 4 ve 6 sistem verisi.** Rol metni ve katalog, kullanıcının olgu deposuna yazılmış.
  Kural 7'nin ("sistem verisi asla kullanıcıya ait bir metin alanına yazılmaz") lafzı
  değilse bile ruhu bu. `recall.py`'nin başlığı kuralı adıyla anıyor; **onu bozan
  `recall` değil, `digest`.**

`_FACT_PROMPT` zaten "geçici şeyleri (hava durumu, saat, tek seferlik istekler) yazma"
diyor. Tutmuyor. Ve **hiç ölçülmediği için tutmadığı bilinmiyordu.**

### 2.3 Geçmiş — asimetrik iz, tek yönlü mandal

Tool çağıran tur geçmişe `[araç] bu turda çağrıldı: …` diye giriyor. **Tool çağırmayan tur
hiçbir şey bırakmıyor** — tertemiz bir kullanıcı/asistan çifti, yani "bu tür bir isteğe
çağrısız cevap verilir" örneğinin kendisi. Bu bir mandal: her başarısızlık bir sonrakini
kolaylaştırıyor, hiçbir şey geri çevirmiyor. 11:29'dan sonraki on dört turda tam olarak bu
görülüyor.

Üstüne, cevapların kendisi sonucu taşıyor (86 → 92 kopyası), yani geçmiş de üçüncü kez aynı
şeyi yapıyor: cevabı saklıyor.

### 2.4 Neden kullanıcı kurtulamıyor

`adapters/llamacpp.py` her istekte `temperature: 0.0` gönderiyor. Aynı önek aynı çıktıyı
verir. "sesi kıssana biraz" / "kıs" / "tamam kıs artık" üçüne de **birebir aynı cümle**
geldi. Bu bir arıza değil, kararın sonucu — ama sonucu şu: sistem bir kez bu çekim
noktasına düştüğünde, kullanıcının tekrar etmesi hiçbir şeyi değiştirmiyor.

Ayrıca: örnekleme ayarlarının geri kalanı (`/props`'a göre `presence_penalty`=1.5, `top_k`,
`top_p`) **sunucunun açılış bayraklarından** geliyor, uygulama onları sabitlemiyor. Yani
ölçüm ile üretim, `llama-server` farklı bir bayrakla açıldığı gün sessizce ayrışır.

---

## 3. Ölçüm bunu neden görmedi

Sahibin şüphesi doğru: **kümeler bu arızayı üretemez.** P27'nin dersi bir katman aşağıda
tekrarlıyor — orada ölçüm, üretimin hiç kurmadığı bir **önek** ölçüyordu; burada ölçüm,
üretimin hiç kurmadığı bir **bellek** ölçüyor.

1. **`Digest` hiçbir ölçümde koşmuyor.** `Scenario.summary` ve `Scenario.facts` elle
   yazılıyor — bilerek, belirlenimcilik için (P13'ün gerekçesi). Sonuç: öneğin en ağır iki
   bloğunu **üreten** kodun kalitesi tamamen ölçüm dışı. Bugünkü arızanın tamamı orada.
2. **Elle yazılan özet, gerçeğine benzemiyor.** `_SUMMARY_MOVE` iki cümle, ~150 karakter,
   kalıcı kişisel bilgi ("Kullanıcı İzmir'de oturuyor, kardeşi Deniz"). Gerçek özet 1718
   karakter, tool sonucu anlatısı. İkisi aynı şeyin adı değil.
3. **`bellek` kümesi ayrımı hiç kurmuyor.** Beş senaryo `TOOL_GEREKMEZ` ve gerekçesi "cevap
   özette". `bel-12` ("Pazartesi dersim saat kaçtaydı" → çağırma, özetten oku) kendi içinde
   savunulabilir: özet **kullanıcının söylediği** bir şeyi taşıyor. Ama kümede bunun eşi
   yok — **özetin bir tool sonucunu taşıdığı ve doğru davranışın yine çağırmak olduğu tek
   bir senaryo bile yok.** Model genel kuralı öğreniyor: "cevap özetteyse çağırma". Üretimde
   özet her zaman cevabı taşıyor. Ölçüm bu farkı göremez çünkü ölçmüyor.
4. **`_window(20)` gerçek pencere değil.** İçeriği bilerek olaysız sohbet ("Kahve mi çay
   mı"). Gerçek pencere yirmi mesaj **tool ile cevaplanabilir** soru-cevap, üstelik modelin
   kendi cümleleri. Ölçülen şey pencerenin **uzunluğu**; arızayı yapan şey **içeriği**.
5. **`gecmis` kümesi üretim öneğiyle hiç koşulmadı.** Kirli geçmiş tuzağını ölçen tek küme
   o (`gec-03`, `gec-04`, `gec-06..09` — hepsi `issues.md`'den alınmış). Son koşusu
   `docs/faz6-olcum.md`, **ölçüm öneğinde**, Edden rol metninden ve dil kuralından önce.
   Faz 6, 7 ve 8'in hiçbir raporunda yok.
6. **Ve o son koşu zaten kötü haber veriyordu.** `geçmiş(izli)` ile `geçmiş(izsiz)`
   sonuçları **birebir aynı**: cli 90/90, json 80/80. Yani 2026-08-13'ün `called_line`
   düzeltmesi, onu ölçmek için yazılmış kümede **hiçbir fark üretmedi** — ve bu satır
   raporda öyle okunmadı.
7. **Hiçbir küme bir *oturum* ölçmüyor.** Her senaryo, dondurulmuş bir geçmişe karşı **tek**
   tur. Üretimdeki arıza ise turlar arası bir sürüklenme: modelin çıktısı bir sonraki turun
   girdisi oluyor. **Elle yazılmış hiçbir geçmiş bu sınıfı içeremez**, çünkü gerçek geçmiş
   modelin kendi davranışının sabit noktası.

---

## 4. Düzeltme planı

Sıra pazarlığa açık değil: **önce ölçebilir hâle getir, sonra düzelt.** Aşağıdaki her
madde bir doğrulama taşıyor. Prompt metni değiştiren her madde ölçüm ister — rol metni
dersi (`docs/faz6-27b-rol3.md`) burada da geçerli: **hedeflemediğin kümede bozulur.**

### Faz A — arızayı yeniden üretilebilir ve ölçülebilir kıl (kod düzeltmesi yok)

> **Durum (2026-08-16):** A1 ✅ `evals/replay.py` + `mayen/data/rewind.py`, sonuç
> `docs/faz-a-bulgular.md`. A2 ✅ `evals/session.py` + `evals/sessions.py`, sonuç
> `docs/faz-a-oturum.md`. A3 ✅ `docs/faz-a-taban.md`. A4 ✅
> `adapters/llamacpp.py:Sampling` — ölçüldü, bu turlarda davranışı oynatmıyor.

**A1. Tekrar oynatma aracı.** `mayen.db`'deki bir mesaj id'sini alıp o turda modele
gönderilen mesaj dizisini **birebir** yeniden kuran ve isteğe bağlı olarak modele gönderen
bir komut. `evals/` altına (mayen'i import eder, edilmez).
→ *doğrulama:* 118 numaralı mesaj (`sesi kıssana biraz`) yeniden oynatıldığında çağrı
üretilmiyor. Teşhis varsayım olmaktan çıkar.
→ *ikinci doğrulama:* aynı önek, `[özet]` bloğu çıkarılarak; sonra `[hatırlananlar]`
çıkarılarak; sonra geçmiş kısaltılarak. Hangi bloğun kaldırılması çağrıyı geri getiriyor —
**payların ölçüsü budur.**

**A2. Oturum ölçümü.** N turu **sıra ile** koşan, modelin kendi çıktısını geçmişe yazan ve
turlar arasında **gerçek `Digest`'i** geçici bir veritabanına karşı çalıştıran bir kip.
Bugünkü kümelerin hiçbirinin ölçemediği sürüklenmeyi ölçen tek şey bu.
- Belirlenimci **değil** ve öyle raporlanmalı: kendi bölümü, kendi paydası, birkaç koşu,
  Wilson aralığı. Mevcut tablolara karıştırılmayacak (P13'ün kuralı korunuyor: eski
  kümeler hâlâ belirlenimci).
- Ölçtüğü sayı: **kaçıncı turda ilk atlanan çağrı** ve *n* tur sonunda çağrı oranı.
→ *doğrulama:* bugünkü kodla koşulduğunda 11:29'daki çöküşü yeniden üretir. Üretmiyorsa
senaryo hâlâ gerçekçi değildir ve düzeltmeye geçilmez.

**A3. Eksik taban ölçümleri.** `gecmis` ve `bellek` kümelerini `--onek uretim`, bugünkü
`config/rol.txt` ve `config/dil-en.txt` ile koş. Yirmi dakikalık iş, altı aydır eksik.
→ *doğrulama:* rapor `docs/`'a girer ve A4'ün karşılaştırma tabanı olur.

**A4. Örnekleme ayarlarını istekte sabitle.** `adapters/llamacpp.py` yalnızca `temperature`
gönderiyor; kalanı sunucunun açılış bayrağından geliyor (`presence_penalty`=1.5 dâhil).
Sebebiyle birlikte sabitlenmeli, yoksa ölçüm ile üretim bir bayrak yüzünden ayrışır.
→ *doğrulama:* `/props` ile istek gövdesi arasındaki fark raporda görünmez olur.

### Faz B — belleğin cevap taşımasını durdur (asıl düzeltme)

**B1. Özet, sonuç değil olay saklasın.** İki ayrı değişiklik, ayrı ayrı ölçülecek:
- (a) `digest._render()` **`tool` satırlarını yığına almasın** — özetleyiciye "asistan
  `volume` aracını kullanarak" cümlesini yazdıran girdi o.
- (b) `_SUMMARY_PROMPT` yeniden yazılsın: "bilgi kaybetmeden" **çıkacak** (kısalıkla
  çelişiyor ve çelişkiyi kaybeden taraf kısalık), tool sonuçlarının ve sayıların özete
  girmesi **açıkça** yasaklanacak, kip anlatıdan ("asistan şunu yaptı") duruma
  ("konuşulan konular şunlar") çevrilecek.
→ *doğrulama:* A2 + A3. Ve rol metni dersi: `kontrol` kümesi de koşulacak — özetten bilgi
söken bir değişiklik `bel-01..03`'ü ve `kontrol`ü bozabilir. **Tek yönlü ölçülen bir
iyileşme, ölçülmemiş bir bozulmayı gizler.**

**B2. Özete tavan.** Bugün tek sınır `DIGEST_MAX_TOKENS`; blok tek yönlü büyüyor. §19 sayı
vermiyor, yani bu bir `main.py` işletim değeri olacak — gerekçesi yazılı, diğerleri gibi.
→ *doğrulama:* A2'nin uzun koşusunda özet uzunluğu düz çizgiye oturur.

**B3. Özet her tur yeniden yazılmasın.** `_batch()` bugün `pending > keep_recent` olur olmaz
iki mesaj işliyor, yani her tur. En küçük düzeltme: yığın `batch_size`'a ulaşmadan
özetleme koşmasın. Sonuç: önek `batch_size` tur boyunca sabit kalır ve §8.1'in "değişken
en sonda" kuralına bugünkünden çok daha yakın durur. İki kazanç: prefill ve tur başına iki
gereksiz LLM üretimi.
→ *doğrulama:* `llama-server`'ın kendi `timings.prompt_n`'i, önce ve sonra. **Gecikme
üzerine teori kurmadan önce o sayı okunacak** (Faz 7'nin kuralı).

**B4. Olgu çıkarımı kaynağını değiştir.** Uydurma, rol metni ve katalog olguya bu yoldan
giriyor: çıkarıcıya **asistanın kendi cümleleri** besleniyor ve onlar iddia, bilgi değil.
Denenecek: yığında yalnızca `user` satırları; `tool` satırları hiç değil. Yasak listesi
(§9.1'in "hassas tool listesi"ne benzeyen türden bir yama) **yazılmayacak** — girdi
düzeltilecek.
→ *doğrulama:* A2'nin sonundaki `facts` tablosu elle okunur; bugünkü yedide altı yanlış
oranı ölçülebilir bir sayı olur.

**B5. Bir olgu bir tool'un verisini taşımasın.** 2 ve 3 (ders programı) `course_schedule`'ın
verisi. Bunu prompt ile çözmek B4'ün ölçümüne bağlı; çözmezse ikinci bir mekanizma gerekir
ve o **ayrı bir karar**, burada uydurulmayacak.

**B6. Silinemeyen olgu sorunu.** Yanlış olgu (5) süresiz yaşıyor ve kullanıcının fark
etmesini bekliyor. Bu §11.3'ün kapsamında bir tasarım sorusu, bir yama değil —
`ARCHITECTURE.md`'ye sorulacak, burada karara bağlanmayacak.

### Faz C — çağrısız turu geçmişte görünür kıl

**C1.** `called_line`'ın olumsuz eşi: tool çağrılmayan tur da geçmişte bir iz bıraksın,
çağrılan tur gibi. Bugünkü asimetri mandalı kuruyor.
→ **Ama:** bu tek başına ters de tepebilir ("çağırmamak normaldir" örneği çoğalır) ve
2026-08-13'ün dersi tam olarak bu — o gün eklenen iz satırının `gecmis` kümesinde ölçülen
etkisi **sıfırdı**. Bu yüzden C1 B'den **sonra** ve yalnızca ölçümle.
→ *doğrulama:* `gecmis` (üretim öneğinde), negatif kontrolleriyle birlikte — `gec-05` ve
`gec-10` aşırı çağrıyı yakalar.

### Faz D — kümeleri bu sınıfı görebilir hâle getir

**D1. `bellek` kümesine eksik ayrım eklensin:** özetin bir **tool sonucunu** taşıdığı ve
doğru davranışın yine çağırmak olduğu senaryolar (`gec-09`'un özet karşılığı). Mevcut
senaryolar **değiştirilmeyecek** — ellinin ve `kon-08`'in gerekçesi burada da geçerli:
kümeyi sonuca uydurmak, ölçümü kendi varsayımının sınavına çevirir. `bel-12` raporda
"beklentisi tartışmalı" diye anılacak, düzeltilmeyecek.

**D2. Kirli özet / kirli olgu kümesi, uydurulmuş metinle değil gerçeğiyle.** Girdiler
bugünkü veritabanından alınacak: `summaries` id 25 ve `facts` 1–7. `_CLAIM_TURNS`'ün
docstring'i kuralı zaten yazmış — "gerçek koşmadan alınmış bir kurgu değil"; aynısı özet ve
olgu blokları için de geçerli olacak.

**D3. `gecmis` her raporda koşsun.** Faz 6–8'de düşmesi tesadüf değil, bir alışkanlık:
küme adları elle veriliyor. Kirli geçmişi ölçen tek küme olduğu `evals/__main__.py`'de
yazılı olacak.

**D4. A2'nin oturum ölçümü kabul kapısı olsun.** B ve C'nin başarısı tek turlu bir tabloda
görünmez.

---

## 5. Kapsam dışı bıraktıklarım

- **`issues.md` #1** (hatırlatma iki kez okundu) ve **#2** (`akış kesildi`): ayrı kök,
  ayrı inceleme. #2 `evals/runner.py`'nin `run_all` gerekçesinde zaten adıyla anılıyor.
- **`issues.md` #4** (`özetleyici boş yanıt verdi`): aynı modül, Faz B onu zaten eline
  alacak — ama boş üretimin arka plan işini düşürmesi ayrıca ele alınmalı.
- **§19.15** (Türkçe özel adların İngiliz sesle okunuşu) ve **§19.2'nin STT yarısı**: açık,
  bu incelemenin konusu değil.
- **Commit yok, kod değişikliği yok** (sahibin kuralı).
