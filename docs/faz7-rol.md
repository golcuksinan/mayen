# Faz 7: Edden kişiliği ve İngilizce çıkış

2026-08-16. Sahibin kararıyla üç iş sıraya kondu: rol metnine bir oyun karakteri kişiliği
(Ixion'dan **Edden**, Tiqqun'un Personal Assistant'ı), §2'nin "çıkış İngilizce" kararının
uygulanması, ve Kokoro TTS. İlk ikisi burada; ölçümler `faz7-edden-27b.md`,
`faz7-edden-27b-tur2.md`, `faz7-edden-27b-tur3.md` ve `faz7-dil-kurali.md`.

Hepsi **27B dense** (`Qwen3.8-27B-IQ4_XS`) üzerinde, **üretim öneğiyle**, dört küme (altın,
kontrol, halüsinasyon, bellek) × iki çağrı biçimi. **35B'de koşulmadı** — CLAUDE.md'nin
kuralı bunu istiyor (bir rol metni sonucu yalnızca koştuğu modelde geçerli) ve sahip
benimsemeyi 35B'yi beklemeden seçti. Bu bir bilinen açık, gizli bir varsayım değil.

## Asıl bulgu: kuralın metni değil, yeri

§2'nin "çıkış İngilizce" kararı **rol metnine yazıldığında tutmuyor.** Üç turda denendi:

| tur | dil kuralı nasıl yazıldı | `kontrol` kümesinde İngilizce yanıt |
|---|---|---|
| 1 | Türkçe cümle + `"Administrator" de` | 18'de ~5 |
| 2 | kuralın kendisi İngilizce yazıldı, hitap satırı çıkarıldı | 18'de 1 |
| 3 | tur 2 + hitap satırı geri | 18'de ~2, yalnızca en kısa selamlamalar |

Türkçe kullanıcı girdisi, Türkçe geçmiş ve Türkçe katalog, öneğin **başındaki** tek bir
yönergeden ağır basıyor. Kuralın kendi dilini İngilizce yapmak yardım etmedi; işe yarayan
tek şey `Administrator` çıpasıydı ve o da **kelimeyi** çekti, dili değil.

Denenmemiş tek kaldıraç konumdu, ve iki konum denendi. Kural **sistem promptunun sonuna,
katalogdan sonra** konunca `kontrol` kümesinin **18/18'i** İngilizce çıktı, Edden tonu
korunmuş hâlde. Aynı cümle, rol metninin başında %10, sabit öneğin sonunda %100.

`agent/prompt.py`'de `system_prompt(language_rule=…)`, `MAYEN_LANGUAGE_RULE_PATH` ile
`config/dil-en.txt`'den. Kural 3 bozulmuyor: kural süreç boyunca sabit, yani sistem promptu
da sabit kalıyor.

**Kural iki yerde birden duruyor** — `config/rol.txt`'nin ikinci paragrafında ve
`config/dil-en.txt`'de. Tekilleştirilmedi, çünkü **ölçülen yapılandırma bu**. Birini silmek
ölçülmemiş bir değişiklik olur ve tam olarak konumun belirleyici olduğu bir eksende yapılır.

## İkinci bulgu: "gemi bilgisayarı gibi konuş" modeli üçüncü şahsa itiyor

Tur 1'de model kendi **rol metnini** ve JSON **şema anahtarlarını** (`name`, `arguments`)
cevabın içine tırnaklayarak sızdırdı; `desteksiz alıntı` sayacı yakaladı (`bel-04`,
`kon-18`, `bel-05`). Kişiliği "durumu bildirir" diye yazmak, modeli yöneticiye değil
yönetici **hakkında** konuşmaya itiyordu — `Kullanıcının konumu hakkında güncel bilgiye
sahip değilim` gibi cevaplar. Çözüm yasak değil, ilkeydi:

> You speak to the Administrator, not about them. Say "your class is at ten", never "the
> user's class is at ten". Write only what you say out loud — your own reasoning is not
> part of the answer.

Sayaç bundan sonra bütün kollarda sıfır.

## Sayılar (27B, üretim öneği)

Karşılaştırma tabanı 2026-08-15'te benimsenen metin.

Son sütun **benimsenen** yapılandırma: Edden metni + dil kuralı sistem promptunun sonunda.

| küme | önceki metin | Edden (tur 3) | Edden + dil kuralı (benimsenen) |
|---|---|---|---|
| altın (cli/json) | 100 / 96 | 100 / 100 | 98 / 98 |
| kontrol | 100 / 100 | 100 / 100 | 100 / 100 |
| halüsinasyon (cli/json) | 93 / 100 | 100 / 93 | 93 / 93 |
| bellek (cli/json) | 94 / 94 | 82 / 88 | 82 / 82 |

Aralıklar çakışıyor ve yön tutarsız; **bunlar sıralama değil.** Tutarlı olan tek şey
`bellek` kümesindeki kayıp: dört ölçümün dördünde de tabanın altında. CLAUDE.md'nin kabul
ettiği takas bu — gereksiz çağrı gecikmedir, "evet, kurdum" `issues.md`'dir.

## Üçüncü bulgu: değişkenin arkasına konan sabit de önbelleği düşürüyor

Kural **önce** öneğin en sonuna, kullanıcı mesajından sonra ayrı bir `[dil]` mesajı olarak
konmuştu (`faz7-dil-kurali.md`). Dil tuttu ama TTFT 0.24'ten **1.04'e** çıktı — her kümede,
her biçimde. Sıra ve önbellek ısınması elendi: aynı kural üçüncü bir kol olarak tekrar
koşuldu, 1.06.

Sebep `llama-server`'ın kendi `timings` alanından okundu, senaryo başına işlenen prompt
jetonu:

- kuralsız: `1560, 23, 20, 26, 22, 21, 25, 21` — ilk istek soğuk, sonrası önbellekten
- kural sonda: `80, 1633, 1630, 1636, 1632, …` — **her istek öneğin tamamını yeniden işliyor**

Yani maliyet üretim değil **prefill**. Kuralı kullanıcı mesajından sonraya koymak, değişken
içeriği öneğin sonundan ortasına taşıyor ve ortak önek eşleşmesi çöküyor. §8.1'in
"değişken içerik daima en sona" kuralının koruduğu şey tam olarak bu, ve kuralın **sabit**
olması muafiyet vermiyor: değişkenin arkasında durması yetiyor.

Kural sabit öneğin sonuna taşınınca bedel kayboldu (`faz7-dil-sistem-sonu.md`):

| | dil | altın (cli/json) | TTFT (altın) |
|---|---|---|---|
| kuralsız | Türkçe | 100 / 100 | 0.22 / 0.24 |
| kural kullanıcıdan sonra | **İngilizce** | 96 / 94 | **1.05 / 1.03** |
| kural sistem promptunun sonunda | **İngilizce** | 98 / 98 | **0.24 / 0.26** |

İkinci konum her eksende üçüncüsünden kötü; seçilen üçüncüsü.

## Yerini alan metin (2026-08-15'te benimsenmişti)

Verbatim, `faz6-27b-rol3.md`'nin kazananı:

```
Sen Mayen'sin: tek bir makinede çalışan, kendi verisine sahip bir sesli asistansın.
Kullanıcı seninle Türkçe konuşur. Yanıtların sesli okunacak; kısa ve konuşma dilinde yaz,
madde işareti ve biçimlendirme kullanma.

İki tür bilgi arasında ayrım yap. Konuşmada söylenenler iddiadır: kullanıcının ya da senin
daha önce söylediğin bir şey, o işin yapıldığı ya da o kaydın var olduğu anlamına gelmez.
Bir tool çağırıp sonucunu gördüğünde ise bilirsin. Kayıtlara dair her soruda, cevabı
konuşmadan hatırlıyor olsan bile tool çağır; hatırladığın şey kaydın kendisi değil, ondan
söz edilmiş olmasıdır.

Ama çağırmadan önce her seferinde şuna bak: o tool'un zorunlu alanları için gereken bilgi
konuşmada geçiyor mu. Geçmiyorsa çağırma ve değer uydurma; eksik olanı kullanıcıya sor.
Bu, yukarıdaki kuraldan önce gelir — eksik bilgiyle çağırmaktansa sormak doğrudur.

Buna karşılık, kullanıcının sana o an söylediği bir şeyi tekrar sormak için tool çağırma.
Sohbetin kendisi hakkındaki sorulara doğrudan cevap ver.

Sonucu gördüğünde yalnızca sonucun söylediğini aktar; eksikse eksik olduğunu söyle.
İzin gerektiren bir iş varsa onu da tool çağırarak yap; izni sistem soracak.
```

Edden metni bu paragrafların **dördünü de değiştirmeden** koruyor; eklenen şey kimlik, dil
ve ses. Üç ölçülü turla kazanılmış davranışa dokunulmadı.
