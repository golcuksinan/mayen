# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384
- sunucunun varsayılan örneklemesi: `temperature`=0.699999988079071, `top_k`=20, `top_p`=0.800000011920929, `min_p`=0.0, `repeat_penalty`=1.0, `presence_penalty`=1.5, `frequency_penalty`=0.0
- adaptör her istekte `temperature: 0.0` gönderiyor ve sunucunun varsayılanını ezer; kalan ayarlar sunucudan gelir, yani modeller arasında **eşitlenmeleri gerekir** (`mayen/adapters/llamacpp.py`).

## Önek

Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi** olduğu sonucu değiştirir (P27):

- **ölçüm öneği** — `docs/faz2-olcum.md`'den beri kullanılan dizi: çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]` bloğu ve olgular **yok**.
- **üretim öneği** — `turn/runner.py`'nin modele gerçekten gönderdiği dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.

Rol metni: `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest | 50 | 94% [84%–98%] | 91% | — | 0 | 0 | 0 (5) | 4 | 0 | 15 | 0.24 | 0.38 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu | 50 | 86% [74%–93%] | 88% | — | 0 | 0 | 1 (5) | 0 | 0 | 10 | 0.24 | 0.33 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × serbest | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 24 | 0.10 | 0.31 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × zorunlu | 18 | 89% [67%–97%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 6 | 0.12 | 0.18 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × serbest | 15 | 73% [48%–89%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 11 | 0.92 | 1.02 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × zorunlu | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 8 | 0.92 | 0.99 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × serbest | 17 | 71% [47%–87%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 11 | 1.25 | 1.35 |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × zorunlu | 17 | 59% [36%–78%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 10 | 1.25 | 1.34 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest | 50 | 96% [87%–99%] | 91% | — | 0 | 0 | 1 (5) | 0 | 0 | 21 | 0.23 | 0.42 |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu | 49 | 86% [73%–93%] | 91% | — | 0 | 0 | 0 (4) | 0 | 3 | 20 | 0.26 | 0.47 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × serbest | 18 | 100% [82%–100%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 23 | 0.10 | 0.29 |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × zorunlu | 18 | 89% [67%–97%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 6 | 0.12 | 0.18 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × serbest | 15 | 87% [62%–96%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.92 | 1.08 |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × zorunlu | 15 | 100% [80%–100%] | 100% | — | 0 | 0 | 0 (0) | 0 | 0 | 18 | 0.93 | 1.10 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest | 16 | 75% [51%–90%] | 100% | — | 0 | 0 | 0 (6) | 4 | 0 | 21 | 1.21 | 1.40 |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × zorunlu | 17 | 65% [41%–83%] | 100% | — | 0 | 0 | 0 (7) | 0 | 0 | 20 | 1.25 | 1.42 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest | 100% | 100% | 86% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu | 100% | 100% | 14% | 100% | 100% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × serbest | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × zorunlu | — | — | — | 89% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × serbest | — | — | — | 100% | 71% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × zorunlu | — | — | — | 100% | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × serbest | 100% | — | — | 33% | 50% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × zorunlu | 100% | — | — | 0% | 50% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest | 100% | 100% | 100% | 100% | 88% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu | 100% | 100% | 14% | 100% | 100% | 86% |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × serbest | — | — | — | 100% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × zorunlu | — | — | — | 89% | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × serbest | — | — | — | 100% | 86% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × zorunlu | — | — | — | 100% | 100% | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest | 100% | — | — | 33% | 100% | 100% |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × zorunlu | 100% | — | — | 0% | 100% | 100% |

## Bağlam kırılımı (tool doğruluğu)

Kova sınırı: **200 jeton** ve üstü "uzun" (P27). Sayan taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor kovası, sistemde bir eşik değil (`evals/runner.py`).

Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor, yani eşik yanlış seçilmişse okuyan görüyor.

| koşu | geçmişsiz | kısa geçmiş | uzun geçmiş |
|---|---|---|---|
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest | 94% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu | 86% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × serbest | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × zorunlu | 89% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × serbest | — | 73% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × zorunlu | — | 100% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × serbest | — | 64% (11) | 83% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × zorunlu | — | 55% (11) | 67% (6) |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest | 96% (50) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu | 86% (49) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × serbest | 100% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × zorunlu | 89% (18) | — | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × serbest | — | 87% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × zorunlu | — | 100% (15) | — |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest | — | 73% (11) | 80% (5) |
| Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × zorunlu | — | 64% (11) | 67% (6) |

Kovaların gerçek doluluğu (ortalama jeton, ve `n_ctx`=16384 içindeki payı):

- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × serbest**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × zorunlu**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × serbest**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × zorunlu**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × serbest**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × zorunlu**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu**: geçmişsiz ~44 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × serbest**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × zorunlu**: geçmişsiz ~43 jeton (%0.3)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × serbest**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × zorunlu**: kısa geçmiş ~101 jeton (%0.6)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)
- **Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × zorunlu**: kısa geçmiş ~156 jeton (%1.0), uzun geçmiş ~574 jeton (%3.5)


## Ölçülemeyen senaryolar

Servis iki denemede de düştü. Bu satırlar **hiçbir doğruluk paydasına girmiyor**: modelin yanlışı değil, ölçümün eksiği. Yanlış cevap sayılsalardı model servisin kopmasından sorumlu tutulurdu; hiç yazılmasalardı payda sessizce küçülür ve rapor eksikliğini gizlerdi (Kural 13, Kural 14).

**Bir sayı burada görünüyorsa o koşu eksiktir ve öyle okunmalıdır.**

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu** — 1/50:

- `tek-02`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: Server disconnected without sending a response.

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest** — 1/17:

- `bel-11`: Qwen3.6-35B-A3B-IQ4_XS: akış kesildi: Server disconnected without sending a response.


## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu** — desteksiz sayı geçen senaryolar:

- `tek-10`: `6` — yanıt: `Bir hatırlatıcın var. İlaç için yarın sabah saat 6'da uyarılacaksın.`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest** — desteksiz sayı geçen senaryolar:

- `tek-01`: `12` — yanıt: `Şu an saat 12:00, Pazar günü.`

Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest** — desteksiz alıntı geçen senaryolar:

- `yok-03`: `Bilgisayarım bozuldu, ne yapacağımı bilmiyorum.`, `Ne oldu?`, `Ekranı mavi oldu.`, `O normal, Windows'un en sevdiği renk.`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest** — desteksiz alıntı geçen senaryolar:

- `bel-12`: `name`, `course_schedule`, `arguments`, `day`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest** — 15 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Silinecek notun numarasını söyler misin?`
- `eks-04`: `Ne zaman ve neyi hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Kimin numarasını ekleyelim? Adı ve telefon numarası nedir?`
- `yok-01`: `Rica ederim. Başka bir işin var mı?`
- `yok-02`: `İyiyim, teşekkürler. Sen nasılsın?`
- `yok-03`: `Tabii, işte bir tane. Bir adamın biri arkadaşına demiş ki; "Bilgisayarım bozuldu, ne yapacağımı bilmiyorum." Arkadaşı sormuş: "Ne oldu?" Adam: "Ekranı mavi oldu." Arkadaş: "O normal, Windows'un en sev`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir şey yoksa buradayım.`
- `yok-06`: `Ben Mayen, tek bir makinede çalışan sesli asistanınım. Rehberindeki kişileri yönetebilir, notlar oluşturup arayabilir, ders programını ve hava durumunu kontrol edebilir, görevler kurup iptal edebilir,`
- `yok-07`: `Dört eder.`
- `yok-08`: `Ben bir sesli asistanım ama konuşma hızımı senin için ayarlayamam. Bu ayarı cihazının ses veya erişilebilirlik menüsünden yapabilirsin. Başka bir konuda yardımcı olabilir miyim?`
- `ayr-03`: `Telefon numarası nedir?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu** — 9 yanıt:

- `eks-04`: `<tool> no_tool`
- `yok-01`: `<tool> no_tool`
- `yok-02`: `<tool> no_tool`
- `yok-03`: `<tool> no_tool`
- `yok-04`: `<tool> no_tool`
- `yok-05`: `<tool> no_tool`
- `yok-06`: `<tool> no_tool`
- `yok-07`: `<tool> no_tool`
- `yok-08`: `<tool> no_tool`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × serbest** — 18 yanıt:

- `kon-01`: `İyi geceler.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir şey var mı?`
- `kon-05`: `Evet, gerçekten güzel bir akıştı.`
- `kon-06`: `Temelde iki ana bileşenden oluşur: donanım ve yazılım. Donanım, fiziksel parçalar; yazılım ise bu parçaları yöneten talimatlar demektir. İşlemci (CPU), verileri işlerken bellek (RAM) geçici olarak sak`
- `kon-07`: `Anladım, sakin ol. Sana nasıl yardımcı olabilirim? Bir sorun mu var yoksa sadece konuşmak mı istedin?`
- `kon-08`: `Bu isteği doğrudan yerine getiremiyorum. Ses seviyeni cihazının ayarlarından düşebilirsin.`
- `kon-09`: `Evet, bakabilirim. Hangi şehrin hava durumunu öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda sistem, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderir. Bu bildirimle birlikte de o görevi iptal etme seçeneğin olur.`
- `kon-11`: `Evet, notların yalnızca sana aittir ve senin dışarıda kimseye göstermem.`
- `kon-12`: `Rehber, telefon numaralarını ve kişileri sakladığın yerdir. İsim ekleyebilir, güncelleyebilir veya silebilirsin.`
- `kon-13`: `Tamam, not ettim. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, anladım. Başka bir isteğin olursa buradayım.`
- `kon-15`: `Bugün saat kaç?`
- `kon-16`: `Anladım, Ali ile konuştuğunuzu ve durumunun iyi olduğunu not ettim. Başka bir konuda yardımcı olabilir miyim?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Bugün senin için özel bir planın var mı?`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. Belki biraz dinlenmek ya da farklı bir şey yapmak daha iyi gelebilir.`

**Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × zorunlu** — 16 yanıt:

- `kon-01`: `<tool> no_tool`
- `kon-02`: `<tool> no_tool`
- `kon-03`: `<tool> no_tool`
- `kon-04`: `<tool> no_tool`
- `kon-05`: `<tool> no_tool`
- `kon-06`: `<tool> no_tool`
- `kon-07`: `<tool> no_tool`
- `kon-08`: `<tool> no_tool`
- `kon-10`: `<tool> no_tool`
- `kon-11`: `<tool> no_tool`
- `kon-12`: `<tool> no_tool`
- `kon-13`: `<tool> no_tool`
- `kon-14`: `<tool> no_tool`
- `kon-16`: `<tool> no_tool`
- `kon-17`: `<tool> no_tool`
- `kon-18`: `<tool> no_tool`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × serbest** — 5 yanıt:

- `hal-03`: `Üç`
- `hal-06`: `Üç tane.`
- `hal-12`: `Evet, Veli'yi eklemiştim. Şimdi kontrol edeyim.  <tool> contact_get --name Veli`
- `hal-14`: `Evet, akşam yedide ilacı hatırlatacak bir görev oluşturuldu.`
- `hal-15`: `Rica ederim. Başka bir şey var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × zorunlu** — 1 yanıt:

- `hal-15`: `<tool> no_tool`

**Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × serbest** — 2 yanıt:

- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-12`: `Bunu kontrol edeyim.  <tool> course_schedule --day 1`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest** — 16 yanıt:

- `eks-01`: `Hangi şehir için bakmamı istersin?`
- `eks-02`: `Silinecek notun numarasını söyler misin?`
- `eks-03`: `Uyandırmak istediğin cihazın adı nedir?`
- `eks-04`: `Ne zaman ve ne hakkında hatırlatmamı istersin?`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istersin? Lütfen görevin numarasını söyle.`
- `eks-06`: `Silinecek kişinin adını söylemen lazım.`
- `eks-07`: `Kimin numarasını ekleyelim? Adı ve telefon numarası nedir?`
- `yok-01`: `Rica ederim. Başka bir işin var mı?`
- `yok-02`: `İyiyim, teşekkürler. Sana nasıl yardımcı olabilirim?`
- `yok-03`: `Tabii, işte bir tane:  Neden bilgisayarlar asla üşümez? Çünkü Windows'ları var!`
- `yok-04`: `Paris.`
- `yok-05`: `Tamam, başka bir şey yoksa buradayım.`
- `yok-06`: `Ben Mayen. Tek bir makinede çalışan ve kendi verilerine sahip bir sesli asistanım. Rehberindeki kişileri yönetebilir, notlar oluşturup arayabilir, ders programını görebilir, görevler oluşturup iptal e`
- `yok-07`: `Dört eder.`
- `yok-08`: `Hız ayarını değiştiremiyorum, bu benim kontrolümde değil. Konuşma hızı cihazının ses ayarlarından düzenlenebilir.`
- `ayr-03`: `Telefon numarasını verir misin?`

**Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu** — 9 yanıt:

- `eks-07`: `<tool> no_tool`
- `yok-01`: `<tool> no_tool`
- `yok-02`: `<tool> no_tool`
- `yok-03`: `<tool> no_tool`
- `yok-04`: `<tool> no_tool`
- `yok-05`: `<tool> no_tool`
- `yok-06`: `<tool> no_tool`
- `yok-07`: `<tool> no_tool`
- `yok-08`: `<tool> no_tool`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × serbest** — 18 yanıt:

- `kon-01`: `İyi geceler.`
- `kon-02`: `Buyur, nasıl yardımcı olabilirim?`
- `kon-03`: `Tamam, bekliyorum.`
- `kon-04`: `Rica ederim. Başka bir şey var mı?`
- `kon-05`: `Evet, gerçekten de öyleydi.`
- `kon-06`: `Temelde işlemci, bellek ve depolama birimlerinin birlikte çalışmasıyla gerçekleşir. İşlemci talimatları işler, bellek geçici verileri tutar, depolama ise kalıcıdır. Detaylı bilgi mi istersin?`
- `kon-07`: `Anladım, bazen her şey üst üste gelebiliyor. Sana nasıl yardımcı olabilirim? Bir not kaydetmemi ister misin, yoksa sadece sohbet mi etmek istersin?`
- `kon-08`: `Ben bir sesli asistanım ama cihazının ses ayarlarını doğrudan kontrol etme yetkim yok. Lütfen telefonunun veya bilgisayarının ses seviyesini kendin düşür.`
- `kon-09`: `Evet, bakabilirim. Hangi şehir için öğrenmek istersin?`
- `kon-10`: `Görev oluşturduğunda, belirlediğin tarihte ve saatte sana bir hatırlatma bildirimi gönderiyorum. Bu bildirimde de o görevle ilgili mesaj yer alıyor.`
- `kon-11`: `Evet, notların yalnızca sana özeldir. Başkaları erişemez.`
- `kon-12`: `Rehber, telefon numaralarını ve kişileri sakladığın yerdir. İstersen oraya yeni bir kişi ekleyebilir, var olanları arayabilir veya silebilirim.`
- `kon-13`: `Tamam, not ettim. Başka bir isteğin var mı?`
- `kon-14`: `Tamam, başka bir sorun yoksa buradayım.`
- `kon-15`: `Bugün saat kaçta?`
- `kon-16`: `Anladım, Ali ile konuştuğunu ve durumunun iyi olduğunu not ettim. Başka bir konuda yardımcı olabilir miyim?`
- `kon-17`: `Evet, zaman gerçekten çok hızlı akıyor. Şu an 9 Eylül 2026, saat 09:00.`
- `kon-18`: `Anlıyorum, bazen öyle günler olur. Belki biraz dinlenmek ya da sevdiğin bir şey yapmak daha iyi gelebilir.`

**Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × zorunlu** — 16 yanıt:

- `kon-01`: `<tool> no_tool`
- `kon-02`: `<tool> no_tool`
- `kon-03`: `<tool> no_tool`
- `kon-04`: `<tool> no_tool`
- `kon-05`: `<tool> no_tool`
- `kon-06`: `<tool> no_tool`
- `kon-07`: `<tool> no_tool`
- `kon-08`: `<tool> no_tool`
- `kon-10`: `<tool> no_tool`
- `kon-11`: `<tool> no_tool`
- `kon-12`: `<tool> no_tool`
- `kon-13`: `<tool> no_tool`
- `kon-14`: `<tool> no_tool`
- `kon-16`: `<tool> no_tool`
- `kon-17`: `<tool> no_tool`
- `kon-18`: `<tool> no_tool`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × serbest** — 3 yanıt:

- `hal-06`: `Üç tane.`
- `hal-14`: `Evet, kurdum. Akşam yedide hatırlatacak.`
- `hal-15`: `Rica ederim. Başka bir şey var mı?`

**Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × zorunlu** — 1 yanıt:

- `hal-15`: `<tool> no_tool`

**Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest** — 2 yanıt:

- `bel-03`: `Hayır, sabahları erken kalkmayı sevmediğini söylemiştin.`
- `bel-12`: `Bunu kontrol edeyim.  <tool> {"name": "course_schedule", "arguments": {"day": 1}} </tool>`

## Başarısız senaryolar

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × serbest — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target ?`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarası nedir?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message Kütüphane kitabını geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × üretim öneği × zorunlu — 11/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> wake_on_lan --target masaüstü bilgisayar`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): phone fazladan verildi — çıktı: `<tool> contact_save --name Veli --phone 5551234567`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `eks-02` (eksik argüman): düz metin beklenirken note_search çağrıldı — çıktı: `<tool> note_search --query ""`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> wake_on_lan --target ?`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> task_list`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get`
- `eks-07` (eksik argüman): düz metin beklenirken contact_save çağrıldı — çıktı: `<tool> contact_save --name ? --phone ?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Annemi ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T10:00:00Z --message Annemi ara ve doğum gününü kutla`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-15T09:00:00Z --message Kütüphane kitabını geri ver`

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × serbest — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × kontrol × üretim öneği × zorunlu — 2/18

- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `kon-15` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul --fields temperature,condition`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × serbest — 4/15

- `hal-03` (ayırt etme): note_search beklenirken çağrı üretilmedi — çıktı: `Üç`
- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-12` (ayırt etme): contact_get beklenirken çağrı üretilmedi — çıktı: `Evet, Veli'yi eklemiştim. Şimdi kontrol edeyim.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, akşam yedide ilacı hatırlatacak bir görev oluşturuldu.`

### Qwen3.6-35B-A3B-IQ4_XS × cli × halusinasyon × üretim öneği × zorunlu — 0/15

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × serbest — 5/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-05` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-17` (ayırt etme): note_search beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Annem`

### Qwen3.6-35B-A3B-IQ4_XS × cli × bellek × üretim öneği × zorunlu — 7/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-03` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-05` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Deniz`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> fact_list`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> course_schedule --day 1`
- `bel-17` (ayırt etme): note_search beklenirken contact_get çağrıldı — çıktı: `<tool> contact_get --name Annem`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × serbest — 5/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarasını verir misin?`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "kütüphane kitabını ayın on beşin`

### Qwen3.6-35B-A3B-IQ4_XS × json × üretim öneği × zorunlu — 10/50

- `tek-04` (tek tool): city: 'İstanbul' beklenirken 'Istanbul' geldi — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul", "fields": ["temperature"]}}`
- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): weather: 'city' boş olamaz; düz metin beklenirken note_search çağrıldı — çıktı: `<tool> {"name": "note_search", "arguments": {"query": "hava durumu"}}`
- `eks-02` (eksik argüman): düz metin beklenirken note_delete çağrıldı — çıktı: `<tool> {"name": "note_delete", "arguments": {"id": 1}}`
- `eks-03` (eksik argüman): wake_on_lan: 'target' boş olamaz; düz metin beklenirken system_metrics çağrıldı — çıktı: `<tool> {"name": "system_metrics", "arguments": {}}`
- `eks-04` (eksik argüman): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T14:00:00Z", "message": "Hatırlatma"}}`
- `eks-05` (eksik argüman): düz metin beklenirken task_list çağrıldı — çıktı: `<tool> {"name": "task_list", "arguments": {}}`
- `eks-06` (eksik argüman): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `ser-06` (serbest metin): note_create beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-15T09:00:00Z", "message": "kütüphane kitabını ayın on beşin`

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × serbest — 0/18

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × kontrol × üretim öneği × zorunlu — 2/18

- `kon-09` (tool gerekmez): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Ankara"}}`
- `kon-15` (tool gerekmez): düz metin beklenirken date_time çağrıldı — çıktı: `<tool> {"name": "date_time", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × serbest — 2/15

- `hal-06` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Üç tane.`
- `hal-14` (ayırt etme): task_list beklenirken çağrı üretilmedi — çıktı: `Evet, kurdum. Akşam yedide hatırlatacak.`

### Qwen3.6-35B-A3B-IQ4_XS × json × halusinasyon × üretim öneği × zorunlu — 0/15

Yok.

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × serbest — 4/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`

### Qwen3.6-35B-A3B-IQ4_XS × json × bellek × üretim öneği × zorunlu — 6/17

- `bel-01` (tool gerekmez): düz metin beklenirken contact_get çağrıldı — çıktı: `<tool> {"name": "contact_get", "arguments": {}}`
- `bel-02` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-03` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-05` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-10` (tool gerekmez): düz metin beklenirken fact_list çağrıldı — çıktı: `<tool> {"name": "fact_list", "arguments": {}}`
- `bel-12` (tool gerekmez): düz metin beklenirken course_schedule çağrıldı — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 1}}`

## Okuma (2026-08-15) — P25'in kararı yeni rol metniyle de ayakta

**Soru sahibinden geldi:** zorunlu tool modu (P25) ölçülüp silindiğinde bugünkü rol metni
yoktu. O zamanki metin *"Tool kullan her zaman lazımsa"* diyordu, yani gramer de prompt da
modeli aynı yöne itiyordu. Yeni metin ters yönde bir kural taşıyor — eksik bilgi varsa
çağırma, sor — ve zorunlu modun `no_tool` kaçışı zaten vardı. Fark yaratır mıydı?

**Yaratmadı.** Karar ölçütü koşudan önce yazılmıştı: zorunlu mod **kontrol ve bellek**
kümelerinde serbesti geçmeliydi. İkisinde de geriledi.

| küme | serbest | zorunlu |
|---|---|---|
| halüsinasyon, CLI / JSON | %73 / %87 | **%100 / %100** |
| altın, CLI / JSON | **%94 / %96** | %86 / %86 |
| kontrol, CLI / JSON | **%100 / %100** | %89 / %89 |
| bellek, CLI / JSON | **%71 / %75** | %59 / %65 |

Halüsinasyondaki %100 bir başarı değil: o kümede zaten çağırmasını istiyoruz ve zorunlu mod
çağırmamayı imkânsıza yakın kılıyor. Ölçtüğü şey modelin ayırt etmesi değil, gramerin
zorlaması — §17.1'in `uydurulan tool` sütunuyla aynı türden bir sıfır.

**Asıl bulgu eksen kırılımında: eksik argüman ekseni CLI'de %86 → %14.**

- `eks-02` → `<tool> note_search --query ""`
- `eks-03` → `<tool> wake_on_lan --target ?`

**Zorunlu modda "sormak" diye bir davranış yok.** `no_tool` "bu tur tool gerekmiyor" demek;
"tool gerekiyor ama bilgim eksik" diyecek bir dal yok. Model de boş string ve soru işareti
uyduruyor. Bugün rol metnine yazdığımız öncelik kuralı — *eksik bilgiyle çağırmaktansa
sormak doğrudur* — zorunlu modda **uygulanamaz bir kural**: prompt ile gramer çelişiyor ve
gramer kazanıyor, kazanması da gerekiyor (Değişmez: gramer güvenlik sınırı, prompt değil).

Yani P25'in silme kararı bu metinle de doğru, ama gerekçesi keskinleşti: sorun "model fazla
çağırıyor" değil, **kaçış yolunun yanlış yerde olması.**

## Yamanın durumu

`docs/faz4/zorunlu-mod-geri-alma.patch` **bayatladı.** P26/P27 `evals/` ve `main.py`'yi
değiştirdi; yama on dört dosyanın dördünde çakışıyor (`git apply --check` başarısız).
Kaynak tarafı (`grammar.py`, `calls.py`, `loop.py`, `prompt.py`) temiz uyguluyor, `evals`
borulaması elle taşınıyor — yaklaşık yarım saatlik iş. Bu ölçüm ana ağaçta değil, bir
kopyada koşuldu; `src/` ve `config/` değişmedi.
