# Faz 7: Kokoro TTS

2026-08-16. Faz 7'nin üçüncü ve son işi. §19.2'nin **TTS yarısı kapandı**; ses karakteri
(§19.10) legacy'den taşındı ve sahibin dinlemesine bırakıldı.

Kaynak: `mayen-legacy/orchestrator/services/tts.py`. Yapılan iş bir taşıma değil,
uyarlama — legacy'nin üç kararı bu depoda geçerli değildi.

## Legacy'den ayrılan üç yer

**1. Model ayrı süreçte (Kural 2).** Legacy Kokoro'yu orchestrator'ın içine yüklüyordu
(`load_tts_model()`, modül düzeyinde global `_cfg`). Burada model `services/kokoro/`'da,
kendi uv projesi ve kendi `.venv`'i ile yaşıyor; `mayen` tarafında yalnızca
`adapters/kokoro.py` var — torch yok, ses işleme yok. `llama-server` neyse bu da o.
Depo kökündeki `.venv` temiz kaldı: dört kapının hiçbiri torch görmüyor.

**2. Akışlı (§6).** Legacy bütün sesi üretip tek parça WAV döndürüyordu; o arayüz ilk-ses
bütçesini baştan harcar. Uç artık `StreamingResponse` ve adaptör `AsyncGenerator`.

**3. WAV değil ham PCM.** Çerçeve başlığı biçimi zaten taşıyor (§13); ikinci bir kap
gereksiz.

Taşınan şey ffmpeg zinciri oldu, birebir: `aecho=0.8:0.88:40:0.4` (metalik yankı) +
`highpass=400`/`lowpass=3000` (telsiz bandı) + `volume=1.5`. Legacy istek başına bir kez
çağırıyordu; burada ffmpeg **istek boyunca kalıcı bir süreç** ve PCM stdin'e akıtılıyor —
parça parça çağırmak `aecho`'yu her segmentin başında sıfırlar, yani yankı segment
sınırlarında duyulur biçimde kesilirdi.

## Örnekleme hızı: dönüştürme serviste

Kokoro 24 kHz üretir, yerelin biçimi 16 kHz (`client/audio.py`, tek yerde yazılı; mikrofon
da o hızda). Dönüştürme zincirin sonunda ffmpeg'e yaptırıldı (`-ar 16000`). Alternatif —
24 kHz'i çerçeveden istemciye kadar taşımak — `Output.chunk` imzasını ve dört `Output`
uygulamasını değiştirmeyi gerektiriyordu; sahibin kararı ilkiydi. Zincir zaten 3 kHz'in
üstünü kesiyor, yani 24→16 kHz'de kaybedilen bantta ses zaten yok.

**Servisin çıkış hızı bilerek ayarlanabilir değil.** Ayarlanabilir olsaydı servisin
ürettiği hız ile adaptörün bildirdiği hız sessizce ayrışabilirdi; sesteki karşılığı
"asistan tiz konuşuyor" olan, sebebi görünmeyen bir arıza. Bunun yerine `/health` biçimi
de bildiriyor ve adaptör bekleneni doğruluyor — uyuşmazlık sağlıksızlık sayılıyor ve kayda
geçiyor (Kural 13).

## Ölçülmüş kısıt: kart dolu, Kokoro CPU'da

Legacy `device="cuda"` diyordu. İlk çalıştırmada servis açılışta öldü: `llama-server`
kartın 16 GB'ının **15.6'sını** tutuyor ve Kokoro 20 MB ayıramadı. Varsayılan `cpu`'ya
alındı ve gerekçesi `services/kokoro/main.py`'de duruyor.

CPU'da ölçülen (RTX 5070 Ti makinesi, LLM aynı anda yüklü, `bf_emma`, hız 0.85, efektli):

| metin | ilk parça | toplam | üretilen ses |
|---|---|---|---|
| 14 harf | 0.26 s | 0.26 s | 2.29 s |
| 27 harf | 0.33 s | 0.33 s | 2.84 s |
| 57 harf | 0.44 s | 0.44 s | 4.69 s |
| 135 harf | 1.01 s | 1.02 s | 9.19 s |

Yani gerçek zamanın ~9 katı hızda üretiyor; GPU gerekmiyor. Cümle bölücünün alt sınırı
`MIN_CHARS = 24` olduğu için gerçek turda TTS'e giden birim yukarıdaki ikinci satıra
yakın: **ilk ses için ~0.3 s**.

**Bir cümle içinde akış yok, ve bu tablonun görünür bulgusu:** "ilk parça" ile "toplam"
her satırda eşit. Kokoro tek cümleyi tek segment olarak üretiyor, ffmpeg de girdisini
almadan çıkmıyor. Akış makinesinin kazandırdığı şey cümle **içinde** değil, uzun metinde
ve asıl olarak §13'ün cümle cümle çalan kuyruğunda. Bu bir arıza değil ama "akışlı"
kelimesinin ne kadarının bugün gerçek olduğu yazılı olmalı.

§19.4 (gecikme hedefleri) hâlâ açık; yukarıdakiler bir hedefe göre değil, tek başına
okunacak sayılar.

## Kurulum ve çalıştırma

```
uv sync --project services/kokoro                       # torch + kokoro, ayrı ortam
uv run --project services/kokoro python services/kokoro/main.py
```

Model diskte hazırdı (`~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M`); indirilen
tek şey Python bağımlılıkları oldu. `ffmpeg` bir sistem bağımlılığı.

**`baslat` artık TTS servisini de açıyor, `llama-server`'ı hâlâ açmıyor.** İkisi de model
servisi ama ikisi aynı şey değil: LLM ölçüm koşarken elle değiştiriliyor, farklı `-c`/`-ngl`
ile açılıyor ve GPU'yu o tutuyor — `config/mayen.service`'in başındaki gerekçe bu. TTS'in
böyle bir kullanımı yok. Port dinleniyorsa hazır kabul ediliyor; betiğin açtıkları pencere
kapanınca kapanıyor, hazır bulduklarına dokunulmuyor. LLM kapalıysa ölümcül değil, uyarı
yazılıyor. **Sesli GUI de buradan geliyor**: `--tts real` iken pencere `--ses` ile
açılıyor, yani `./baslat` bugün sistemin çalışan hâli — LLM hariç.

`baslat` iki bayrak alıyor: `--stt fake|real`, `--tts fake|real` (varsayılan `fake`/`real`).
Bayrak `MAYEN_STT`/`MAYEN_TTS` olarak dışa aktarılıyor ve kabuk değişkeni
`uv run --env-file .env`'i eziyor, yani bayrak `.env`'den üstün. Doğrulama tek yerde,
`config.py`'de. **`--stt real` bilerek hata veriyor** (çıkış 78): §19.2'nin STT yarısı
açık, seçilecek bir model yok — düğmenin hiç olmaması "STT zaten gerçek" izlenimi
bırakırdı, sessizce sahteye düşmek ise açık maddeyi varsayımla kapatmak olurdu.
`--tts fake`, Kokoro servisi kapalıyken uçtan uca konuşmak için.

Uygulama tarafında yapılandırma tek satır: `MAYEN_TTS_URL`. Ses kimliği, hız, cihaz ve
efekt zinciri **servisin** ortam değişkenleri (`MAYEN_KOKORO_*`), çünkü modeli tanıyan
tarafta durmaları gerekiyor ve uygulama süreci onları hiç görmüyor.

## Pencere ve hoparlör

`client/gui.py` gelen parçayı UTF-8 metin olarak çözüyordu — sahte TTS'in yükü metindi
(P1) ve gerçek TTS'te pencere `[4096 bayt ses]` yazıp susardı. Artık hoparlör isteğe bağlı
bir bağımlılık olarak veriliyor (`--gui --ses`) ve `GuiOutput` onu `VoiceOutput` gibi
kullanıyor; `client/core.py` yine bir satır değişmedi (P17).

**Ve cevabın metni protokole eklendi (`Reply`, protokol sürümü 1 → 2).** Kokoro
bağlanınca ortaya çıkan asıl arıza buydu: istemcilerin hepsi cevabı **ses parçalarını
UTF-8 çözerek** gösteriyordu — sahte TTS'in yükü metindi (P1) ve bunun geçici olduğu
`client/output.py`'de yazılıydı. Gerçek TTS'te o yol kapandı ve kullanıcı kendi sorusunu
görüp cevabı hiç göremez oldu; metin, pencerede de uçbirimde de yoktu.

Metin artık sesin yanında ayrı bir çerçeye: cümle başına bir tane, o cümlenin **sesinden
önce**. `Transcript`'in kullanıcı için yaptığının aynısı, konuşan taraf için — ve §13'e bu
şekilde yazıldı. Sonuç olarak üç istemci de (metin, ses, GUI) cevabı gösteriyor ve
`TextOutput`/`GuiOutput`'taki artımlı UTF-8 çözme kodu silindi.

**Yükün ne olduğu tahmin edilmiyor.** "UTF-8 çözülüyorsa metindir" bir sezgi olurdu ve ham
PCM'in bir kısmı geçerli UTF-8'dir — sesi sohbet dökümüne çöp olarak basardı. Çerçeve
biçimi taşıyor (§13) ama `Output.chunk` onu görmüyor; bayrak, o boşluğun bugünkü dürüst
karşılığı. İleride `Output.chunk`'a biçim eklenirse bayrak gereksizleşir.

## İki kusur: tek bayt ve yutulan istisna

Gerçek turda ses cümlenin ortasında kesildi ve o andan sonra yazılanlar cevapsız kaldı.
İkisi tek bir zincir:

**1. Çerçeve sınırı örnek sınırı değil.** Servis ffmpeg'in çıktısını sabit boyutta okuyor
(`READ_SIZE`); dönen parçanın uzunluğu **tek** olabiliyor ve PCM16'da bir örnek iki bayt.
PortAudio bunu `ValueError: len(data) not divisible by samplesize` ile reddediyor.
`Speaker` artık yarım kalan baytı bir sonraki parçaya taşıyor. Atmak çözüm değildi: kalan
bayt sonraki parçanın ilk baytının yarısı, atılırsa akış bir bayt kayar ve o noktadan
sonraki bütün ses gürültüye döner. `stop()` artığı da atıyor — sonraki cevabın başına
yapışsaydı onu kaydırırdı.

**2. Ve o hata sessizce yutuluyordu (Kural 13).** `Client.run()` yalnızca
`ConnectionClosed` yakalıyordu; başka bir istisna okuma görevini öldürüyor, kimse onu
`await` etmediği için ekrana hiçbir şey düşmüyor ve istemci o andan sonra **sessizce sağır**
kalıyordu. Kullanıcının gördüğü buydu: yazıyor, hiçbir şey olmuyor. Artık çerçeve işleme
hatası bozuk çerçevedeki kararın aynısına tabi — kayda geçiyor, `failed` ile kullanıcıya
söyleniyor, bağlantı düşmüyor. **Asıl arıza tek baytlık olandı; onu bir sürü boyunca
görünmez tutan ikincisiydi.**

Esc (iptal) hoparlörü de kesiyor: tampondaki ses **atılıyor**, çalınıp bitirilmiyor.

## Açık kalanlar

- **§19.15** (Türkçe özel adların İngilizce sesten geçmesi) sahibin kararıyla açık.
  Artık dinlenebilir: `contact_save` ile kaydedilmiş bir Türkçe ad, `bf_emma` ağzından
  nasıl çıkıyor. Ölçülmeden kapatılmayacak.
- **§19.10** (ses karakteri) efektli ve düz iki örnek üretildi, karar sahibin dinlemesine
  bırakıldı. Kod bugün efektli tarafta duruyor.
- **§19.2'nin STT yarısı** hâlâ açık; ses **girişi** hâlâ çalışmıyor. Sistem bugün metinle
  giriyor, sesle çıkıyor.
