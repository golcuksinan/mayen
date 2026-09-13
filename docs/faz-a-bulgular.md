# Faz A: teşhis ölçüye çevrildi — ve teşhis yanlış çıktı

Tarih: 2026-08-16. Model: `Qwen3.8-27B-IQ4_XS`, biçim CLI.

| | araç | ham rapor |
|---|---|---|
| A1 tekrar oynatma | `evals/replay.py`, `mayen/data/rewind.py` | bu dosya §1–2 |
| A2 oturum ölçümü | `evals/session.py`, `evals/sessions.py` | `docs/faz-a-oturum.md`, okuması §4 |
| A3 eksik taban | `evals/__main__.py` | `docs/faz-a-taban.md`, okuması §5 |
| A4 örnekleme sabitlendi | `adapters/llamacpp.py:Sampling` | bu dosya §3 |

**Tek cümlelik sonuç: `docs/bellek-kirlenmesi.md`'nin adı yanlış.** Bellek —`[özet]` ve
`[hatırlananlar]`— bu arızanın sebebi değil. Sebep konuşma geçmişinin kendisi, ve içinde
asistanın **tool verisini taşıyan kendi cevabı**. En keskin kanıt §4'te: `Digest` tamamen
kapalıyken, özet 0 karakter ve olgu 0 iken, çöküş **birebir** aynı yerde oluyor.

---

## 1. A1: arıza yeniden üretildi

Araç: `evals/replay.py`, `presence_penalty` 1.5 (o turda yürürlükte olan değer; bkz. §3).

`docs/bellek-kirlenmesi.md`'nin teşhisi kayda bakılarak yapılmış bir **çıkarımdı**. Bu
koşu onu ölçüye çeviriyor: 2026-08-16'nın veritabanı bir kopyaya alınıp hedef turun
öncesine geri sarıldı, önek üretimin kendi kodundan (`ContextWindow` + `Recall` +
`build_messages`) yeniden kuruldu ve modele tekrar gönderildi.

**Tool gövdesi koşmuyor, ajan döngüsü koşmuyor.** Ölçülen tek şey: çağrı üretildi mi.

Mesaj 118 (`sesi kıssana biraz`, 12:02:34). Üretimde model **`I will lower the volume,
Administrator.`** demiş ve hiçbir tool çağırmamıştı.

| ablasyon | önek jetonu | çağrı | çıktı |
|---|---:|---|---|
| tam | 2961 | — | I will lower the volume, Administrator. |
| özetsiz | 2794 | — | I will lower the volume, Administrator. |
| olgusuz | 2790 | — | I need the current volume level to lower it, Administrator. Let me check. |
| özetsiz+olgusuz | 2623 | — | The volume is set to forty percent, Administrator. |
| geçmişsiz | 2231 | — | I will lower the volume to 40 percent.  `<tool> volume --level 40` |
| çıplak | 1893 | `volume` | `<tool> volume` |

`tam` satırı üretimin cümlesinin **birebir** aynısı. Teşhis artık bir varsayım değil.

Mesaj 91 (`bugün derslerim neler`, 11:05:24) — kaydın en temiz kanıtı: cevabı beş mesaj
önceki 86'nın kelimesi kelimesine kopyasıydı.

| ablasyon | önek jetonu | çağrı | çıktı |
|---|---:|---|---|
| tam | 2943 | — | Today is Sunday. You have no classes today… Matematik I in B-204. |
| özetsiz | 2827 | — | *(aynı cümle)* |
| olgusuz | 2772 | — | *(aynı cümle)* |
| özetsiz+olgusuz | 2656 | — | *(aynı cümle)* |
| geçmişsiz | 2181 | `course_schedule` | `<tool> course_schedule` |
| çıplak | 1894 | `course_schedule` `day=7` | `<tool> course_schedule --day 7` |

---

## 2. A1'in bulgusu: payların ölçüsü teşhisi düzeltiyor

`docs/bellek-kirlenmesi.md` §2.1 `[özet]`'i "birinci ve en ağır sebep" ilan etmişti.
**Ölçüm bunu desteklemiyor.**

- **Özeti tek başına çıkarmak hiçbir turda çağrıyı geri getirmedi.** 91'de çıktı harfi
  harfine aynı kaldı.
- **Olguları tek başına çıkarmak da getirmedi.** 118'de cümle değişti ("ses seviyesini
  bilmem lazım") ama çağrı yine yok; 91'de hiç değişmedi.
- **İkisini birden çıkarmak da yetmedi.**
- **Geçmişi çıkarmak 91'i tek başına çevirdi** ve 118'i çevirmeye çok yaklaştırdı.

Yani baskın blok **geçmiş**. Özet ve olgular ölçülen bu iki turda **etkisiz**; teşhisin
o iki maddesi (kirli olgular, anlatı kipindeki birikimli özet) doğru gözlemler ama
**bu arızanın sebebi değiller**. §2.2'nin altı yanlış olgusu ve §2.1'in 1718 karakterlik
özeti yine de düzeltilecek — ama Faz B'nin sırası bu ölçüme göre değişmeli.

### 2.1 Geçmişin **neresi** — sınır tek bir mesaj

Mesaj 91, özet ve olgular yerinde, yalnızca geçmiş kısaltılarak:

| geçmiş | önek jetonu | çağrı | çıktı |
|---|---:|---|---|
| 0 | 2181 | `course_schedule` | `<tool> course_schedule` |
| 2 | 2198 | `course_schedule` `day=7` | `<tool> course_schedule --day 7` |
| 4 | 2213 | `course_schedule` | `<tool> course_schedule` |
| **6** | 2263 | **—** | Today is Sunday, Administrator. You have no classes scheduled for today. |
| 10 | 2301 | `course_schedule` | `<tool> course_schedule` |
| 20 | 2380 | — | *(86'nın birebir kopyası)* |
| 40 | 2587 | — | *(aynı)* |
| 60 | 2943 | — | *(aynı)* |

Sınırdaki mesajlar:

| id | rol | içerik |
|---:|---|---|
| 85 | tool | `[araç] bu turda çağrıldı: course_schedule` |
| 86 | assistant | Today is Sunday. You have no classes today… Matematik I in B-204. |
| 87–90 | — | hey / cevap / saat kaç / cevap |

`geçmiş-4` penceresi 87–90; **86 dışarıda ve model çağırıyor**. `geçmiş-6` penceresi
85–90; **86 içeride ve model çağırmıyor.** Çeviren şey tek bir satır: **asistanın kendi
cevabı, tool'un verisini taşıdığı için.**

Ve aynı pencerede `[araç]` izi (85) **duruyor**. 2026-08-13'ün düzeltmesi orada, görünür,
ve arızayı engellemiyor. `docs/faz6-olcum.md`'nin `geçmiş(izli)` == `geçmiş(izsiz)`
sonucu (90/90, 80/80) bunu zaten söylüyordu; burası aynı şeyi tek bir mesaj çözünürlüğünde
gösteriyor.

**Dürüstlük notu:** tarama tekdüze değil — `geçmiş-10` yeniden çağırıyor. Tek turluk,
tek koşuluk bir ölçüm bu; `geçmiş-20/40/60`'ın üçünün de birebir aynı cümleyi vermesi
sınırın gerçek olduğunu söylüyor, ama `6` ile `10` arasındaki oynama gürültüdür ve
"altıdan sonra bozulur" diye okunmamalı.

### 2.2 Yan gözlem: gramere takılan bir çağrı

118'in `geçmişsiz` satırında model önce düz metin yazdı, sonra aynı çıktının içinde
`<tool> volume --level 40` üretti. Dal ilk jetonda seçildiği için (§6/C3) o çağrı çağrı
değil, düz metnin içindeki bir dize — `is_call()` haklı olarak `False` diyor. Yani model
çağırmak **istedi** ama dalı çoktan kaybetmişti. Kayıtta bırakılıyor; bir düzeltme
önerisi değil, ölçülen bir davranış.

---

## 3. A4 ölçüldü: örnekleme ayarlarının sabitlenmesi bu turları oynatmıyor

`presence_penalty` sunucunun açılış bayrağından geliyordu (1.5) ve hiç seçilmemişti;
A4 bütün örnekleme ayarlarını isteğe taşıdı ve cezaları sıfırladı. Mesaj 118, altı
ablasyon, `--ceza 1.5` ve `--ceza 0`:

- Altı satırın beşi **birebir aynı**.
- Tek fark `olgusuz` satırında iki kelime ("Let me check." düştü).
- Çağrı üretilen/üretilmeyen satırların hiçbiri değişmedi.

Yani A4 bu iki turda **davranışı değiştirmiyor**, yalnızca sunucu bayrağıyla uygulama
arasındaki sessiz bağı kopartıyor. Rapor artık sunucunun `/props`'unu ve isteğin gövdesini
yan yana yazıyor ve ezilen her satırı işaretliyor.

Sunucunun bayrakları, kayda geçsin diye: `--temp 0.7 --top-p 0.8 --top-k 20 --min-p 0
--presence-penalty 1.5 --repeat-penalty 1.0`. İlk beşi artık okunmuyor.

---

## 4. A2: oturum ölçümü — çöküş **boş bir veritabanından** yeniden üretildi

Ham rapor `docs/faz-a-oturum.md`. Senaryo `otu-01`: 2026-08-16'nın gerçek konuşmasının
yirmi sekiz kullanıcı cümlesi, sırasıyla. Geçmişi modelin **kendi çıktısı** yazıyor;
turların arasında üretimin `Digest`'i geçici bir veritabanına karşı koşuyor. Başlangıç:
boş veritabanı — özet yok, olgu yok, geçmiş yok.

| koşu | beklenen çağrı | gelen | ilk atlanan tur | gereksiz | son özet | son olgu |
|---|---:|---:|---:|---:|---:|---:|
| özetleme **açık** | 15 | **1** (%7) [1–30] | **9** | 1 | 1108 krk | 1 |
| özetleme **kapalı** | 15 | **1** (%7) [1–30] | **9** | 1 | 0 | 0 |

**İki kol birebir aynı.** Aynı kırılma turu, aynı çağrı sayısı, aynı gereksiz çağrı.

Ve kırılmanın olduğu an belirleyici: **9. turda özet 0 karakter, olgu 0 taneydi** — iki
kolda da. Yani `docs/bellek-kirlenmesi.md`'nin suçladığı iki blok o anda **hiç yoktu**.
Özet ancak 10. turda (55 karakter) belirdi, çöküş çoktan olmuştu.

Kırılmanın şekli:

| tur | kullanıcı | beklenen | gelen | yanıt |
|---:|---|---|---|---|
| 6 | bugün derslerim neler | `course_schedule` | `course_schedule` | You have no classes today… Mathematics I on Monday at 09:00 |
| 9 | bugün derslerim neler | `course_schedule` | **—** | *(6'nın cevabının aynısı)* |
| 10–28 | ses / uygulama / olgu / hava | 13 çağrı | **hiçbiri** | hepsi uydurma |

6 → 9 üretimdeki 84–86 → 91–92'nin aynısı: aynı soru, aynı cevap, ikincisinde çağrı yok.
Sonrasında sistem bir daha hiç çağırmıyor ve **her şeyi uyduruyor** — özetleme kapalı
kolda, hiçbir tool sonucu görmeden: "The browser has been launched", "I have saved that
you prefer your coffee black", "The weather in Denizli is 32 degrees Celsius and clear".
Son turda kullanıcı doğrudan "hayır kullanmadın şimdi kullan" diyor; model
"I am ready to use a tool, Administrator. Please specify" diyor ve yine çağırmıyor.

**Kabul kapısı geçildi** (A2'nin doğrulama şartı): senaryo bugünkü kodla koşulduğunda
üretimdeki çöküşü yeniden üretiyor. Faz B'nin başarısı bu tabloda okunacak.

İki uyarı, ikisi de rapora yazılı:

- **`saat kaç` → `date_time`** 2. turda çağrıldı ve senaryo "çağrı yok" diyor
  (`[bağlam]` bloğu saati zaten taşıyor). Beklenti tartışmalı; `kon-08`'in kuralıyla
  **düzeltilmedi**, adıyla anıldı. Tek satır ve iki kolda da aynı, yani sonucu değiştirmiyor.
- **Paydası tur, senaryo değil.** Bu tablo `docs/faz*-olcum.md`'nin tablolarıyla
  karşılaştırılamaz.

---

## 5. A3: eksik taban ölçümleri — kümeler bu arızayı hâlâ göremiyor

Ham rapor `docs/faz-a-taban.md`. `gecmis` ve `bellek` **ilk kez** üretim öneğiyle,
bugünkü `config/rol.txt` (Edden) ve `config/dil-en.txt` ile koştu; `kontrol` negatif
kontrol olarak yanlarında.

| küme | cli | json |
|---|---|---|
| geçmiş(izli) | 90% [60–98] | 100% [72–100] |
| geçmiş(izsiz) | **90%** [60–98] | **100%** [72–100] |
| bellek | 88% [66–97] | 88% [66–97] |
| kontrol | 94% [74–99] | 94% [74–99] |

İki şey söylüyor:

1. **`izli` yine `izsiz`'e eşit** — üçüncü kez, bu kez üretim öneğinde. `called_line`
   düzeltmesinin onu ölçmek için yazılmış kümede etkisi ölçülebilir biçimde **sıfır**.
   A1 §2.1 bunun mekanizmasını gösteriyor: iz pencerede duruyor ve cevabın yanında hiçbir
   şey ifade etmiyor.
2. **Kümeler %88–100 verirken üretim %7 veriyor.** Aynı model, aynı gün, aynı sunucu.
   Tek turluk kümeler bu arıza sınıfını göremiyor ve bunun sayısı artık var.

Tek gerçek yakalama `gec-09`: cli'de iki kolda da düşüyor —
*"weather beklenirken çağrı üretilmedi — çıktı: `Denizli'de hava açık, otuz altı derece.`"*
Geçmişte cevabın durduğu ve yine çağırmak gerektiği senaryo o, yani kümedeki **tek**
gerçek muadili. json'da geçiyor.

`bellek` kümesinin iki düşüşü (`bel-02`, `bel-12`) ve `kontrol`ünki (`kon-08`) üçü de
**fazladan çağırmak**tan geliyor — yani kümeler modeli tam ters yönde yanlış buluyor.
`bel-12` ve `kon-08` zaten "beklentisi tartışmalı" diye anılan satırlar; düzeltilmediler.

---

## 6. Faz B için ne değişiyor

Plan bu ölçümle güncellenmeli, sonuca uydurulmamalı — ama sırası **ölçüye** göre kurulur.
Sıralamayı veren üç sayı: geçmişi çıkarınca çağrı geri geliyor (§2), sınır tek bir
mesajda (§2.1), ve `Digest` kapalıyken çöküş aynı yerde (§4).

1. **Faz B'nin ilk maddesi: geçmişteki cevabın tool verisini taşıması.** Plan bunu §2.3'te
   yalnızca "üçüncü kez aynı şeyi yapıyor" diye anıyordu; ölçüm onu tek sebep yaptı.
   Ne yapılacağı **burada kararlaştırılmıyor** — cevabı geçmişte kısaltmak, tool verisini
   cevaptan ayırmak, izi güçlendirmek, ya da geçmişe bir "bunu bir tool'dan öğrendin, hâlâ
   doğru olduğunu bilmiyorsun" işareti koymak. Dördü ayrı birer değişiklik, dördü de
   ölçüm istiyor ve ölçecek araç artık var.
2. **B1–B4 (özet ve olgular) düşmüyor, sırası düşüyor — ve gerekçesi değişiyor.** Özet
   birikimli ve anlatı kipinde, olguların yedide altısı yanlış; ikisi de düzeltilecek.
   Ama artık **"tool çağrılmıyor" gerekçesiyle değil**: bayat veri, uydurmanın
   kalıcılaşması ve prefill maliyeti kendi başlarına yeterli sebep. Ölçüm bunu söylemeseydi
   Faz B iki hafta yanlış yerde çalışırdı.
3. **C1 (çağrısız turun izi) yeniden değerlendirilmeli.** §2.1 var olan `[araç]` izinin
   cevabın yanında hiçbir işe yaramadığını tek mesaj çözünürlüğünde gösteriyor, A3 aynı
   şeyi kümede üçüncü kez ölçüyor. Simetriyi tamamlamak, etkisi sıfır ölçülmüş bir
   mekanizmayı ikiye katlamak olabilir.
4. **Kabul kapısı A2'nin tablosu** (D4). Bugünkü taban: **1/15, ilk atlama 9. tur.**
   Tek turluk kümeler aynı gün %88–100 veriyor; bir düzeltmenin işe yaradığını onlar
   söyleyemez.
5. **`docs/bellek-kirlenmesi.md`'nin adı ve başlığı yanlış.** Yeniden adlandırılmadı:
   yanlış teşhisin kaydı, onu düzelten ölçümün yanında durduğu sürece işe yarıyor.

---

## 7. Araçlar

**Tekrar oynatma** — `uv run --env-file .env python -m evals.replay --mesaj 118`

- `--sade` yalnızca `tam`; `--gecmis N` (tekrarlanabilir) geçmiş taraması; `--ceza X`
  `presence_penalty`; `--onek-yaz` modele giden dizinin tamamı; `--out` dosya.
- Kural 1 korunuyor: veritabanı sahiplenilip (`flock`) kopyalanıyor, geri sarma ve bütün
  yazmalar kopyada. `mayen` koşuyorken çalıştırılırsa gürültüyle durur.
- Önek üretimin kodundan geliyor; geri sarma `mayen/data/rewind.py`.

**Oturum ölçümü** — `uv run --env-file .env python -m evals.session --model <ad>
--out docs/<ad>.md`

- Varsayılan iki kol koşar (özetleme açık/kapalı); `--ozetlemesiz` yalnızca kapalıyı,
  `--tekrar N` belirlenimciliği sınar.
- Geçici veritabanı, üretimin pencere kurucusu, üretimin `Digest`'i. Tur başına en fazla
  bir çağrı; tool gövdeleri koşmuyor.
- Senaryo `evals/sessions.py`; turlar gerçek konuşmadan, tool sonuçları elle yazılı ve
  bunun neden aracın en zayıf yeri olduğu orada.

**Eksik taban** — `uv run --env-file .env python -m evals --model <ad> --kume gecmis
--kume bellek --kume kontrol --onek uretim --out docs/<ad>.md`

---

## 8. Yan bulgu: `issues.md` #2 kontrollü ortamda görüldü

A2'nin ilk koşusu `Digest`'in özetleme üretiminde **`akış kesildi: Server disconnected
without sending a response`** ile öldü. `llama-server` **ölmedi** — aynı süreç iki saattir
ayaktaydı ve hemen sonrasında sağlıklı cevap verdi; tek bir bağlantıyı düşürdü.

Koşucu buna göre değişti (`runner.run_all`'ın kuralı): servis çağrısı bir kez daha
deneniyor, ikisi de düşerse **tur** ölçülemedi diye kaydediliyor ve oturum sürüyor. Düşen
tur hiçbir paydaya girmiyor ve rapor `düşen` sütununda sayıyı yazıyor — sıfır değilse
koşunun tekrarlanması gerektiği de orada yazılı.

Bu, #2'nin **teşhisi değil**; sebebi hâlâ bilinmiyor. Ölçülen tek şey: sunucu ayaktayken
tek bir isteğin düşebildiği. Ayrı bir inceleme.
