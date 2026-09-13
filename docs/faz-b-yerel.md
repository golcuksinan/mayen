# Yerel tool çağrısı: kabul kapısında ölçüm

Tarih: 2026-08-16. Model: `Qwen3.8-27B-IQ4_XS`, açgözlü örnekleme. Ham rapor:
`docs/faz-b-yerel-ham.md`. Sondaj: `docs/faz-b-sondaj-yerel.md`.

Koşu: `uv run --env-file .env python -m evals.session --model … --yerel --ozetlemesiz`

## Neden koşuldu

Sahibin elle koşusunda model bir çağrıyı **taklit etti**: düz metin dalına kilitlenmişken
`[tool] date_time` yazdı, hiçbir şey koşmadı ve cümle sesli okundu. Log'da o tur için
"tool adımı" satırı yok, gramerde `<` yasak — yani gördüğümüz şey bir çağrı değil, bir
çağrının kılığı.

Bunun öncesinde `<` gramerde yasaklanmıştı, çünkü model aynı şeyi `<tool> date_time`
yazarak yapıyordu. **Yasak davranışı kaldırmadı, kılığını değiştirdi.** Altta yatan
neden tasarımsal: §6/C3 gereği model bir üretimde ya konuşabiliyor ya çağırabiliyor, ve
burada ikisini birden istiyordu — "anladım, kuruyorum; ama önce saati almam lazım".
Modelin kendi şablonunda bu çakışma yok: `content` ile `tool_calls` aynı yanıtta durur.

## Sonuç

| kol | beklenen çağrı | gelen [%95] | ilk atlanan tur | gereksiz çağrı |
|---|---:|---:|---:|---:|
| bugünkü biçim (CLI, katalog promptta) | 15 | 12 (80%) [55–93%] | 23 | 4 |
| yerel (katalog `tools`'ta, çağrıyı sunucu ayrıştırıyor) | 15 | **14 (93%)** [70–99%] | **28** | 4 |

**Wilson aralıkları örtüşüyor, yani bu bir sıralama değil (Kural 14).** İki koşu da
`--tekrar 2` ile birebir tekrarlandı: açgözlü örneklemede oturum belirlenimci ve
öyle çıktı, yani fark gürültü değil — ama iki senaryoluk bir fark, on beş paydada
istatistiksel olarak ayrışmıyor.

**Sayının altındaki şey sayıdan net:** yerel kolun çevirdiği iki tur, Faz B/1'den beri
açıkta duran **tek arıza sınıfı**. 23 (`tamam kıs artık`) ve 24 (`sesi kıs sesi alo`) —
kullanıcı ısrar ediyor, model "zaten kısık" diyor ve çağırmıyor. Yerel kolda dördü de
çağrıldı (21→30%, 22→20%, 23→10%, 24→5%). Kalan tek kaçık 28 (`hayır kullanmadın şimdi
kullan`), iki kolda da yanlış tool'a gidiyor.

Gereksiz çağrı sayısı **değişmedi** (4/4, dördü de `saat kaç`). Yani kazanç "her tura
tool çağıran bir model" değil; negatif kontrol yerinde duruyor.

## Ne ölçülmedi, ne yanlış okunur

1. **Önek jetonu sütunu iki kol arasında karşılaştırılamaz.** Yerelde 744–1345, CLI'da
   1945–2650 görünüyor; **katalog kaybolmadı, sayılmıyor.** `count_tokens` mesaj
   metnini sayıyor ve katalog artık `tools` alanında. Gerçek bağlam tüketimi ölçülmedi.
2. **İlk ses ölçülmedi.** Sondaj kollar arasında ayrım bulamamıştı (2.13–2.66 s, hepsi);
   burada süre hiç raporlanmıyor. §19 madde 4 açık.
3. **Tek senaryo, tek model.** `otu-01`, 28 tur, 15 beklenen çağrı. Rol metni bu modelde
   ve **CLI biçimi için** yazıldı; yerel kolda sistem promptundan katalog ve çağrı
   sözdizimi çıkıyor, yani rol metni ölçülmemiş bir öneğin içinde koşuyor.
4. **§17.1'in uyarısı burada şekil değiştiriyor.** Gramerde uydurulan bir tool adı
   *üretilemezdi*; şemada üretilebilir. Bu koşuda `bilinmeyen tool` sıfır çıktı ve bu
   sayı ilk kez gerçekten modeli ölçüyor — ama tek koşunun sıfırı "olmaz" demek değil.
5. **Ölçüm bir kez kirlendi ve düzeltildi.** İlk denemede geçmişteki çağrı asistan
   **metni** olarak yazılıyordu; model onuncu turdan sonra biçimi kopyaladı ve dört turda
   cevap olarak `{"name": "volume", "arguments": {...}}` üretti — 6/15. Düzeltme:
   `PromptMessage.tool_calls` (`adapters/llm.py`) ve `evals/session.py:_native_history`.
   **Ders eskisinin aynısı:** model geçmişte kendi ürettiği biçimi görmeli, yoksa ölçülen
   şey çağrı arayüzü değil geçmişin biçimi olur.

## Kod: ne değişti, ne değişmedi

Üretimin çağrı yolu **değişmedi**. `CallFormat`'a üçüncü bir değer eklenmedi; `main.py`
hâlâ CLI seçiyor ve ajan döngüsü yerel biçimi tanımıyor. Eklenenler:

- `src/mayen/tools/schema.py` — defterden JSON şema, `grammar.py`'nin üçüncü kardeşi.
  Kaynak tek: şema `usage()` gibi imzadan türetiliyor. `ENUM` → `enum`.
- `adapters/llamacpp.py:stream_native` — `tools` alanı, `tool_calls` akışı, geçmişteki
  çağrının `tool_calls` olarak geri yazılması. `LLMClient` arayüzünde **değil**.
- `adapters/llm.py:NativeCall` ve `PromptMessage.tool_calls` — metin biçimlerinde boş
  kalıyor, hiçbir şeyi değiştirmiyor.
- `evals/session.py --yerel` — iki kol aynı koşuda, aynı sunucuda, tek raporda.

## Üretime alındıktan sonra: dört küme yeniden ölçüldü

Sahibin kararıyla `main.py:CALL_FORMAT` yerel biçime alındı ve **önek değiştiği için**
dört küme yeniden koşuldu (`docs/faz-b-yerel-kumeler.md`, üretim öneği, dil kuralı açık —
üretimin koşulu). Kural bizim kendi kuralımız: model ya da önek değişirse rol metni
yeniden ölçülür.

| küme | cli | json | **yerel** |
|---|---:|---:|---:|
| altın (50) | 98% | 98% | **92%** [81–97] |
| kontrol (18) | 89% | 89% | **94%** [74–99] |
| halüsinasyon (15) | 93% | 100% | **100%** [80–100] |
| bellek (17) | 88% | 88% | **82%** [59–94] |
| argüman doğruluğu | 89% | 91% | **94%** |

Hiçbir eksen çökmedi ve bütün aralıklar örtüşüyor. Altındaki üç senaryoluk düşüşün
**dördü de aynı sınıf**: model çağırmak yerine **eksik alanı sordu** (`cok-06`, `ayr-03`,
`ser-05` telefon/saat istiyor; `eks-05` listelemeye gidiyor). Rol metninin önkoşul kuralı
yerel önekte daha güçlü tutuyor. Beklentiyi değiştirmedim — `kon-08`'in kuralı: kümeyi
sonuca uydurmak, ölçümü kendi varsayımının testine çevirir. Kalan ikisi gerçek argüman
hatası (`tek-07`, `tek-12`).

**Dil kuralı yerel biçimde yerini değiştirmek zorunda kaldı ve bu ölçülebilir.** Kuralsız
kolda `kontrol` 78%, kurallı kolda 94% — ve kural sistem promptunun sonunda bırakıldığında
elle koşuda **altı turun altısı Türkçe** çıktı. Sebebi Faz 7'nin kaldıracının tersine
dönmesi: katalogu artık şablon ekliyor ve `tools` bloğunu bizim metnimizin **arkasına**
koyuyor, yani sistem promptunun sonu öneğin sonu olmaktan çıktı. Kural bağlam bloğunun
sonuna taşındı — Faz 7'nin "değişkenin arkasına koyma" yasağıyla çakışmıyor, çünkü bağlam
bloğu zaten değişken ve zaten orada; yasaklanan şey sabit kuyruktan sonra **yeni bir mesaj**
açmaktı (22 → 1631 önek jetonu). Taşındıktan sonra altı turun altısı İngilizce.

**İki adımlı zincir üretimde ilk kez çalıştı.** Elle koşuda "10 saniye sonra bir şey
yapcam da hatırlat" → model eksik alanı sordu; alan gelince tek turda `date_time` **ve**
`task_create`. Bugüne kadar model bunu yapmak isteyip çağrıyı düz metinde taklit ediyordu.

**Düzeltme turu yerel biçimde sıfır** ve bu bir üstünlük değil, tanım: düzeltilecek
sözdizimi hatası taşımanın altında kalıyor. TTFT 0.26 → 0.38 s; aynı koşuda üretilen
ortalama token da 12 → 8, yani ikisi doğrudan karşılaştırılamaz ve §19 madde 4 açık.

## Karar ve açıkta kalanlar

**Sahip yerel biçimi seçti (2026-08-16)** ve gerekçe bir puan değil: metin biçimlerinde
model konuşmakla çağırmak arasında seçim yapmak zorunda ve ikisini birden istediğinde
çağrıyı taklit ediyor. Karakter yasaklamak o sınıfı çözmüyor, kılığını değiştiriyor.

Açıkta kalanlar, hiçbiri varsayımla kapatılmadı:

- **§19 madde 4 (ilk ses bütçesi) hâlâ açık.** TTFT iki kolda karşılaştırılabilir değil.
- **Rol metni bu önekte yeniden yazılmadı**, yalnızca ölçüldü. Altındaki dört senaryo
  "çağırmak yerine sordu" sınıfı; metni onlara göre düzeltmek fitting olurdu ve zaten
  bir turdan sonra durma kuralı var (`docs/faz6-27b-rol3.md`).
- **`bellek` 82%** — tek senaryo, ama üç biçimde de en zayıf küme.
- Metin biçimleri kodda duruyor. Model değişirse yeniden ölçülecek tek satır
  `main.py:CALL_FORMAT`.
