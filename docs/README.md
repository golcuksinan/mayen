# `docs/` — ne nerede

Elli yedi dosya var ve **hepsi aynı türden değil.** Bir sayıyı aktarmadan önce baktığın
dosyanın hangi tür olduğunu bil:

| Tür | Kim yazdı | Nasıl okunur |
|---|---|---|
| **Sözleşme** | elle | `ARCHITECTURE.md` ve `PLAN.md`. Kararların tek kaynağı. |
| **Okuma** | elle | Ham sayıları yorumlar, ne kanıtladığını ve **ne kanıtlamadığını** yazar. |
| **Ham rapor** | `evals/report.py` | Başlığı "Çağrı biçimi ve tool modu ölçümü" ya da "Oturum ölçümü" olan her dosya. Üretecin çıktısı, yorum içermez. |

**Ham raporu tek başına okuma.** Yorum okumada; okuması olmayan bir ham rapor bir koşunun
kaydıdır, bir bulgu değildir. Bazı ham raporların sonuna elle bir `## Okuma` bölümü
eklenmiştir (`faz6-onek.md`) — o bölüm okumadır, üstündeki tablo hamdır.

**Her sayıyı okumadan önce iki şey:** tarihi 2026-08-15'ten eski raporlar **3.6
nesli** üzerinde ölçüldü ve §17.1'in `uydurulan tool` uyarısını taşımıyor; ve bir sayının
hangi dünyayı ölçtüğünü sor (tek turluk kümeler üretimin geçmişini ölçmez — bkz.
`faz-c-model-taramasi.md`). Ayrıntı `CLAUDE.md`'nin "Measurement" bölümünde.

---

## Sözleşme

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — tasarım ve arkasındaki her karar. **Tek kaynak.**
  §19 açık maddeleri, §20 değişmezleri burada.
- **[PLAN.md](PLAN.md)** — P1–P28 iş paketleri: her biri ne yaptı, neyi neden reddetti.
  Sonunda §19 → paket bağımlılık haritası.

## Okumalar — kronolojik

Proje kararlarının hikâyesi bu on yedi dosyada. Sırayla okunursa neden bu kodun bu şekle
geldiği anlaşılır.

| Dosya | Ne buldu |
|---|---|
| [faz2-olcum.md](faz2-olcum.md) | LLM adaylarının VRAM ve tool seçim ölçümü; altın 50 senaryonun ilk taban çizgisi |
| [faz4-cagri-modu.md](faz4-cagri-modu.md) | **Zorunlu tool modu ölçüldü ve silindi** — §6'nın ikili dallanması çok yollu seçime dönüşüyor |
| [faz5-model-secimi.md](faz5-model-secimi.md) | 27B ile 35B **ayırt edilemiyor**; belgenin varlık sebebi ham raporların yanlış okunmasını engellemek |
| [faz6-rol.md](faz6-rol.md) · [faz6-27b-rol.md](faz6-27b-rol.md) | reddedilen rol metinleri, birebir |
| [faz6-onek.md](faz6-onek.md) | **Ölçüm öneği üretimin öneği değildi** (P27); altın 98→92, eksik-argüman 100→71 |
| [faz7-rol.md](faz7-rol.md) | **Bir prompt kuralının yeri bir kaldıraç** — aynı cümle rol metninde 2/18, katalogdan sonra 18/18 |
| [faz7-kokoro.md](faz7-kokoro.md) | Kokoro TTS kendi sürecinde; legacy'den ayrılan üç yer |
| [faz8-tool.md](faz8-tool.md) | Katalog genişlemesi; **eklenmeden önce silinen üç tool** ve `ENUM`'un gramerle zorlanması |
| [bellek-kirlenmesi.md](bellek-kirlenmesi.md) | `issues.md` #7'nin teşhisi — **adı yanlış çıktı, bkz. faz-a-bulgular** |
| [faz-a-bulgular.md](faz-a-bulgular.md) | Teşhis ölçüye çevrildi ve **teşhis yanlıştı**; suçlu bellek değil |
| [faz-b-bicim.md](faz-b-bicim.md) | Geçmişteki cevabın biçimi: beş aday ölçüldü |
| [faz-b-rol-hitap.md](faz-b-rol-hitap.md) | "Administrator" her cümlenin sonundan kalktı |
| [faz-b-sondaj-yerel.md](faz-b-sondaj-yerel.md) | Modelin kendi tool-calling şablonunun sondajı (betik scratchpad'de kaldı) |
| [faz-b-uygulama.md](faz-b-uygulama.md) | **Tool sonucu geçmişe `tool` rolünde yazılıyor** — üretimde çağrı yapılmama sorununun düzeltmesi |
| [faz-b-yerel.md](faz-b-yerel.md) | **§19.1 kapandı: `CallFormat.YEREL`** — karakter yasağı kılık değiştiriyor, sınıf tasarımsal |
| [faz-c-model-taramasi.md](faz-c-model-taramasi.md) | LFM2.5 ve 35B-A3B elendi; Kokoro'nun GPU ölçümü; **`halusinasyon` kümesi ile kabul kapısı farklı dünyaları ölçüyor** |

## Ham raporlar

Üreteç çıktıları. Hangi okumaya ait olduklarını yukarıdaki tablodan izle.

**Kök dizinde, faz sırasıyla:** `faz0-olcum.md` · `faz3-gecmis.md`, `faz3-gecmis-35b.md` ·
`faz4-ilk-ses.md`, `faz4-ilk-ses-35b.md` · `faz5-halusinasyon.md`, `faz5-model-27b.md`,
`faz5-model-35b.md` · `faz6-olcum.md`, `faz6-bellek.md`, `faz6-onay.md`, `faz6-35b.md`,
`faz6-35b-zorunlu.md`, `faz6-35b-tell-user.md`, `faz6-*-rol*.md` ·
`faz7-dil-kurali.md`, `faz7-dil-sistem-sonu.md`, `faz7-edden-27b*.md` ·
`faz8-tool-olcum.md` · `faz-a-taban.md`, `faz-a-oturum.md` ·
`faz-b-bicim-91.md`, `faz-b-bicim-118.md`, `faz-b-dogrulama.md`, `faz-b-oturum.md`,
`faz-b-rol-hitap-ham.md`, `faz-b-rol-hitap2.md`, `faz-b-tekrar.md`,
`faz-b-yerel-ham.md`, `faz-b-yerel-kumeler.md`

**Alt dizinler** — bir koşunun model başına ayrı dosyaya çıktığı yerler:

- **[faz2/](faz2/)** — dört LLM adayı, model başına bir dosya.
- **[faz4/](faz4/)** — çağrı biçimi ve tool modu, model başına bir dosya. Ayrıca
  `zorunlu-mod-geri-alma.patch`: zorunlu modu geri getiren yama. **Bayat** — P26/P27
  `evals/`i taşıdı, 14 dosyanın 4'ünde uygulanmıyor; `src/` kısmı temiz uyguluyor.
- **[faz-c/](faz-c/)** — LFM2.5 ve 35B-A3B koşuları, küme başına bir dosya.

## İkisi de olmayan bir dosya

`mayen.db` — sıfır bayt, bir koşudan artakalmış. Doküman değil; silinebilir.
