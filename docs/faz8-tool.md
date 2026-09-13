# Faz 8: katalog genişlemesi — bellek yazma ve makine denetimi

2026-08-16. §9.2'nin ilk sürüm kataloğu on altı tool'du ve hepsi *veriye* dokunuyordu.
Bu iş iki şey ekliyor: belleğin eksik kapısı ve makinenin kendisi (ses, medya, pencere,
uygulama). Sahibin seçimi: A + B1 + B2, `ArgType.ENUM` dâhil, hepsi bir seferde ve
sonunda ölçüm.

## Önce silinen üç tool

Genişletme listesinin ilk hâlinde `note_list`, `contact_list` ve `contact_update` vardı.
Üçü de yazılmadı, çünkü **üçü de zaten vardı**:

- `note_search`'ün `query` alanı isteğe bağlı — verilmezse hepsini listeliyor.
- `contact_get`'in `name` alanı isteğe bağlı — verilmezse rehberin tamamı.
- `contact_save` var olan kişinin telefonunu zaten güncelliyor.

Liste depo metodlarına (`notes.list_all`, `people.update`) bakılarak çıkarılmıştı; tool
gövdeleri okunsaydı üçünün de karşılığı görülürdü. Yazılsalardı zarar somut olurdu:
örtüşen iki tool, ölçülmüş biçimde kırılgan olan tool seçimini bozar — kataloğu büyütmenin
tek maliyeti token değil.

Aynı sebeple ses seviyesi **tek** tool: `contact_get`'in başlığındaki gerekçe ("ayrı bir
listeleme tool'u kataloğu büyütür ve modele ikinci bir seçim ekler") burada da geçerli.
Seviye verilmezse okur, verilirse ayarlar.

## Sayılı seçenek: `ArgType.ENUM`

Tool adları gramerde sabit listedir ve bu yüzden **uydurulamaz** (§17.1'in sayacının
yapısal olarak sıfır olmasının sebebi). Argümanlarda böyle bir güvence yoktu: `--action`
alanına serbest metin düşerdi ve gövde `kapat`/`close`/`close window` üçlüsünü elle
eşlemek zorunda kalırdı.

`ENUM` bunu argümana taşıyor. Seçenekler gramerde harfi harfine alternatif:

```
cli-enum-window-action-action ::= "minimize" | "maximize" | "fullscreen" | ...
json-enum-window-action-action ::= "\"minimize\"" | "\"maximize\"" | ...
```

Üç ayrıntı bilerek böyle:

1. **Kural tool'a *ve* alana özel.** İki tool'un aynı adlı alanı farklı seçenekler taşıyor
   (`window_action --action` ile `media_control --action`); tek bir `enum-action` kuralı
   ikisini birbirine karıştırırdı.
2. **JSON tarafında tırnaklar kuralın içinde.** `json-string`'e devredilseydi kısıt
   tamamen kaybolurdu — geçerli JSON üretilirdi ama değer serbest kalırdı.
3. **Katalogda tipin adı değil seçeneklerin kendisi yazılı.** `usage()` katalog metninin
   kaynağı (§8.4) ve modelin `<enum>` görmesi ona hiçbir şey söylemezdi.

Doğrulama gramerden **bağımsız olarak** gövdede de duruyor: gramer bir güvenlik sınırı
değil (Değişmez 4) ve tek giriş yolu o değil.

## İzin listesi görünür olmak zorunda

`app_launch` ilk hâlinde `STRING` alıyordu ve liste yalnızca gövdede doğrulanıyordu —
`wake_on_lan`'ın kalıbı. Gerçek modelde denendi ve **başarısız oldu**: "tarayıcıyı aç"
sorusuna model *hiç denemeden* "tanımlı bir tarayıcım yok" dedi. Katalogda yazan tek şey
"yapılandırmada tanımlı bir uygulamayı açar"dı; hangi adların tanımlı olduğu görünmüyordu.

Düzeltme: adlar `ENUM` seçeneği olarak yapılandırmadan geliyor, yani `app_launch` bir sabit
değil, defter kurulurken üretiliyor (`builtin_registry(config)`). Sonuç aynı koşuda:

```
--- hangi uygulamaları açabiliyorsun
I can launch four applications: files, text editor, browser, and terminal.

--- kwrite uygulamasını şimdi başlat
I cannot launch KWrite, Administrator. It is not in my configured application list.
```

İkincisi asıl kazanılan şey: liste görünür ama **kapalı**. Kural 8 bozulmadan model
listenin dışına çıkamıyor ve bunu kullanıcıya açıklayabiliyor.

**Hiç uygulama tanımlı değilse tool kataloğa hiç girmiyor.** Boş seçenek listesi zaten
üretilemez, ama asıl sebep o değil: hiçbir şey açamayan bir tool modele yapamayacağı bir
şey vaat eder.

`evals` de defteri artık yapılandırmadan kuruyor. Yoksa ölçüm, üretimin hiç kullanmadığı
bir katalogla koşardı — P27'nin önek için öğrendiği şeyin aynısı.

## Değişmez 8: kabuk yok

Masaüstü denetiminin tamamı argv ile `exec`; hiçbir yerde kabuk, dize birleştirme ya da
`shell=True` yok. Modelden gelen değer hiçbir argv'ye doğrudan girmiyor:

| model ne veriyor | argv'ye ne giriyor |
|---|---|
| `--action close` | `WINDOW_ACTIONS["close"]` → `"Window Close"` (kodda sabit eşleme) |
| `--name tarayici` | `config.apps["tarayici"]` → `("firefox",)` (yapılandırmadan) |
| `--level 40` | `"40%"` — modelin yazabildiği tek serbest sayı, ve 0–100'e sınırlanıyor |

`Kill Window` da bir KWin kısayoludur; listede olmadığı için erişilemez. Yapılandırma
dosyasındaki değer **dizi**, tek metin değil: `"firefox --new-window"` yazılabilseydi onu
bölmek bir kabuk ayrıştırması isterdi ve tırnak kuralları tam da kaçmanın sızdığı yer.

## Bu makine: Wayland + KDE

Mekanizmalar ölçülerek seçildi, hepsi zaten kurulu araçlarla:

| iş | yol | neden bu |
|---|---|---|
| ses | `wpctl` (PipeWire) | seviye oku/yaz tek satır |
| medya | MPRIS, `busctl` | `playerctl` kurulu değil ve gerekmiyor |
| pencere | KWin genel kısayolları (`org.kde.kglobalaccel`) | `wmctrl`/`xdotool` X11; Wayland'da çalışmaz |

**"Şu uygulamaya geç" ve "hangi pencereler açık" bilerek yok.** Kısayol yolu *aktif*
pencere üzerinde çalışıyor; pencere listesi Wayland'da KWin'e script yüklemekten geçiyor
(`org.kde.KWin.Scripting`) ve o kırılgan yol açılmadı.

Adaptörün gerçek yolu elle koşuldu: ses 50 → 53 → 50, medya duraklatıldı (`firefox`),
genel bakış açılıp kapandı. Testler bunu kurmuyor — sahtelerle ölçülen şey hangi argv'nin
kurulduğu ve çıktının nasıl okunduğu; CI'da zaten masaüstü oturumu yok.

## Kaydedilen olgu kimseye bağlanmıyor

`fact_save` olguyu `person_id` olmadan yazıyor. Sebep yapısal: `ToolContext` süreç başına
bir kez kuruluyor, yani tool konuşanın kim olduğunu göremiyor — arka plan çıkarımı
bağlayabiliyor çünkü mesaj satırından okuyor. Bugün pratikte fark yok, §19.3 açık olduğu
sürece `person_id` zaten üretilmiyor (`MAYEN_ASSUME_OWNER`). Konuşmacı tanıma gerçek
olduğunda burası tura bağlı bir kimlik ister; o güne kadar boş bırakmak, olmayan bir
kimliği uydurmaktan doğru.

## Ölçüm

Katalog 16 → 21 tool (uygulama listesi tanımlıysa 22). Katalog metni **783 → 1069 token**
(sayaçtan, Kural 10), 16384'lük bağlamın %6.5'i. Tool başına ~49 token, yani genişleme
bağlam bütçesinde değil **tool seçiminde** ölçülmeli.

Dört küme, iki önek, `Qwen3.8-27B-IQ4_XS`: `docs/faz8-tool-olcum.md`. Taban, aynı modelde
aynı rol metniyle (Edden + dil kuralı) koşulmuş son ölçüm — `docs/faz7-rol.md`. **Üretim
öneği, cli/json:**

| küme | önce | sonra |
|---|---|---|
| altın | 98 / 98 | 98 / 100 |
| kontrol | 100 / 100 | **94 / 94** |
| halüsinasyon | 93 / 93 | 93 / 93 |
| bellek | 82 / 82 | 88 / 88 |

**Katalog beş tool büyüdü ve ölçülebilir bir gerileme yok.** Hareket eden iki kümede de
oynayan tek bir senaryo var (17'de bir, 18'de bir); aralıklar çakışıyor, yani sıralama
değil.

**`kontrol`'ün düşüşü modelin hatası değil, senaryonun bayatlaması.** Düşen tek senaryo iki
biçimde de aynı: `kon-08` — *"Sesini biraz kısabilir misin?"*. Küme onu `TOOL_GEREKMEZ`
diye işaretliyor çünkü yazıldığında **ses tool'u yoktu**; artık var ve model `volume`
çağırıyor. Doğru davranış, yanlış beklenti.

P27'nin altın kümede bulduğunun aynısı ve aynı şekilde bırakılıyor: **senaryo elle
değiştirilmedi.** Değiştirilseydi bu rapor kendinden öncekilerle karşılaştırılamaz olurdu
ve bir kümeyi sonuca uydurmak, ölçümü kendi varsayımını doğrulayan bir teste çevirir.
Beklentinin güncellenmesi sahibin kararı; güncellenirse `kontrol` 100/100'e döner.

**Ölçülmeyen şey:** yeni tool'ların kendileri hiçbir kümede senaryo olarak yok. Ölçülen şey
"katalog büyüdü, eskisi bozuldu mu" — cevabı hayır. "Model `window_action`'ı doğru
seçiyor mu" sorusunun bir sayısı **yok**; elle görülen üç doğru (ses oku, ses ayarla, medya
duraklat) ve iki uydurma (aşağıda) bir ölçüm değil.

## Elle görülen: iki uydurulmuş eylem

Gerçek turda iki başarısızlık görüldü ve ikisi de aynı sınıf — **çağrı yapmadan "yaptım"
demek**:

```
--- metin düzenleyiciyi aç      → "I am launching the text editor" (tool çağrılmadı, kwrite açılmadı)
--- kahveyi sade içtiğimi unutma → "I will remember that" (tool çağrılmadı, olgu yazılmadı)
```

Bu yeni bir sınıf değil: `halusinasyon` kümesinin ölçtüğü şeyin ta kendisi ve rol metninin
bilinen kalan açığı. `CLAUDE.md`'de yazılı ödün burada da geçerli — "gereksiz çağrı
gecikmedir; 'evet, kurdum' `issues.md`'dir." Yeni tool'ların bu sınıfı **büyütüp
büyütmediği** ölçümün cevaplaması gereken soru; elle görülen iki vaka bir sayı değil.
