# 27B ve 35B karşılaştırması — sonuç: ayırt edilemiyor (2026-08-13)

Ham raporlar: `docs/faz5-model-27b.md`, `docs/faz5-model-35b.md`.

> **Not (2026-08-15).** Bu belge "35B'de kalındı" diye okunmamalı. Sahip 35B kararını hiç
> vermediğini belirtti; §19.2'nin LLM yarısı yeniden **AÇIK** ve seçilmiş bir model yok.
> **Buradaki ölçümler geçerli** — geri alınan şey ölçüm değil, ölçümün yanına yazılıp karar
> hâline gelmiş çıkarım. Zaten bu belgenin kendi sonucu da "doğruluk karar veremedi" idi.
> Ayrıca sunucuda artık Qwen3.8-27B-IQ4_XS koşuyor (`docs/faz6-olcum.md`), yani aşağıdaki
> iki aday da bugün kurulu değil.

**Bu belgenin varlık sebebi, ham raporların yanlış okunmasını engellemek.** Tek tek
hücrelere bakan biri sağlamlık kümesinde %90'a %80, argüman doğruluğunda %89'a %62 görür
ve "27B kazandı" der. **Öyle değil.** Paydalar 7–10 ve aralıklar çakışıyor; bu, P7'de bir
kez düşülen ve `evals/report.py:wilson()`'ın önlemek için yazıldığı hatanın aynısı.

## Neden koşuldu

§19.2'nin LLM yarısı P21'de (2026-08-10) Qwen3.6-35B-A3B olarak kapanmıştı. 2026-08-13'te
o kararın **tek maddi dayanağının VRAM olduğu** görüldü: 27B tek başına 15628 MiB alıyor ve
karta STT/TTS için yer bırakmıyor (`PLAN.md`, P9). Sahip VRAM kısıtını masadan kaldırınca
(STT ertelemesi sürüyor) geriye kararı taşıyan bir şey kalmadı ve doğruluğun ikisini
ayırıp ayırmadığı soruldu.

Bir tutarsızlık da düzeltildi: VRAM 49k ctx'te ölçülmüştü, bütün doğruluk ölçümleri
16384'te. Bu koşu ikisini aynı yapılandırmaya getiriyor.

## Koşulun koşulları

İki model aynı gün, **aynı kodla** (zorunlu tool modu silindikten sonra), `n_ctx` 16384 ve
`presence_penalty` 1.5 ile koşuldu. Kümeler: altın (50), kontrol (18), adım2 (8), sağlamlık
(10), uzun (4), geçmiş izli/izsiz (10+10) — biçim başına 110 senaryo.

**İki model de kendi önceki koşusunu birebir tekrarladı** (`docs/faz4/`). Ölçümün kararlı
olduğunun kanıtı; aynı zamanda zorunlu modun silinmesinin serbest dalı bozmadığının ikinci
doğrulaması.

## Sonuç: havuzlanmış tool doğruluğu

| | CLI | JSON |
|---|---|---|
| 27B | 101/110 = %92 [85–96] | 99/109 = %91 [84–95] |
| 35B | 100/110 = %91 [84–95] | 98/108 = %91 [84–95] |

**Tek senaryo fark.** Aralıklar neredeyse tamamen üst üste. Tool seçimi ekseninde iki model
ayırt edilemiyor.

## Ayrımın beklendiği hücreler de ayırmıyor

Koşudan önce, farkın sağlamlık ve geçmiş kümelerinin **argüman doğruluğunda** çıkması
bekleniyordu (eski koşularda 27B lehine %89'a %62 ve %100'e %71). Fark tekrarlandı, ama
aralıklarıyla birlikte:

| | 27B | 35B |
|---|---|---|
| sağlamlık argüman (CLI) | 8/9 = %89 [56–98] | 5/8 = %62 [31–86] |
| geçmiş argüman (CLI) | 9/9 = %100 [70–100] | 5/7 = %71 [36–92] |

İki karşılaştırmada da aralıklar geniş biçimde çakışıyor. **Yön tutarlı, fark anlamlı
değil.** n=7–9'da başka türlüsü de beklenmezdi.

### Küme küme (CLI, tool doğruluğu)

| küme | 27B | 35B |
|---|---|---|
| altın (50) | %90 [79–96] | %94 [84–98] |
| kontrol (18) | %94 | %94 |
| adım2 (8) | %100 | %100 |
| sağlamlık (10) | %90 | %80 |
| uzun (4) | %100 | %100 |
| geçmiş izli (10) | %90 | %80 |
| geçmiş izsiz (10) | %90 | %80 |

27B üç hücrede önde, üçünde eşit, birinde geride (altın küme). Altın kümedeki fark iki
senaryo; aralıklar orada da çakışıyor.

## Ayırt eden tek eksen: TTFT

27B 0.20 sn, 35B 0.28 sn. Sahip hızın belirleyici olmadığını söyledi, o yüzden bu sayı
kararın yanında duruyor, dayanağı değil. §19.4 hâlâ açık olduğu için bir geçti/kaldı da yok.

## Karar: 35B'de kalındı

Gerekçe **"35B daha iyi" değil** — o da veriyle desteklenmiyor. Gerekçe şu: model
değişikliğinin bir bedeli var (§19.1'in CLI kararı 35B adına verilmiş, `main.py` ve üç
doküman güncellenir, `faz2`/`faz3` karşılaştırmaları başka bir modele kayar) ve bu bedeli
karşılayacak bir kazanç **ölçülemedi**. Değişiklik için kanıt yoksa mevcut karar durur.

## Bu sonucun kendi sınırı — P26 bunu açabilir

**Bu karşılaştırma kör bir sayaç kümesinin üstünde alındı.** Aynı gün ortaya çıktı ki
§17.1'in birinci halüsinasyon sayacı (`uydurulan tool`) yapısal olarak sıfır: gramer tool
adlarını birebir literal alternatif olarak yazıyor, yani defterde olmayan bir ad
üretilemiyor. Her iki koşuda da "sıfır uydurulan tool" yazıyor ve bu **modellerin bir
özelliği değil**.

Daha önemlisi, `issues.md` #3/#5/#6'daki asıl üretim hatası — yapılmamış bir eylemi yaptım
demek ve olmayan kaydın içeriğini uydurmak — **hiçbir kümede ölçülmüyor**. Yani iki model
tam da en çok ayrışabilecekleri eksende karşılaştırılmadı.

`PLAN.md`'nin **P26**'sı bu boşluğu kapatıyor. Koştuğunda model seçimi yeniden açılabilir
ve bu belgedeki "ayırt edilemiyor" sonucu o ölçümle birlikte yeniden okunmalıdır.

## Koşunun eksikleri

`akış kesildi` (`issues.md` #2, sunucu tarafı) birkaç senaryoyu düşürdü ve bunlar hiçbir
doğruluk paydasına girmedi:

- 27B: `tek-02`, `uzn-04`, `gec-01`
- 35B: `uzn-04`, `gec-01`

Etkilenen hücreler `json × uzun` (n=3, ikisinde de) ve `json × geçmiş(izli)` (35B'de n=9).
Havuzlanmış paydalar bu yüzden 110 değil 108–109. Karşılaştırma bundan etkilenmiyor —
düşen senaryolar iki modelde de büyük ölçüde aynı — ama o iki hücre tek başına okunmamalı.
