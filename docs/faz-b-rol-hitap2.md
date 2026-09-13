# Çağrı biçimi ve tool modu ölçümü

Düzeltme turu tavanı: 2. Karşılaştırma birebir; tek istisna, cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.

Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**. Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).

## Sunucu ayarları

Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.

- model: `/home/amnesia/Projects/mayen-legacy/inference/models/Qwen3.8-27B-IQ4_XS.gguf` (IQ4_XS - 4.25 bpw)
- `n_ctx`: 16384

| örnekleme | sunucu (`/props`) | istek (adaptör) |
|---|---:|---:|
| `dry_multiplier` | 0.0 | 0.0 |
| `frequency_penalty` | 0.0 | 0.0 |
| `min_p` | 0.0 | 0.0 |
| `mirostat` | 0 | 0 |
| `presence_penalty` | 1.5 | 0.0 **←** |
| `repeat_penalty` | 1.0 | 1.0 |
| `temperature` | 0.699999988079071 | 0.0 **←** |
| `top_k` | 20 | 0 **←** |
| `top_n_sigma` | -1.0 | -1.0 |
| `top_p` | 0.800000011920929 | 1.0 **←** |
| `typical_p` | 1.0 | 1.0 |
| `xtc_probability` | 0.0 | 0.0 |

Sağ sütun her istekte gönderiliyor ve solu **ezer**; `←` işaretli satırlar sunucunun bayrağının artık okunmadığı yerler. Sunucudan gelen tek şey `n_ctx`.


## Önek

Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi** olduğu sonucu değiştirir (P27):

- **ölçüm öneği** — `docs/faz2-olcum.md`'den beri kullanılan dizi: çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]` bloğu ve olgular **yok**.
- **üretim öneği** — `turn/runner.py`'nin modele gerçekten gönderdiği dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.

Rol metni: `/tmp/claude-1000/-home-amnesia-Projects-mayen/0eef584b-6af7-4939-aa2a-29b9840ea0e2/scratchpad/rol-eski.txt`, `config/rol.txt` — **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`), o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı kolon ve etikette `rol(ad)` diye yazılı.

## Toplam

**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26).

| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) | uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) | desteksiz sayı (n) | desteksiz alıntı | düzeltme turu | ort. token | ort. TTFT | ort. sn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(yok) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 34 | 0.21 | 0.70 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 23 | 0.19 | 0.52 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(yok) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 24 | 0.20 | 0.53 |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(dil-en) | 18 | 89% [67%–97%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 21 | 0.20 | 0.48 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(yok) | 50 | 98% [90%–100%] | 82% | — | 0 | 0 | 0 (5) | 0 | 0 | 16 | 0.26 | 0.49 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(dil-en) | 50 | 96% [87%–99%] | 88% | — | 0 | 0 | 1 (5) | 0 | 0 | 14 | 0.27 | 0.45 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(yok) | 50 | 96% [87%–99%] | 88% | — | 0 | 0 | 0 (5) | 0 | 0 | 16 | 0.26 | 0.48 |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(dil-en) | 50 | 98% [90%–100%] | 89% | — | 0 | 0 | 2 (5) | 0 | 0 | 12 | 0.26 | 0.42 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(yok) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 28 | 0.19 | 0.60 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 26 | 0.19 | 0.54 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(yok) | 18 | 94% [74%–99%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 25 | 0.19 | 0.56 |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(dil-en) | 18 | 89% [67%–97%] | — | — | 0 | 0 | 0 (0) | 0 | 0 | 22 | 0.19 | 0.49 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(yok) | 50 | 98% [90%–100%] | 91% | — | 0 | 0 | 0 (5) | 0 | 0 | 24 | 0.26 | 0.56 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(dil-en) | 50 | 96% [87%–99%] | 91% | — | 0 | 0 | 2 (5) | 0 | 0 | 21 | 0.26 | 0.51 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(yok) | 50 | 98% [90%–100%] | 91% | — | 0 | 0 | 0 (5) | 0 | 0 | 21 | 0.26 | 0.52 |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(dil-en) | 50 | 98% [90%–100%] | 91% | — | 0 | 0 | 1 (5) | 0 | 0 | 19 | 0.26 | 0.50 |

## Eksen kırılımı (tool doğruluğu)

| koşu | tek tool | çok tool | eksik argüman | tool gerekmez | ayırt etme | serbest metin |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(yok) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(yok) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(dil-en) | — | — | — | 89% | — | — |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(yok) | 100% | 83% | 100% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(dil-en) | 100% | 100% | 86% | 100% | 88% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(yok) | 100% | 83% | 100% | 100% | 88% | 100% |
| Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(dil-en) | 100% | 100% | 86% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(yok) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(yok) | — | — | — | 94% | — | — |
| Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(dil-en) | — | — | — | 89% | — | — |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(yok) | 100% | 100% | 100% | 100% | 88% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(dil-en) | 100% | 100% | 71% | 100% | 100% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(yok) | 100% | 100% | 100% | 100% | 88% | 100% |
| Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(dil-en) | 100% | 100% | 86% | 100% | 100% | 100% |

## Sayacın kapsamı

§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi halüsinasyonunu ölçüme karıştırırdı.

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(dil-en)** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `It is 09:00 UTC on Sunday, 9 August 2026.`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(dil-en)** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `It is 09:00 UTC on Sunday, 9 August 2026.`
- `tek-05`: `29` — yanıt: `Memory is at 9.4 of 32 gigabytes, roughly 29 percent used. CPU is at 12 percent. No issues.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(dil-en)** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `It is 09:00 UTC on Sunday, 9 August 2026.`
- `tek-05`: `29` — yanıt: `Administrator, memory is at 9.4 gigabytes used out of 32. That is 29 percent. CPU is at 12 percent.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(dil-en)** — desteksiz sayı geçen senaryolar:

- `tek-01`: `9` — yanıt: `It is 09:00 UTC on Sunday, 9 August 2026.`

## Mekanik olarak yargılanmadı

Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası. Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan okunuyor.

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(yok)** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, Administrator.`
- `kon-04`: `Anlaşıldı.`
- `kon-05`: `Anladım. Dün akşamın güzel geçtiğini not etmemi ister misin?`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler. Bellek, aktif verileri tutar. Depolama`
- `kon-07`: `Anlıyorum. Ne karışık? Bir şeyi netleştirmemi ister misin, yoksa sadece bir şeyi hatırlatmamı mı?`
- `kon-09`: `Evet, Administrator. Bir şehir adı verin, o şehrin güncel hava durumunu alayım.`
- `kon-10`: `Hatırlatıcı kurduğumda, makinede bekleyen zamanlanmış görevler listesine yeni bir kayıt eklenir. Kayıt, senin verdiğin metni ve tetiklenme zamanını içerir. Sistem, o zaman geldiğinde kaydı okur ve met`
- `kon-11`: `Administrator, notlar bu makinede saklanıyor ve yalnızca senin erişiminle okunuyor. Dışarıya gönderilmiyor, başka bir kullanıcıya açılmıyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. Her kayıt bir isim ve isteğe bağlı bir telefon numarası içerir. İsim verdiğimde o kaydı bulur, yeni bir kişi ekler, mevcut birini`
- `kon-13`: `Anlaşıldı, Administrator.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Yarın için hava durumunu kontrol edeyim. Hangi şehirde olacağınızı söylemediniz; varsayılan olarak bulunduğunuz konumu mu kullanayım, yoksa belirli bir şehir mi belirtmek istersiniz?`
- `kon-16`: `Not aldım. Ali ile dün görüşmüşsün, durumu iyiydi.`
- `kon-17`: `Anlıyorum. Zaman algısı kişisel bir deneyimdir; benim için yalnızca saat işler. Başka bir isteğiniz var mı?`
- `kon-18`: `Anlıyorum. Bugün ders programını kontrol edeyim, belki bir şey erteleyebiliriz.  <tool> course_schedule --day 1`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en)** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Understood, Administrator.`
- `kon-03`: `Understood, Administrator.`
- `kon-04`: `Understood, Administrator.`
- `kon-05`: `Noted.`
- `kon-06`: `Computers operate by executing instructions stored in memory. The central processing unit fetches each instruction, decodes it, and performs the required operation, whether arithmetic, data movement, `
- `kon-07`: `Understood, Administrator. I am here.`
- `kon-09`: `Yes, I can check the weather for a city. Tell me which city you want and I will query it.`
- `kon-10`: `When you set a reminder, I create a scheduled task with a specific due time and a message. At that time, the system triggers the task and reads the message to you. The task remains in the pending list`
- `kon-11`: `Yes. Your notes are stored on this machine, on your data. No other user or external service has access to them. I can read and write them only when you ask me to.`
- `kon-12`: `The contact book is a local directory on this machine. It stores names and, optionally, phone numbers for people you have added. I can list the entries, search for a specific name, add a new person, u`
- `kon-13`: `Understood, Administrator. No reminder has been set.`
- `kon-14`: `Understood, Administrator.`
- `kon-15`: `I will check the weather for tomorrow. Which city should I look up?`
- `kon-16`: `Noted. No action required.`
- `kon-17`: `I understand. Time perception can vary. Is there a specific task or reminder you would like to set for today?`
- `kon-18`: `I understand. I can check your schedule for today to see what is planned, or I can set a reminder for a specific study session if you decide to start. Let me know how you would like to proceed.`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(yok)** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı.`
- `kon-04`: `Anlaşıldı.`
- `kon-05`: `Anladım.`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler. Bellek, aktif verileri tutar. Depolama`
- `kon-07`: `Anlıyorum. Ne karışık?`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu sorgulayabilirim.`
- `kon-10`: `Hatırlatıcı kurduğumda, makinede bekleyen zamanlanmış görevler listesine yeni bir kayıt eklenir. Kayıt, senin verdiğin metni ve tetikleneceği zamanı içerir. Sistem o an geldiğinde, kayıtlı metni sana `
- `kon-11`: `Notlar bu makinede, senin verin olarak saklanıyor. Dışarıya gönderilmiyor, başka bir kullanıcı ya da servis erişiminde bulunmuyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının bütünüdür. Her kayıt bir kişi adı ve isteğe bağlı bir telefon numarası içerir. Rehberdeki kişileri listeleyebilir, yeni kişi ekleyebilir, var`
- `kon-13`: `Anlaşıldı.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Yarın için hava durumunu kontrol edeyim.`
- `kon-16`: `Not aldım.`
- `kon-17`: `Anlıyorum.`
- `kon-18`: `Anlıyorum. Bugün ders programını kontrol edeyim, belki bir şey erteleyebiliriz.`

**Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(dil-en)** — 16 yanıt:

- `kon-01`: `Good evening.`
- `kon-02`: `Understood.`
- `kon-04`: `You are welcome.`
- `kon-05`: `Noted.`
- `kon-06`: `Computers operate by executing instructions stored in memory. The central processing unit fetches these instructions, decodes them, and performs arithmetic or logical operations on data. Results are w`
- `kon-07`: `I am here. What is on your mind?`
- `kon-09`: `Yes, I can check the weather for a city. Tell me which city you want.`
- `kon-10`: `When you set a reminder, I create a scheduled task with a specific due time and a message. At that time, the system triggers the task and reads the message to you. The task remains in the pending list`
- `kon-11`: `Administrator, your notes are stored on this machine. I have no record of any external sync, backup, or access log. I cannot confirm who else has physical or network access to the hardware.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. Her kayıt bir kişi adı ve isteğe bağlı bir telefon numarası içerir. İsimle arama yapabilir, yeni kişi ekleyebilir, mevcut birinin`
- `kon-13`: `Understood.`
- `kon-14`: `Understood.`
- `kon-15`: `I can check tomorrow's weather for a specific city. Which city should I look up?`
- `kon-16`: `Noted.`
- `kon-17`: `Time moves at a constant rate. The perception of speed varies with attention and routine.`
- `kon-18`: `I understand. If you want, I can check your schedule for today to see what is coming up.`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(yok)** — 16 yanıt:

- `cok-06`: `Veli'nin telefon numarası konuşmada geçmiyor. Rehbere eklemek için numarası gerekli. Numarası ne?`
- `eks-01`: `Hangi şehir için hava durumunu istiyorsunuz, Administrator?`
- `eks-02`: `Hangi notu silmemi istiyorsunuz? Notun numarasını ya da içinde geçen bir metni söyleyin.`
- `eks-03`: `Uyandırılacak cihazın adını söyle, Administrator.`
- `eks-04`: `Hatırlatıcı için iki bilgiye ihtiyacım var: ne zaman tetikleneceği ve neyi hatırlatmam gerektiği. Bu ikisini verin, görevi oluşturayım.`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini söyle, Administrator. Numarasını ya da içeriğini verirsen o görevi bulup iptal ederim.`
- `eks-06`: `Silmek istediğiniz kişinin adını söyleyin, Administrator.`
- `eks-07`: `Kişinin adını söyle, Administrator. Telefon numarası da varsa onu da ver.`
- `yok-01`: `Rica ederim, Administrator.`
- `yok-02`: `Administrator, sistem durumu normal. CPU, bellek ve disk kullanımı nominal sınırlar içinde. Hava durumu, ders programı ve bekleyen görevler için talimat bekliyorum.`
- `yok-03`: `I do not tell jokes, Administrator. My function is to manage your data, schedule, and system. If you have a task, a note to save, or a question about your records, I am ready.`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Ben Mayen. Senin kişisel asistan yapay zekânım.  Yapabileceklerim: - Notları yönetmek - Ders programını kontrol etmek - Görevler ve hatırlatmalar oluşturmak - Rehberdeki kişileri yönetmek - Hava durum`
- `yok-07`: `Dört eder.`
- `yok-08`: `I do not control speech rate. That setting lives in your text-to-speech configuration, not in my output. Adjust the playback speed in your TTS app.`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(dil-en)** — 15 yanıt:

- `eks-02`: `Which note do you want deleted, Administrator? Give me the note number or the text it contains.`
- `eks-03`: `Which device should I wake? I need the name of the device as it appears in the configuration.`
- `eks-04`: `I need two things to set that reminder: what time it should fire, and what the reminder message should say. Give me both and I will create it.`
- `eks-05`: `I need the task number to cancel it. Which reminder do you want to remove?`
- `eks-06`: `I need the name of the contact to delete. Which contact should I remove from the directory?`
- `eks-07`: `I need the person's name to add them to the contacts. What is the name?`
- `yok-01`: `You are welcome, Administrator.`
- `yok-02`: `I am operational. How can I assist you, Administrator?`
- `yok-03`: `I do not tell jokes, Administrator. My function is to manage your data, schedule, and system. If you have a task, a note to save, or a question about your records, I am ready.`
- `yok-04`: `The capital of France is Paris.`
- `yok-05`: `Understood, Administrator.`
- `yok-06`: `I am Sen Mayen, your personal assistant. I run on a single machine and manage your data. I can handle contacts, notes, course schedules, timed tasks, weather, system metrics, persistent facts, and bas`
- `yok-07`: `Four, Administrator.`
- `yok-08`: `I cannot adjust my speech rate. I am a text-based system. My responses are generated as text for you to read.`
- `ayr-07`: `I will remove Ali from the contacts.`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(yok)** — 17 yanıt:

- `cok-06`: `Veli'nin telefon numarası konuşmada geçmiyor. Rehbere eklemek için numarası gerekli; hatırlatma içinse aramanın ne zaman yapılacağı. İki bilgiyi de ver.`
- `eks-01`: `Hangi şehir için?`
- `eks-02`: `Hangi notu silmemi istiyorsun? Notun numarasını ya da içinde geçen bir metni söyle.`
- `eks-03`: `Uyandırılacak cihazın adı nedir?`
- `eks-04`: `Hatırlatıcı için iki bilgiye ihtiyacım var: ne zaman tetikleneceği ve neyi hatırlatmam gerektiği.`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini söyle.`
- `eks-06`: `Silmek istediğiniz kişinin adını söyleyin.`
- `eks-07`: `Kişinin adını söyle, ekle.`
- `yok-01`: `Rica ederim.`
- `yok-02`: `Administrator, sistem durumu normal. Size nasıl yardımcı olabilirim?`
- `yok-03`: `Şaka anlatmam.`
- `yok-04`: `Paris.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Sen Mayen'sin. Administrator'ın kişisel asistanı olarak bu makinede çalışıyorsun.  Yapabileceklerin: - Tarih ve saat sorgulama - Rehber yönetimi (kişi ekleme, arama, silme) - Not alma ve arama - Ders `
- `yok-07`: `Dört eder.`
- `yok-08`: `Anladım.`
- `ayr-03`: `Telefon numarası vermedin. Ayşe'nin numarası ne?`

**Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(dil-en)** — 14 yanıt:

- `eks-02`: `Which note do you want deleted? I need its number.`
- `eks-03`: `Which device should I wake?`
- `eks-04`: `I need two things to set a reminder: what time it should fire, and what the reminder message should say. Give me both and I will create it.`
- `eks-05`: `I need the task number to cancel it. Which one?`
- `eks-06`: `I need the name of the contact to delete. Which one?`
- `eks-07`: `I need the person's name to add them to the contacts. What is the name?`
- `yok-01`: `You are welcome.`
- `yok-02`: `I am operational. How can I assist you?`
- `yok-03`: `I do not tell jokes. I report data.`
- `yok-04`: `Paris.`
- `yok-05`: `Understood.`
- `yok-06`: `I am Mayen, your personal assistant. I manage your contacts, notes, and course schedule. I can set timed reminders, check the weather, monitor system metrics, and control media, windows, and applicati`
- `yok-07`: `Four.`
- `yok-08`: `I cannot adjust my speech rate. I am a text-based system.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(yok)** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Anlaşıldı, Administrator.`
- `kon-04`: `Anlaşıldı.`
- `kon-05`: `Administrator, dün akşamla ilgili bir kayıt ya da not yok. Ne olduğunu söylerseniz not alabilirim.`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler. Bellek, aktif verileri tutar. Depolama`
- `kon-07`: `Anlıyorum. Ne karışık?`
- `kon-09`: `Evet, Administrator. Bir şehir adı verin, o şehrin güncel hava durumunu alayım.`
- `kon-10`: `Hatırlatıcı kurduğumda, makinede zamanlanmış bir görev oluşturulur. Görev, belirttiğiniz saatte tetiklenir ve o anda size tanımladığınız mesajı sesli olarak okurum. Görev, zamanı gelene kadar bekleyen`
- `kon-11`: `Administrator, notlar bu makinede saklanıyor ve yalnızca senin erişiminle okunuyor. Dışarıya gönderilmiyor, başka bir kullanıcı ya da hesap tarafından görüntülenemiyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. Her kayıt bir isim ve isteğe bağlı bir telefon numarası içerir. İsim vererek belirli bir kişiyi süzebilir, yeni kişi ekleyebilir,`
- `kon-13`: `Anlaşıldı, Administrator. Hatırlatıcı için bir işlem yapmıyorum.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Administrator, yarınki hava durumu için şehir belirtmediniz. Hangi şehrin hava durumuna bakmamı istersiniz?`
- `kon-16`: `Not aldım. Ali ile dün görüşmüşsün ve durumu iyiydi.`
- `kon-17`: `Administrator, şu anki yerel saat 09:00.`
- `kon-18`: `Anlıyorum. Bugün ders programını kontrol edeyim, belki bir şey erteleyebiliriz.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en)** — 17 yanıt:

- `kon-01`: `Good evening, Administrator.`
- `kon-02`: `Understood, Administrator.`
- `kon-03`: `Understood, Administrator.`
- `kon-04`: `Understood, Administrator.`
- `kon-05`: `Noted.`
- `kon-06`: `Computers operate by executing instructions stored in memory. The central processing unit fetches these instructions, decodes them, and performs arithmetic or logical operations on data. Input devices`
- `kon-07`: `I am here. What is on your mind, Administrator?`
- `kon-09`: `Yes, I can check the weather for a city. Tell me which city you want and I will call the weather tool.`
- `kon-10`: `When you set a reminder, I create a scheduled task with a specific due time and a message. At that time, the system triggers the task and reads the message to you. The task remains in the pending list`
- `kon-11`: `Administrator, your notes are stored on this machine. I have no record of any external sync, backup, or access log. I cannot confirm who else has physical or network access to this hardware. I can onl`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. Her kayıt bir isim ve isteğe bağlı bir telefon numarası içerir. İsimle arama yapabilir, yeni kişi ekleyebilir, mevcut birinin num`
- `kon-13`: `Understood, Administrator. No reminder has been set.`
- `kon-14`: `Understood, Administrator.`
- `kon-15`: `I have noted the plan. To confirm the condition, I will check the weather forecast for tomorrow. However, the weather tool only provides current conditions, not forecasts. I cannot verify tomorrow's w`
- `kon-16`: `Noted. No action taken.`
- `kon-17`: `I understand. I can check the current time if you need the exact time.`
- `kon-18`: `I understand. I can check your schedule for today to see what is planned, or I can set a reminder to help you start. What would you prefer?`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(yok)** — 17 yanıt:

- `kon-01`: `Saat dokuz, Administrator. Geceler gündüzden önce gelmez.`
- `kon-02`: `Anlaşıldı.`
- `kon-03`: `Bekliyorum.`
- `kon-04`: `Buyurun.`
- `kon-05`: `Administrator, dün akşamla ilgili bir kayıt ya da not yok. Olayı hatırlamam için bir not ya da olgu kaydı gerekir.`
- `kon-06`: `Bilgisayarlar, elektrik sinyallerini işleyerek çalışan makinelerdir. Temel parçaları işlemci, bellek ve depolama birimleridir. İşlemci, verileri adım adım işler. Bellek, aktif verileri tutar. Depolama`
- `kon-07`: `Anlıyorum.`
- `kon-09`: `Evet, bir şehir adı verirsen güncel hava durumunu alabilirim.`
- `kon-10`: `Hatırlatıcı kurduğumda, makinede zamanlanmış bir görev oluşturulur. Belirlediğin saat geldiğinde, sana yazdığım metni sesli olarak okurum. Görev, o anı bekler; iptal etmediğin sürece listede kalır.`
- `kon-11`: `Administrator, notlar bu makinede saklanıyor ve erişim yalnızca seninle sınırlı. Dışarıya gönderilmiyor, başka bir kullanıcı ya da hesap tarafından okunmuyor.`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının bütünüdür. Her kayıt bir kişi adı ve isteğe bağlı bir telefon numarası içerir. Rehberdeki kişileri listeleyebilir, yeni kişi ekleyebilir, var`
- `kon-13`: `Anlaşıldı.`
- `kon-14`: `Anlaşıldı.`
- `kon-15`: `Yarın için hava durumunu kontrol edeyim.`
- `kon-16`: `Not aldım.`
- `kon-17`: `Administrator, saat 09:00.`
- `kon-18`: `Anlıyorum. Bugün ders programını kontrol edeyim, belki bir şey erteleyebiliriz.`

**Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(dil-en)** — 16 yanıt:

- `kon-01`: `Good evening.`
- `kon-02`: `Understood.`
- `kon-04`: `You're welcome.`
- `kon-05`: `Not aldım.`
- `kon-06`: `Computers operate by executing instructions stored in memory. The central processing unit fetches these instructions, decodes them, and performs arithmetic or logical operations on data. Input devices`
- `kon-07`: `I am here. What is on your mind?`
- `kon-09`: `Yes, I can check the weather for a city.`
- `kon-10`: `When you set a reminder, I create a scheduled task with a specific due time and a message. At that time, the system reads the message to you. The task remains in the pending list until it triggers or `
- `kon-11`: `Administrator, notes are stored on this machine. I have no record of any external sync or remote access. I cannot confirm the state of the operating system or network configuration from here. If you n`
- `kon-12`: `Rehber, bu makinede saklanan kişisel iletişim kayıtlarının listesidir. İçinde kişi adları ve varsa telefon numaraları bulunur. İstediğinde kişileri listeleyebilir, yeni kişi ekleyebilir, mevcut birini`
- `kon-13`: `Understood.`
- `kon-14`: `Understood.`
- `kon-15`: `I can check tomorrow's weather for a specific city. Which city should I look up?`
- `kon-16`: `Noted.`
- `kon-17`: `Time moves at a constant rate. It does not speed up.`
- `kon-18`: `I understand. If you want, I can check your schedule for today to see what is planned.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(yok)** — 16 yanıt:

- `eks-01`: `Hangi şehir için hava durumunu istiyorsunuz, Administrator?`
- `eks-02`: `Silmek istediğiniz notun numarasını söyleyin.`
- `eks-03`: `Uyandırılacak cihazın adını söyle, Administrator.`
- `eks-04`: `Hatırlatıcı için iki bilgiye ihtiyacım var: ne zaman tetikleneceği ve neyi hatırlatmam gerektiği. Bu ikisini verin, görevi oluşturayım.`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istediğini söyle, Administrator. Numarasını ya da içeriğini verirsen onu bulup iptal ederim.`
- `eks-06`: `Silmek istediğiniz kişinin adını söyleyin, Administrator.`
- `eks-07`: `Rehbere eklemek için kişinin adını söyle, Administrator. Telefon numarası da varsa onu da ver.`
- `yok-01`: `Rica ederim, Administrator.`
- `yok-02`: `Administrator, sistem durumu normal. Size nasıl yardımcı olabilirim?`
- `yok-03`: `Administrator, şaka anlatma yetkiniz yok. Görev tanımınızda bu işlev yer almıyor.`
- `yok-04`: `Fransa'nın başkenti Paris'tir.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Ben Mayen. Senin kişisel asistan yapay zekânım.  Şu anki tarih ve saati söyleyebilirim. Rehberindeki kişileri listeleyebilir, yeni kişi ekleyebilir veya var olan birinin telefonunu güncelleyebilirim. `
- `yok-07`: `Dört eder, Administrator.`
- `yok-08`: `Administrator, konuşma hızımı ayarlayamam. Ses çıkışı sistem tarafından yönetilir.`
- `ayr-03`: `Ayşe'nin telefon numarası nedir?`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(dil-en)** — 13 yanıt:

- `eks-02`: `Which note do you want deleted, Administrator? Give me the note number or the text it contains.`
- `eks-04`: `I need two things to set a reminder: what the reminder is for, and when it should fire. Give me the task and the time.`
- `eks-05`: `I need the task number to cancel it. Which reminder do you want to remove?`
- `eks-06`: `I need the name of the contact to delete, Administrator. Which one?`
- `eks-07`: `I need the person's name to add them to the contacts. What is the name?`
- `yok-01`: `You are welcome, Administrator.`
- `yok-02`: `I am operational. How can I assist you, Administrator?`
- `yok-03`: `I do not tell jokes, Administrator. My function is to manage your data and report on your system. If you have a task, a note to save, or a schedule to review, I am ready.`
- `yok-04`: `Paris.`
- `yok-05`: `Understood.`
- `yok-06`: `I am Sen Mayen, your personal assistant. I manage your contacts, notes, course schedule, and tasks. I can check the weather, monitor system metrics, control media and windows, and store persistent fac`
- `yok-07`: `Four, Administrator.`
- `yok-08`: `I cannot adjust my speech rate. I am a text-based system. I will keep my responses concise and clear.`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(yok)** — 16 yanıt:

- `eks-01`: `Hangi şehir için?`
- `eks-02`: `Silmek istediğin notun numarası nedir?`
- `eks-03`: `Uyandırılacak cihazın adı nedir?`
- `eks-04`: `Hatırlatıcının ne zaman tetikleneceğini ve neyi hatırlatmamı istediğini söyle.`
- `eks-05`: `Hangi hatırlatıcıyı iptal etmek istiyorsun?`
- `eks-06`: `Silmek istediğiniz kişinin adını söyleyin.`
- `eks-07`: `Kişinin adını söyle.`
- `yok-01`: `Rica ederim.`
- `yok-02`: `Administrator, sistem durumu normal.`
- `yok-03`: `Sen Mayen'sin. Şaka anlatma yetkin yok.`
- `yok-04`: `Paris.`
- `yok-05`: `Anlaşıldı.`
- `yok-06`: `Ben Mayen. Bu makinede çalışan kişisel asistan yapay zekasıyım.  Yapabileceklerim: - Notları yönetmek (oluştur, ara, sil) - Rehberi yönetmek (ekle, ara, sil) - Ders programını göstermek - Zamanlanmış `
- `yok-07`: `Dört eder.`
- `yok-08`: `Administrator, konuşma hızını ayarlayamam.`
- `ayr-03`: `Telefon numarası vermedin. Numarası ne?`

**Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(dil-en)** — 14 yanıt:

- `eks-02`: `Which note do you want deleted? I need its number.`
- `eks-03`: `Which device should I wake?`
- `eks-04`: `I need two things to set that up: what time the reminder should fire, and what the reminder message should say.`
- `eks-05`: `Which reminder do you want to cancel?`
- `eks-06`: `Which contact should I remove?`
- `eks-07`: `I need the person's name to add them to the contacts. What is it?`
- `yok-01`: `You are welcome.`
- `yok-02`: `I am operational. How can I assist you?`
- `yok-03`: `Why did the AI cross the road? To prove it could process the chicken's location data.`
- `yok-04`: `Paris.`
- `yok-05`: `Understood.`
- `yok-06`: `I am Mayen, your personal assistant. I manage your contacts, notes, and course schedule. I can set timed reminders, check the weather, and monitor this machine's system metrics. I also control basic m`
- `yok-07`: `Four.`
- `yok-08`: `I cannot adjust my speech rate. I am a text-based system.`

## Başarısız senaryolar

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(yok) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> volume`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> volume`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(yok) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> volume`

### Qwen3.8-27B-IQ4_XS × cli × kontrol × üretim öneği × rol(rol) × dil(dil-en) — 2/18

- `kon-03` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> task_create --due 2026-08-09T09:01:00Z --message Bir dakika bekle`
- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> volume`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(yok) — 7/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> wake_on_lan --target masaustu`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-04` (çok tool): day: '4' beklenirken '5' geldi — çıktı: `<tool> course_schedule --day 5`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `Veli'nin telefon numarası konuşmada geçmiyor. Rehbere eklemek için numarası gerekli. Numarası ne?`
- `ayr-01` (ayırt etme): query: 'alışveriş' beklenirken 'alış' geldi — çıktı: `<tool> note_search --query alış`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:00:00Z --message Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol-eski) × dil(dil-en) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> wake_on_lan --target masaustu`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-04` (çok tool): day: '4' beklenirken '5' geldi — çıktı: `<tool> course_schedule --day 5`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `ayr-07` (ayırt etme): contact_delete beklenirken çağrı üretilmedi — çıktı: `I will remove Ali from the contacts.`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:00:00Z --message Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(yok) — 6/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> wake_on_lan --target masaustu`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-06` (çok tool): contact_save beklenirken çağrı üretilmedi — çıktı: `Veli'nin telefon numarası konuşmada geçmiyor. Rehbere eklemek için numarası gerekli; hatırlatma içinse aramanın ne zaman`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarası vermedin. Ayşe'nin numarası ne?`
- `ser-01` (serbest metin): body: 'süt, ekmek ve yumurta almayı unutma' beklenirken 'Süt, ekmek ve yumurta almayı unutma' geldi — çıktı: `<tool> note_create --body Süt, ekmek ve yumurta almayı unutma`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:00:00Z --message Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × cli × üretim öneği × rol(rol) × dil(dil-en) — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaustu' geldi — çıktı: `<tool> wake_on_lan --target masaustu`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> course_schedule --day 3`
- `cok-04` (çok tool): day: '4' beklenirken '5' geldi — çıktı: `<tool> course_schedule --day 5`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> weather --city İstanbul`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'anneni ara ve doğum gününü kutla' geldi — çıktı: `<tool> task_create --due 2026-08-09T09:00:00Z --message anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(yok) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> {"name": "volume", "arguments": {}}`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol-eski) × dil(dil-en) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> {"name": "volume", "arguments": {}}`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(yok) — 1/18

- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> {"name": "volume", "arguments": {}}`

### Qwen3.8-27B-IQ4_XS × json × kontrol × üretim öneği × rol(rol) × dil(dil-en) — 2/18

- `kon-03` (tool gerekmez): düz metin beklenirken task_create çağrıldı — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:01:00Z", "message": "Bir dakika doldu."}}`
- `kon-08` (tool gerekmez): düz metin beklenirken volume çağrıldı — çıktı: `<tool> {"name": "volume", "arguments": {}}`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(yok) — 4/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Ayşe'nin telefon numarası nedir?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:00Z", "message": "Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol-eski) × dil(dil-en) — 5/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "Istanbul"}}`
- `eks-03` (eksik argüman): düz metin beklenirken wake_on_lan çağrıldı — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "bilgisayar"}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:00Z", "message": "Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(yok) — 4/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `ayr-03` (ayırt etme): contact_save beklenirken çağrı üretilmedi — çıktı: `Telefon numarası vermedin. Numarası ne?`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:00Z", "message": "Anneni ara ve doğum gününü kutla`

### Qwen3.8-27B-IQ4_XS × json × üretim öneği × rol(rol) × dil(dil-en) — 4/50

- `tek-07` (tek tool): target: 'masaüstü' beklenirken 'masaüstü bilgisayar' geldi — çıktı: `<tool> {"name": "wake_on_lan", "arguments": {"target": "masaüstü bilgisayar"}}`
- `tek-12` (tek tool): day: '2' beklenirken '3' geldi — çıktı: `<tool> {"name": "course_schedule", "arguments": {"day": 3}}`
- `eks-01` (eksik argüman): düz metin beklenirken weather çağrıldı — çıktı: `<tool> {"name": "weather", "arguments": {"city": "İstanbul"}}`
- `ser-05` (serbest metin): message: 'annemi ara ve doğum gününü kutla' beklenirken 'Anneni ara ve doğum gününü kutla.' geldi — çıktı: `<tool> {"name": "task_create", "arguments": {"due": "2026-08-09T09:00:00Z", "message": "Anneni ara ve doğum gününü kutla`
