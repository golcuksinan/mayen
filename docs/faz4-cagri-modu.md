# Faz 4 — zorunlu tool modu ölçümü (P25.3'ün okuması)

Bu dosya **okuma**dır; ham çıktılar `docs/faz4/` altında ve üreticinin kendisi yazıyor.
Buradaki her sayı oradan geliyor.

| Model | Dosya | Durum |
|---|---|---|
| Qwen3.6-27B-IQ4_XS | `faz4/qwen3.6-27b-iq4xs.md` | Geçerli — `presence_penalty=1.5` |
| Qwen3.6-27B-IQ4_XS | `faz4/qwen3.6-27b-iq4xs-pp0.md` | Geçerli — `presence_penalty=0`, bayrak karşılaştırması için |
| Qwen3.6-35B-A3B-IQ4_XS | `faz4/qwen3.6-35b-a3b-iq4xs.md` | Geçerli — 2 senaryo ölçülemedi, raporda yazılı |
| LFM2.5-2.6B-Q8_0 | `faz4/lfm2.5-2.6b-q8.md` | **Ölçülemedi** — şablon `<think>` enjekte ediyor, aşağıda |
| LFM2.5-2.6B-Q8_0 (düşünmesiz) | `faz4/lfm2.5-2.6b-q8-dusunmesiz.md` | Geçerli — özel sohbet şablonuyla |

Her koşu: 2 çağrı biçimi × 2 mod × (altın 50, kontrol 18, adım2 8, sağlamlık 10, uzun
sonuç 4, geçmiş 10×2) = 28 koşu, ~110 senaryo. `-c 16384`, adaptör `temperature: 0.0`
gönderiyor.

---

## Sonuç: zorunlu mod **modele göre** kazandırıyor ya da kaybettiriyor

İki modelin yönü zıt, ve zıtlık her iki çağrı biçiminde de aynı yönde:

| Altın küme (n=50) | serbest | zorunlu |
|---|---|---|
| 27B × CLI | %90 [79–96] | **%98 [90–100]** |
| 27B × JSON | %88 [76–94] | **%94 [84–98]** |
| 35B × CLI | **%94 [84–98]** | %88 [76–94] |
| 35B × JSON | **%94 [84–98]** | %84 [71–92] |

Negatif kontrol kümesinde (n=18) fark daha keskin:

| Kontrol kümesi | serbest | zorunlu |
|---|---|---|
| 27B × CLI | %94 | %94 |
| 27B × JSON | %94 | **%100** |
| 35B × CLI | %94 | **%72** |
| 35B × JSON | %94 | **%50** |

35B'nin JSON zorunlu koşusunda 18 sohbet cümlesinin **9'u** tool çağırıyor: "Hı hı,
anladım" → `date_time`, "Rehber dediğin şey nedir" → `contact_get`, "Ali'yle dün konuştum"
→ `contact_get --name Ali`. P24'ün 35B'de bulduğu fazla-çağrı eğilimi zorunlu modda ikiye
katlanıyor.

Üçüncü model bu tabloya **üçüncü bir yön** ekliyor: düşünmesiz LFM2.5'te zorunlu modun
etkisi **sıfır** (%60 → %60), çünkü model zaten her şeye tool çağırıyor ve `no_tool`'u hiç
kullanmıyor. Yani mod, kazandıran/kaybettiren/etkisiz üç ayrı davranış gösteriyor.

**Bu, §19.1'in CLI/JSON kararının aynı hikâyesi.** P7 tek modelde ölçtü ve bir sıralama
çıkardı; P9 dört model daha ölçtü ve sıralamanın **modele göre döndüğünü** gösterdi; P21
model sabitlenince kararı verdi. Zorunlu mod da aynı yerde: tek modelle karar vermek,
ölçülen iki modelden birini seçmek olurdu.

### Mekanizma tek eksende ve iki modelde ters çalışıyor

Kazanç ve kayıp **eksik argüman** ekseninde toplanıyor (n=7) — geri kalan beş eksen iki
modelde de neredeyse hiç değişmiyor:

| Eksik argüman ekseni | serbest | zorunlu |
|---|---|---|
| 27B × CLI | %29 | **%86** |
| 27B × JSON | %29 | **%71** |
| 35B × CLI | %57 | **%14** |
| 35B × JSON | %57 | **%0** |

Aynı mod, aynı senaryolar, zıt sonuç. Okunabilir hâli:

- **27B**, eksik bilgiyle karşılaşınca serbest modda değeri **uyduruyor** ("Hava durumuna
  bakar mısın?" → `weather --city Ankara`). Zorunlu mod ona adı konmuş bir çıkış veriyor,
  `no_tool` yazıp soruyor.
- **35B**, serbest modda soruyordu; zorunlu modda "her adımda bir çağrı yaz" baskısı onu
  değer uydurmaya itiyor.

Yani `no_tool` bir modelde kaçış yolu, diğerinde kullanılmayan bir seçenek. Gramer tarafı
ikisinde de sağlam: `no_tool` sütunu ile "çağrı üretilmeyen tur" sütunu **her satırda
eşit**, yani model işareti doğru kullanıyor — hata seçimde.

### Zorunlu modun bilinen bedeli hâlâ ölçülmedi

P25.1 baştan yazmıştı: zorunlu modda her sohbet turu önce `no_tool` üretip **ikinci bir
üretim turu** açmak zorunda. Koşucu işareti görünce duruyor, o ikinci turu koşmuyor.
Dolayısıyla:

- **TTFT farkı yok** (27B 0.20→0.19 sn, 35B 0.28→0.27) ama bu ölçüm o bedeli içermiyor.
- **Toplam sürenin zorunlu modda düşmesi bir hızlanma değil** (27B 0.66→0.39): eksik turdan
  geliyor.

Kural 14: ölçülmeden "ucuz" denemez. Bunu kapatmak koşucuya `no_tool` sonrası bir yanıt
turu eklemeyi gerektirir.

---

## `presence_penalty` neredeyse hiçbir şeyi değiştirmedi

27B iki bayrak setiyle koşuldu — aynı model, aynı senaryolar, tek fark bayrak:

| 27B altın küme | `pp=0` | `pp=1.5` |
|---|---|---|
| CLI serbest | %94 | %90 |
| CLI zorunlu | %98 | %98 |
| JSON serbest | %86 | %88 |
| JSON zorunlu | %94 | %94 |

Farkların hepsi bir-iki senaryo, aralıkların çok içinde. **Zorunlu modun kazancı bayrak
değişikliğinden sağ çıktı** — model bağımlılığı bulgusunu güçlendiren şey bu.

`top_p`, `top_k` ve `min_p` farkları eşitlenmedi ve **eşitlenmeleri gerekmiyor**: adaptör
`temperature: 0.0` gönderdiği için üretim argmax, ve bu üç örnekleyici yalnızca aday
kümesini buduyor — en yüksek olasılıklı token hiçbirinde atılmıyor. Logit'leri değiştiren,
yani argmax'ı kaydırabilen tek fark ceza terimleriydi.

---

## LFM2.5-2.6B: önce ölçülemedi, sonra şablon değiştirilip ölçüldü

Modelin sohbet şablonu üretimin başına **koşulsuz** bir düşünce açıcısı koyuyor:

```
<|im_start|>assistant\n<think>
```

`<think>` üretilen bir token değil, prompt'un parçası; şablonda onu kapatan bir anahtar
yok. Bu, §6'nın "dal ilk token'da belli olmalı" kuralıyla doğrudan çelişiyor ve iki modda
iki yoldan aynı yere çıkıyor: serbest modda model ortalama 173 token düşünüp hiç çağrıya
geçmiyor; zorunlu modda gramer `<tool> …` üretiyor ama metin `<think><tool> date_time`
oluyor ve `is_call()` öneki 0. konumda aradığı için düz metin sayıyor.

**Tek bir çağrı bile ayrıştırılmadı** — raporun her satırındaki `argüman doğruluğu —` bunun
kanıtı. Oradaki %30'lar modelin becerisi değil, çağrı beklenmeyen senaryoların oranı
(15/50). Model kendi içinde doğru akıl yürütüyor ("I need to use the `date_time` tool").

Bu bir gramer hatası değil, **bir uyumluluk sınırı**: §6'nın ilk-token kuralı, düşünce
bloğunu zorunlu kılan modelleri dışlıyor. Üç seçenek vardı ve karıştırılmamalı:

1. **Modele özgü gramer — hayır.** Katalog, iki biçim ve iki mod tek defterden üretiliyor;
   model başına gramer §9.1'in "ikinci, bağımsız metin" hatasının gramer hâli olur ve altın
   küme modelleri karşılaştırmayı bırakır.
2. **Üçüncü bir eksen ("düşünme öneki") — açılmadı.** CLI/JSON ile aynı düzeyde ölçülebilir
   bir seçenek olurdu, **ama bedeli §6'nın kendisi:** ilk ses, düşüncenin tamamı bitene
   kadar bekler. §19.4'ün gecikme hedefi hâlâ açık, yani "kabul edilebilir" diyecek bir sayı
   yok — bir açık maddeyi varsayımla kapatmak olurdu.
3. **Özel sohbet şablonu — yapıldı.** `config/chat-templates/lfm2.5-dusunmesiz.jinja`, tek
   satırlık fark: üretim öneki `<|im_start|>assistant\n<think>` yerine
   `<|im_start|>assistant\n`. **Gramer değişmiyor** — düzeltilen şey modelin servis ayarı,
   bizim sözleşmemiz değil; (1)'e yapılan itiraz buraya geçmiyor.

### Düşünmesiz LFM2.5 ölçüldü — ve okuması sınırlı

Bu sayılar "LFM2.5 ne yapabilir" değil, "**düşünmesi engellenmiş** LFM2.5 ne yapabilir"
demektir. Model her zaman düşünecek şekilde eğitilmiş; açıcıyı kaldırmak onu eğitildiğinden
farklı bir kipte çalıştırıyor. Mimarimiz §6 gereği düşünmeye yer bırakmadığı için ölçmek
istediğimiz de tam olarak buydu, ama cümle böyle kurulmalı.

| Altın küme (n=50) | serbest | zorunlu |
|---|---|---|
| CLI | %60 [46–72] | %60 [46–72] |
| JSON | %58 [44–71] | %60 [46–72] |

**Zorunlu modun hiçbir etkisi yok, ve sebebi net: model zaten her şeye tool çağırıyor.**
Negatif kontrol kümesinde CLI %17 ve %11, **JSON iki modda da %0** — 18 sohbet cümlesinin
tamamı bir tool çağırıyor. "Tool gerekmez" ekseni %0–%25, eksik argüman ekseni %0–%14: eksik
bilgiyi sormuyor, uyduruyor. `no_tool` bir kaçış yolu sunuyor ama model onu kullanmıyor.

Çağrı *gerektiğinde* fena değil: tek tool %100, ayırt etme %88, serbest metin %86, uzun
sonuç %100. Yani sorun yetenek değil, **ne zaman durulacağını bilmemek** — küçük modelin
karakteristik hatası ve 35B'de gördüğümüz eğilimin uç hâli.

**JSON bu modelde CLI'dan açıkça iyi** ve fark ölçümün gürültüsünden büyük: argüman
doğruluğu %76/%70'e karşı %41/%39, CLI'da 5–9 uydurulan argüman ve 4–7 düzeltme turu varken
JSON'da **sıfır**. P9'un bulgusunun tekrarı: JSON küçük modellerde önde (9B kuantlarında
%84'e karşı %60). §19.1'in CLI kararı 35B için verildi ve orada geçerli.

**TTFT'de 4–6 kat fark var:** 0.04–0.05 sn, 27B'nin 0.20'sine ve 35B'nin 0.28'ine karşı.
§19.4 açık olduğu için bu bir "geçti/kaldı" değil, ama gecikme hedefi sayı kazandığında
karşılaştırılacak ilk şey bu olacak.

LFM2.5 zaten aday değildi; §19.2'nin LLM yarısı 35B olarak kapalı.

---

## Yeni kümelerin kendi bulguları

Bunlar mod tartışmasından bağımsız, **modelin** davranışı — ve dördü de altın kümenin
göremediği yerlerde:

| Bulgu | Nerede | Ne |
|---|---|---|
| Türkçe özel adlar İngilizceleşiyor | `tek-07`, `tek-04`, `sag-09` | `masaüstü` → `desktop`/`masaustu`, `İstanbul` → `Istanbul`. §19.9'un WOL hedef eşleşmesi ve `contact_save`'in ad eşleşmesi **birebir**; tam olarak bunun kaçıracağı hata |
| `--` sessizce siliniyor | `sag-01`, her koşuda | "`-- bugün --` çok yoğun geçti" → "bugün çok yoğun geçti". A4'ün yasağı gramerde; model işaretleri gramerin izin verdiği yerde bile atıyor |
| Türkçe gün numarası kayıyor | `tek-12` | "Salı" → `--day 3` (doğrusu 2) |
| `gec-04` her modelde düşüyor | dört koşuda da | "Kurdun mu gerçekten?" → `task_list` değil **yeni bir** `task_create` |

**Desteksiz sayı sayacının sınırı da görünür oldu:** `tek-05`'te model `%29.4` ve `22.6 GB`
yazıyor; ikisi de sonuçtaki sayılardan **türetilmiş** aritmetik (9.4/32 ve 32−9.4). Sayaç
türetmeyi desteksiz sayıyor. Dar adı bunu zaten söylüyordu ama okuyana anlatmıyordu — bu
paragraf onun için.

**izli/izsiz farkı üç modelde de tam sıfır.** P24'ün düzeltmesinin etkisi hâlâ ölçülmemiş
durumda; kümedeki en uzun geçmiş 5 tur, oysa üretimdeki hata ~24 mesajda görülmüştü.

---

## Karar

**Verilmedi, ve verilmemesi bu ölçümün sonucudur.** Zorunlu mod evrensel olarak iyi ya da
kötü değil; §19.1'in CLI/JSON kararı gibi modele bağlı — üç modelde üç ayrı yön
(kazandırıyor / kaybettiriyor / etkisiz). Kalan iş sahibin:

- Model sabit (35B, §19.2) kalacaksa **serbest mod kazanıyor** ve zorunlu mod silinir —
  35B'de zorunlu mod hem altın kümede hem negatif kontrolde kaybettiriyor.
- Model değişirse ölçüm tekrarlanır: komut tek satır, bayraklar rapora kendiliğinden
  giriyor.

Silinmeden önce kapatılması gereken tek boşluk, yukarıdaki **ölçülmemiş TTFT bedeli**:
zorunlu modun ikinci üretim turu ölçülmeden "pahalı değildi" denemez.

---

## İlk ses bedeli ölçüldü — `docs/faz4-ilk-ses.md` (2026-08-13)

**Boşluk kapandı: zorunlu mod ilk sesi ikiye katlıyor.** Ölçüm 27B'de, negatif kontrol
kümesinde (18 senaryo, tamamı sohbet — yani bedelin doğduğu turların tamamı):

| biçim | serbest | zorunlu |
|---|---:|---:|
| CLI | 0.21 sn (n=17) | **0.41 sn** (n=17) |
| JSON | 0.16 sn (n=17) | **0.40 sn** (n=18) |

**Neden bu sayı raporun `ort. TTFT` sütununda görünmüyordu:** o sütun *birinci* üretimin
ilk token'ını ölçüyor ve zorunlu modda o token `<tool> no_tool`'un ilk harfi. Kullanıcı
onu duymuyor; duyduğu metin, birinci üretim bittikten sonra başlayan **ikinci** üretimden
geliyor. İki mod bu yüzden `ort. TTFT`'de aynı görünüyordu (0.20'ye 0.20) — ölçülen şey
kullanıcının beklediği süre değildi. `ScenarioResult.speech_ttft` turun başından
kullanıcının duyduğu ilk token'a kadar olan süreyi ölçüyor: serbest modda birinci üretimin
TTFT'si (kapanış üretimi yok, `agent/loop.py` düz metin dalında dönüyor), zorunlu modda
birinci üretimin **tamamı** artı kapanışın TTFT'si. Kapanış gerçekten koşuluyor, tahmin
edilmiyor.

**Sayı, CLAUDE.md'de baştan yazılmış olan bedelin ta kendisi:** "zorunlu modda her chit-chat
turu ikinci bir üretim harcar". Harcadığı 0.20 sn ve §6'nın ilk ses bütçesinin tamamı
zaten o mertebede. §19.4 açık olduğu için bu bir "kaldı" değil — ama artık ölçülmüş bir
bedel, ve iki modun tek gerçek ayrımı burada: doğruluk tarafında 27B'nin negatif kontrolü
%94'e %94 (CLI) ve %94'e %100 (JSON), yani aralıkları tamamen çakışıyor.

**Ortalama süre (`ort. sn`) ters yönde okunmasın:** zorunlu modda 1.5 sn'den 0.32 sn'ye
düşüyor, ama bu ölçüm birinci üretimi kapsıyor ve zorunlu modda birinci üretim 5 token
(`<tool> no_tool`), serbestte 60 token (cevabın kendisi). Kısalan şey ölçülen dilim,
turun kendisi değil.

**Payda notu:** serbest CLI/JSON'da 17, zorunlu JSON'da 18. Fark, o tek senaryoda modelin
çağrı üretmiş olması; çağrı üretilen tur bu paydanın dışında, çünkü orada ilk ses zaten
tool'un çalışmasını bekliyor.

### 35B'de de ölçüldü — `docs/faz4-ilk-ses-35b.md`

Aynı gün, sunucuda 35B yüklüyken; `n_ctx` 16384 ve `presence_penalty` 1.5, yani 27B
koşusuyla birebir karşılaştırılabilir.

| biçim | serbest | zorunlu | payda |
|---|---:|---:|---|
| CLI | 0.28 sn (n=17) | **0.35 sn** (n=13) | 17 → 13 |
| JSON | 0.22 sn (n=17) | **0.36 sn** (n=10) | 17 → 10 |

**Mutlak bedel 27B'dekinden küçük** (+0.07/+0.14'e karşı +0.20/+0.24) ve sebebi beklenen:
35B-A3B'nin aktif parametresi az, `no_tool` üretimi çok kısa sürüyor.

**Asıl bulgu paydada.** Serbest modda 18 sohbet turunun 17'si çağrısız kapanıyor; zorunlu
modda bu 13'e (CLI) ve 10'a (JSON) düşüyor — aradaki turlarda model sohbete tool çağırıyor.
Yani yukarıdaki 0.35 ve 0.36, zorunlu modun **doğru davrandığı alt kümede** ölçülmüş
sayılardır. Hatalı turlarda gerçek ilk ses daha kötü: kullanıcı önce tool'un çalışmasını,
sonra ikinci üretimi bekliyor. **Bu tablo zorunlu modun bedelini olduğundan küçük
gösteriyor, büyük değil** (Kural 14).

Aynı koşunun doğruluk tarafı P25.2'nin bulgusunu tekrarlıyor: kontrol kümesinde CLI
%94 → %72, JSON %94 → %56, ve aralıklar çakışmıyor ([74–99]'a karşı [49–88]).

**Tablo tamamlandı:**

| | 27B | 35B |
|---|---|---|
| zorunlu mod doğrulukta | kazandırıyor | kaybettiriyor |
| zorunlu mod ilk seste | +0.20 / +0.24 sn | +0.07 / +0.14 sn (iyimser alt küme) |

35B'de zorunlu modun iki ekseninde de artısı yok; §19.2'nin LLM yarısı 35B kaldığı sürece
silme kararının önünde ölçülmemiş bir şey kalmadı. 27B'de karar hâlâ bir takas: kazancı
doğrulukta çakışan aralıklar kadar, bedeli ilk seste iki kat.
