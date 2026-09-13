# Faz 2 — model ölçümü (1/3: LLM adayları)

> **Sonradan değişti (P11, P13, P14).** Bu rapor koşulduğu andaki araçla üretildi. O
> zamandan beri: CLI grameri artık argüman değerlerinde `<` kabul etmiyor; §17.1'in
> üçüncü halüsinasyon sayacı ("desteksiz sayı") artık ölçülüyor ve raporun bir sütunu;
> altın kümede `tek-04` liste kodlamasını sınayacak biçimde yeniden yazıldı (küme hâlâ 50
> senaryo). Buradaki sayılar geçerliliğini korur ama yeni bir koşuyla birebir
> karşılaştırılmaz.

Bu doküman Faz 2'nin **ilk üçte biri**: LLM adaylarının VRAM tüketimi ve tool seçim
başarımı. STT/TTS ölçümü, üçlünün birlikte 16 GB'a sığması, §19.4'ün gecikme temel çizgisi
ve C1/§19.15 (Türkçe içerik + İngilizce TTS) henüz **ölçülmedi** ve burada yer almıyor.

Araç `evals/` — P7'de yazılan aynı araç, aynı 50 senaryo, aynı katalog. Model başına
üretilen ham raporlar `docs/faz2/` altında; başarısız senaryoların dökümü orada.

## Koşu koşulları

Tüm adaylar aynı bayraklarla koştu, ölçüm karşılaştırılabilir olsun diye:

```
-ngl 99 -c 49152 --cache-type-k q4_0 --cache-type-v q4_0 --no-mmap
--reasoning off --flash-attn on --parallel 1 --threads 8 --threads-batch 8
--jinja --no-context-shift --batch-size 2048 -n 32768
```

Örnekleme adaptörde kapalı (`temperature 0.0`). VRAM `nvidia-smi` ile, sunucu ayakta ve
model yüklü, henüz istek gelmemişken okundu; KV önbelleği ayrılmış hâldedir. Donanım:
RTX 5070 Ti, 15880 MiB kullanılabilir VRAM.

**Qwen3.6-35B-A3B satırı P7'den devralındı ve diğerleriyle aynı koşulda değil:** o koşu
`--n-cpu-moe 7` ile, yani uzman katmanlarının bir bölümü CPU'da koştu. VRAM'i "bu model
GPU'ya sığıyor" anlamına gelmez, "CPU'ya taşarak 15740 MiB'e sığdırıldı" anlamına gelir;
süreleri de bu yüzden diğerleriyle birebir kıyaslanamaz.

## VRAM ve başarım

| model | VRAM | cli tool | cli argüman | json tool | json argüman | cli tok / sn | json tok / sn |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.6-35B-A3B-IQ4_XS ¹ | 15740 MiB | 94% | 94% | 92% | 94% | 21 / 0.28 | 27 / 0.32 |
| Qwen3.6-27B-IQ4_XS | 15628 MiB | 94% | 94% | 86% | 89% | 21 / 0.64 | 30 / 0.85 |
| gemma-4-12B-it-qat-Q4_K_XL | 7194 MiB | **96%** | 88% | 92% | 94% | 29 / 0.45 | 23 / 0.38 |
| Qwen3.5-9B-Q8_0 | 9084 MiB | 84% | 71% | 92% | 97% | 22 / 0.34 | 26 / 0.39 |
| Qwen3.5-9B-UD-Q4_K_XL | 6186 MiB | 60% | 50% | 84% | 100% | 28 / 0.30 | 31 / 0.33 |

¹ CPU'ya taşarak; yukarıdaki nota bakınız.

Beş modelin onu koşusunun **hiçbirinde uydurulmuş tool ya da uydurulmuş argüman yok.**
Gramer, P7'de olduğu gibi, görevini yapıyor. Düzeltme turu yalnızca üç koşuda ve yalnızca
birer kez tetiklendi (27B × json, 9B-Q8 × json, 9B-Q4 × json).

## Çıkan iki sonuç

**1. §19.1'in kararı gerçekten modele bağlıymış — ve dönüyor.** P7 "karar bir aday modele
dayanıyor, Faz 2'de yeniden ölçülecek" diye yazmıştı; iki gramer üreticisinin de yerinde
bırakılma gerekçesi buydu. Ölçüm o gerekçeyi doğruladı: büyük modellerde (35B-A3B, 27B)
CLI önde, küçük modellerde (9B'nin iki niceliği) JSON açık ara önde — 9B-Q4'te fark
%60'a %84. gemma-12B ise ikisini ayırmıyor: tool seçiminde CLI (%96 / %92), argüman
doğruluğunda JSON (%94 / %88) önde.

**Karar bu koşuyla verilmiyor**, çünkü çağrı biçimi seçimi model üçlüsü seçilmeden
anlamsız: hangi biçimin kazandığı seçilen modele bağlı ve model seçimi STT/TTS ölçümünü
bekliyor. §8.3'ün adaptörü ve iki gramer üreticisi bu yüzden hâlâ yerinde duruyor.

**2. Bir aday tek başına bütçeyi bitiriyor, biri fazlasıyla yer bırakıyor.** 16 GB
bütçenin dört model süreci arasında paylaşılması gerekiyor (§2, §3 — LLM, STT, TTS GPU'da;
konuşmacı tanıma CPU'da). 27B tek başına 15628 MiB alıyor, yani STT ve TTS'e yer
kalmıyor; 35B-A3B ancak CPU'ya taşarak sığıyor. gemma-12B 7194 MiB ile en yüksek tool
seçim doğruluğunu veriyor ve geriye ~8,5 GB bırakıyor. **Bu bir seçim değil, bir gözlem:**
seçim STT/TTS ölçüldükten sonra, üçlü olarak yapılacak.

## Ölçüm sırasında çıkan iki bulgu

**CLI grameri, değerin içine çağrı önekini almasını engellemiyor.** gemma × cli'de iki
senaryo şu biçimde bozuldu:

```
<tool> contact_get --name Ali<tool> <tool> note_createon_body Ali'yi akşam arayacağım.
```

Model ikinci bir çağrı üretmeye kalkıyor, `cli-word` `<` karakterini kabul ettiği ve
CLI satırının sonlandırıcısı olmadığı için ikinci çağrı birincinin **argümanının içine**
yazılıyor ve ortaya sözdizimsel olarak geçerli, anlamsal olarak yanlış tek bir çağrı
çıkıyor. JSON dalında bu mümkün değil: kapanan süslü parantez üretimi bitiriyor.
`cli-word`'ün `--` ile başlayamaması gibi `<` de yasaklanabilir; ama bu, ölçülmekte olan
iki adaydan birini ölçüm ortasında değiştirmek demek — **karar sahibinin.** Aynı koşuda
`cli-integer ::= [0-9]+`'ın üst sınırsız olması da bir kez kaçak üretime yol açtı
(`--day 4111…111`); bu iki biçimde de aynı, JSON'da da sınır yok.

**`LlamaCppLLM` bir kez `httpx.ReadError` ile düştü.** İlk 9B koşusu `/tokenize`
çağrısında koptu, aynı koşu birebir tekrar edildiğinde sorunsuz geçti; beş modelin
sonraki dokuz koşusunda bir daha görülmedi. Beş kez akış + `count_tokens` ile
tekrarlanabilir bir repro tutturulamadı; havuzdan gelen bayat bağlantı gibi görünüyor.
Ölçüm aracında bu bir yeniden koşu demek, gerçek tur akışında ise turu öldüren aralıklı
bir hata — kaydedildi, henüz düzeltilmedi.

## Bundan sonrası (Faz 2'nin kalanı)

- STT adaylarının (faster-whisper large-v3 / large-v3-turbo / small) VRAM'i ve Türkçe
  doğruluğu.
- TTS (Kokoro-82M) VRAM'i ve §19.10'un ses karakteri.
- Üçlünün birlikte 16 GB'a sığdığının ölçülmesi; ardından model seçimi ve §19.1'in
  seçilen model üzerinde nihai kararı.
- §19.4: gecikme temel çizgisi ve regresyon testi eşiği.
- C1/§19.15: Türkçe özel adların İngilizce TTS'ten geçmesi.
