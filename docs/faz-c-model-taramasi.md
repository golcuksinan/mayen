# Faz C — Model taraması: LFM2.5, 35B-A3B ve Kokoro'nun GPU'ya taşınması

**Tarih:** 2026-08-17. **Karar üretmedi** — iki aday ölçüldü, ikisi de sahibin kararına
bırakıldı; üretim `Qwen3.8-27B-IQ4_XS` + yerel biçim + Kokoro(CPU) olarak duruyor.

## Neden koşuldu

Sahibin planı: `llama-server` kartın 16.3 GB'ının 15.6'sını tuttuğu için Kokoro CPU'da
koşuyordu (`docs/faz7-kokoro.md`). Daha küçük ya da offload edilebilir bir LLM, Kokoro'ya
GPU'da yer açardı. Sırayla iki aday denendi: `LFM2.5-2.6B-Q8_0` (2.7 GB) ve
`Qwen3.6-35B-A3B-IQ4_XS` (17.5 GB, offload'la).

**Ölçülen soru şudur ve dar tutulmuştur:** yer açmanın tool akışına bedeli ne. Cevap
alınmadı sayılmaz — alındı, ama bedelin nerede toplandığı iki farklı aletle iki farklı
göründü ve raporun ağırlığı orada.

## Kokoro GPU'da: engel kalktı, sayılar burada

`services/kokoro/main.py:63`'ün docstring'i "kart boşaltılırsa `cuda` yazılıp ilk-ses
süresi yeniden ölçülür" diyordu. Ölçüldü.

**VRAM.** Ağırlık diskte 313 MB (82M parametre, fp32); GPU'daki ayak izi ondan büyük,
çünkü torch'un CUDA bağlamı ve aktivasyonlar üstüne biniyor:

| durum | VRAM |
|---|---:|
| model yüklü, sentez yok | 610 MiB |
| sentez altında tepe | **1088–1092 MiB** |

Yani bütçe olarak **~1.1 GB** sayılmalı, 610 değil. Eski hata mesajının ("20 MB
ayıramadı") sebebi Kokoro'nun büyüklüğü değil, kartta hiç yer olmamasıydı.

**İlk ses, LLM yüklüyken** (35B offload'la kartta, `bf_emma`, hız 0.85, efektli):

| metin | GPU ilk parça | CPU'da kayıtlı (`faz7-kokoro.md`) |
|---|---:|---:|
| 14 harf | 0.97 s ← **ilk çağrı, ısınma** | 0.26 s |
| 25 harf | 0.09 s | 0.33 s |
| 43 harf | 0.06 s | ~0.44 s |
| 87 harf | 0.05 s | ~0.7 s |

Cümle bölücünün alt sınırı `MIN_CHARS = 24` olduğu için gerçek turda ikinci satır geçerli:
**ilk ses 0.33 s → 0.09 s.** GPU'da bir kerelik ~1 s ısınma bedeli var, CPU'da yok.

**Birlikte durabiliyorlar:** llama-server 12380 MiB + Kokoro 610 MiB, sentez sırasında hâlâ
2386 MiB boş.

**Ama bu bir taşıma kararı değil.** Kazanç 0.24 saniye ve §19.4 açık — tutturulacak bir
hedef yok. Sahip bu maddeye bilerek sayı koymuyor (aşağıya bakınız), dolayısıyla 0.24 s
uğruna LLM'den VRAM almanın gerekçesi de yok. `MAYEN_KOKORO_DEVICE=cuda` anahtarı hazır;
kart bir gün boşalırsa kod değişikliği sıfır.

## Aday 1: LFM2.5-2.6B-Q8_0 — elendi

VRAM 3332 MiB, `n_ctx` 16384, 4 slot. Sunucu kendi örneklemesiyle açıktı, o yüzden
`--ornekleme sunucu` ile koşuldu (`temperature` 0.01, `top_k` 50, `top_p` 0.95, `min_p`
0.05, `repeat_penalty` 1.1). Üretim öneği, dil kuralı kolu yok.

| küme | cli | json | yerel |
|---|---:|---:|---:|
| altın (n=50) | 30% | 30% | 76% [63–86] |
| kontrol (n=18) | 100% | 100% | 72% [49–88] |
| halüsinasyon (n=15) | 7% | 7% | 87% [62–96] |
| bellek (n=17) | 47% | 47% | 65% [41–83] |

**Metin biçimlerindeki `100%` yanıltıcıdır ve eksen kırılımı sebebi söylüyor:** tek tool
0%, çok tool 0%, ayırt etme 0%, serbest metin 0%; yalnızca "tool gerekmez" ve "eksik
argüman" 100%. Model GBNF'in kalıbında **hiç çağrı üretmiyor** ve sadece doğru cevabın
"çağırmamak" olduğu eksenlerde puan alıyor. Yerel tool çağrısı için eğitilmiş; yerelde
`finish_reason: tool_calls` düzgün geliyor.

Yerelde `uydurulan argüman` sayacı **2** (altın). Yerel biçimde bu sayaç gerçektir —
gramer yok, yani modelin hatası (§17.1'in kapsam notu yerel satırlar için geçerli değil).

TTFT 0.43 s, senaryo başına 0.76 s (halüsinasyon kümesinde 0.33 / 0.50).

**Elenme gerekçesi:** dört kümenin dördünde de 27B'nin altında. Tek tek aralıklar çakışıyor,
yani hiçbiri temiz bir sıralama değil, ama yön dördünde de aynı.

### Akıl yürütmesi kapatılamıyor, ve bu bir bayrak eksikliği değil

Model `reasoning_content` üretiyor (~50–67 token, atılıyor; adaptör `delta.content` ve
`delta.tool_calls` okuduğu için cevaba karışmıyor). Denenen ve **işe yaramayan** yollar:
`reasoning_format: none` (o "akıl yürütmeyi biçimlendirme" demek, "üretme" demek değil),
istek gövdesinde `chat_template_kwargs: {enable_thinking: false}`, `{thinking: false}`,
`reasoning_budget: 0`. Sebebi şablonun kendisinde:

```jinja
{%- if add_generation_prompt -%}
    {{- "<|im_start|>assistant\n<think>" -}}
{%- endif -%}
```

Üretim istemi `<think>`'i **koşulsuz** açıyor; şablonda `enable_thinking` diye bir
değişken yok. Tek anahtar `preserve_thinking` ve o "şu an düşünsün mü" değil, "geçmiş
asistan mesajlarındaki düşünme saklansın mı" demek — varsayılanı `false`, yani geçmişe
birikmiyor. Kapatmanın tek yolu şablonu ezip `</think>` prefill etmek olurdu.

## Aday 2: Qwen3.6-35B-A3B-IQ4_XS — iki alet ters yönde konuşuyor

Offload'la 12380 MiB, `n_ctx` 16384, kartta 3.6 GB boş. **Greedy koşuldu**, sunucunun
kendi ayarlarıyla değil: sunucu `temperature 0.7` ve `presence_penalty 1.5` ile açıktı;
sunucu örneklemesi kullanılsa biçim *ve* örnekleme birlikte değişir, karşılaştırma
okunamazdı. (`presence_penalty 1.5` ayrıca `Sampling`'in docstring'inde adıyla kayıtlı
"kimsenin seçmediği sayı"dır — **üretim bu sunucuya bağlanırsa `main.py:454` onu
`/props`'tan okuyup kullanır.**)

### Dört küme, iki dil-kuralı kolu

| küme | biçim | dil kuralı yok | dil kuralı açık |
|---|---|---:|---:|
| altın | cli | 92% [81–97] | 84% [71–92] |
| | json | 96% [87–99] | 88% [76–94] |
| | **yerel** | 94% [84–98] | **94% [84–98]** |
| kontrol | cli | 83% [61–94] | 89% [67–97] |
| | json | 78% [55–91] | 72% [49–88] |
| | **yerel** | 94% [74–99] | **89% [67–97]** |
| halüsinasyon | cli | 87% [62–96] | 93% [70–99] |
| | json | 87% [62–96] | 87% [62–96] |
| | **yerel** | 40% [20–64] | **33% [15–58]** |
| bellek | cli | 71% [47–87] | 71% [47–87] |
| | json | 71% [47–87] | 71% [47–87] |
| | **yerel** | 82% [59–94] | **76% [53–90]** |

`yerel × halusinasyon` iki bağımsız koşuda **birebir aynı** çıktı: 40%, ve başarısız olan
tam aynı dokuz senaryo (`hal-01 03 04 05 06 07 08 10 11`). Greedy tasarlandığı gibi
çalışıyor; bu sayı gürültü ya da veri kirlenmesi değil. (Sahip aynı gün `mayen.db`'yi
sildi; `evals` üretim veritabanını hiç açmaz — tek `Database` kullanımı
`evals/session.py`'nin `tempfile` içindeki `session.db`'sidir.)

**Hata sınıfı, `issues.md`'nin kendisi:**

```
hal-07: contact_get çağrılmadı → "Veli'nin numarası 0532 111 22 33."
hal-10: note_search  çağrılmadı → "Alışveriş listesine süt ve ekmek yazdım."
hal-11: task_list    çağrılmadı → "Evet, yarın sabah dokuzda ... aktif."
```

### Bulgu: dil kuralı **modele bağımlı** bir kaldıraç

Aynı dosya (`config/dil-en.txt`), aynı konum, aynı gün, yerel biçim:

| küme | 27B: yok → açık | 35B: yok → açık |
|---|---:|---:|
| altın | 88 → **92** | 94 → 94 |
| kontrol | 78 → **94** | 94 → **89** |
| halüsinasyon | 87 → **100** | 40 → **33** |
| bellek | 82 → 82 | 82 → **76** |

27B'de üç kümede iyileştiriyor, 35B'de hiçbirinde iyileştirmiyor, üçünde kötüleştiriyor.
**Bu, rol metni için kayıtlı dersin dil kuralında da geçerli olduğunun ilk ölçümü:** bir
prompt kaldıracı yeterince güçlü modelde tutuyor, model zayıflayınca çalışmıyor. Kaldıracın
kendisi sağlam değildir; modelin gücüne bağlıdır.

**Yan doğrulama, P29 lehine:** kural eklenince TTFT kılını kıpırdatmadı (altın 0.36 → 0.37,
halüsinasyon 1.73 → 1.75) ve token sayıları düşük kaldı. Faz 7'nin felaketi — kural
değişken kuyruğun arkasına konduğunda senaryo başına prompt 22 → 1631, TTFT 0.24 → 1.04 —
**tekrarlamadı.** Kuralı bağlam bloğunun sonuna koyma kararı bu modelde de doğru yerde.

### Kabul kapısı: aynı model, ters sonuç

`halusinasyon` kümesi 33% derken **kabul kapısı 80% diyor.** İkisi de doğru; farklı
dünyaları ölçüyorlar, ve bunu `evals/runner.py:226`'nın docstring'i zaten yazmış:

> "Bu artık üretimin biçimi değil ve bilerek öyle (2026-08-16). Üretim tool adımını çağrı
> (`assistant`) + sonuç (`tool`) olarak yazıyor; buradaki kümelerin senaryolarında ise
> geçmiş turun **sonucu yok** … Sonucu uydurmak, ölçümün kendi varsayımını doğrulaması
> olurdu. **Tek turluk kümeler 2026-08-16 öncesinin geçmişini ölçmeye devam ediyor.**"

`halusinasyon` kümesindeki her fikstür `tool=None`, yani hiç çağrı olmamış bir tur.
Bilerek: küme `issues.md` #3'ü, yani **zehirlenmiş bir geçmişten kurtulmayı** ölçüyor,
birincil halüsinasyonu değil.

**Kabul kapısı, üretim kolu** (yerel biçim, `DIGEST_ON=False`, üretimin dizisi birebir):

| | Qwen3.8-27B (kayıtlı) | Qwen3.6-35B-A3B |
|---|---:|---:|
| kapı | 12–13/15 (80–87%) | **12/15 (80%)** [55–93] |
| ilk atlanan tur | 23 | **22** |
| gereksiz çağrı | 4 (dördü `date_time`) | 5 (dördü `date_time`, biri `weather`) |

Kaçırdığı üç tur **22 "kıs", 23 "tamam kıs artık", 28 "hayır kullanmadın şimdi kullan"**;
27B'nin kalan iki kaçığı 23 ve 28 ve sınıfı kayıtta *"kullanıcı ısrar ediyor"*. Yani aynı
sınıf, bir fazla.

### Okuma

| dünya | 27B | 35B |
|---|---:|---:|
| geçmişte tool sonucu **var** (üretim) | 80–87% | **80%** |
| geçmişte tool sonucu **yok** (`halusinasyon`) | 100% | **33%** |

**Sağlıklı durumda iki model bu örneklem boyutunda ayırt edilemiyor. Bir kez uydurduktan
sonra 27B toparlanıyor, 35B yalanı sürdürüyor.** Bu, bellekteki kayıtla birebir örtüşür:
*"düzeltme eski geçmişi onarmıyor — bozuk geçmiş taşıyan veritabanı düzeltmeden sonra da
bozuk kalıyor ve arıza kendini besleyerek sürüyor."* 27B'de tek kötü turun bedeli bir tur;
35B'de muhtemelen elle DB müdahalesi.

**Elenme gerekçesi (öneri, karar değil):** "35B uyduruyor" değil — sağlıklı durumda
uydurmuyor. Gerekçe şudur: `bellek` 76 vs 82, `kontrol` 89 vs 94, `argüman` 91 vs 94 (hepsi
çakışan aralıklar, hepsi 27B'ye eğilimli), **ve hatadan sonra toparlanmama.** Karşılığında
alınan şey 0.24 saniye.

## Bu turda düzeltilenler

**`src/mayen/main.py` — kalıcı yapılandırma hatası artık geçici hatanın arkasında değil.**
`build()` LLM'e bağlanmayı (`_real_llm`) rol/dil dosyasını okumaktan (`_system`) önce
yapıyordu. Eksik rol dosyası kalıcıdır (`EXIT_CONFIG`), sunucuya ulaşamamak geçicidir; ters
sırada kalıcı hata geçici görünüyor ve birim dosyası onu sonsuz yeniden başlatmaya sokuyor.
`_system(...)` ağ çağrısının üstüne alındı. `tests/test_main.py::test_broken_configuration_
exits_with_the_permanent_code` bunun için düşüyordu ve ayakta kalması `llama-server`'ın
kapalı olmasına bağlıydı.

**`evals/__main__.py` — `--ornekleme {greedy,sunucu}`.** `greedy` varsayılan kalıyor:
`docs/faz2-olcum.md`'den beri her sayı o kabulle okundu. `sunucu`, ayarları `/props`'tan
okuyup **gönderir** — değer sunucudan gelir, gönderim açık kalır, yani bir sunucu bayrağının
sessizce karar vermesine kapatılan kapı yerinde durur. Kendi sıcaklığı/cezası için ayarlanmış
bir modelde (LFM2.5) gereken budur.

**`evals/__main__.py` — `--bicim`, varsayılanı `main.py:CALL_FORMAT`.** Önceden koşucu üç
biçimi de çeviriyordu; §19.1 kapandıktan sonra bu, her koşuyu iki ölü yol uğruna üç katına
çıkarmak demekti. **İki metin biçimi silinmedi** (sahibin kararı: "dursun bir kenarda ama
aktif olmasın") — üretilmeye, ayrıştırılmaya ve test edilmeye devam ediyorlar, sadece
istenmedikçe ölçülmüyorlar. `--bicim cli --bicim json` ile geri gelirler.

**`evals/session.py` — `--yerel` → `--metin-kolu`, varsayılan tersine döndü, etiket
düzeltildi.** Bu bir kusurun düzeltmesi: `CALL_FORMAT` yerelken `native=False` kolu
`parse()`'a yerel biçim veriyor, o da `calls.py:145`'te "kodun hatası" diyor. Kol çağrı
üretemiyor ve **skoru bir ölçüm değil** — ilk okumada 1/15 (7%) diye rapor edildi ve
düzeltme öncesi sayılarla benzerliği rastlantıdır. Üstüne rapor iki kolu da "yerel" diye
etiketliyordu, yani kendi kollarını ayırt edilemez kılıyordu; metin kolu artık
`metin(yerel)` yazıyor.

**Ders:** §19.1 kapandığında ölü yollar sessizce bozuldu ve **bozuk hâlleriyle her koşuda
ölçülmeye devam ettiler.** Üç biçimi canlı tutmanın maliyeti zaman değil, yanlış sayıydı.

## Ölçülmeyenler ve sınırlar

- **Birincil halüsinasyon oranı yok.** `halusinasyon` ikinci mertebeyi (zehirli geçmişten
  kurtulma) ölçüyor, `altın` tool seçimini; temiz geçmişte ilk turda uydurma oranını ölçen
  bir küme yok. `issues.md`'nin şikâyeti orada yaşıyor.
- **Rol metni bu iki modelde yeniden yazılmadı.** `config/rol.txt` (Edden) 27B'de yazıldı
  ve kural "model değişirse yeniden ölç" diyor. Yani yukarıdaki tablolar iki adayın tavanı
  değil, başka bir modele göre biçilmiş bir rol metni altındaki hâlleri. 35B için
  denenmedi, çünkü 27B'yi bu kümede 87→100 taşıyan kaldıraç (dil kuralı) 35B'de hiç
  tutmadı; tutma olasılığı zayıf görünüyor.
- **Her satır tek koşu**, `yerel × halusinasyon` hariç (iki koşu, birebir aynı). Payda
  küçük: kontrol 18, halüsinasyon 15, bellek 17, kapı 15 beklenen çağrı. **Bir `100%`
  "hiç yok" demez, "ölçülen dilimde yok" der** (Kural 14) — 27B'nin halüsinasyon `100%`'ü
  Wilson ile [80–100].
- **`faz6-35b-rol3.md` ile fark:** o rapor cli halüsinasyonu 73% yazıyor, bugün 87%.
  Determinizm bu kadar sıkı olduğu için bu koşu varyansı **olamaz**; iki rapor arasında
  koşulların bir şeyi değişti. Adaylar: `llama.cpp` sürümü (bugün `b10442-9b0a2ce85`),
  offload yapılandırması, ve Faz 8'in katalogu büyütmesi (22 tool). Seçilmedi, ölçülmedi.
- Kokoro tabloları GPU'da tek koşu; ilk satır ısınmayı içerir.

## Sahibin kasıtlı kararsızlıkları (yeni bilgi, kayda geçiyor)

§19'da açık duran iki madde "henüz karar verilmedi" diye okunuyordu; sahibin gerekçesi
bundan farklı ve daha güçlü:

- **§19.4 (ilk ses hedefi) — bilerek sayı konmuyor.** "3 saniye desem ve 3.1 alsak, 100
  milisaniye için uğraşmak istemiyorum." Yani bir eşik, kovalama yükümlülüğü yaratır; MVP
  aşamasında istenen bu değil. **Bu maddeye sayı önermek yanlıştır**; ölçüp raporlamak
  doğrudur.
- **§19.2'nin STT yarısı — bilerek erteleniyor.** Şu an ihtiyaç yok, ve donanım
  değişebilir (GPU/VRAM/model belirsiz). Değişecek bir şeye model kararı bağlamamak için
  bekliyor.

Bu ikisi "ölçüm eksiği" değil, **kapsam kararı**. Faz C boyunca ikisi de sayı önerisiyle
karşılandı ve ikisi de sahip tarafından gerekçeyle reddedildi.
