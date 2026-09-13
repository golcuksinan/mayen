"""Başsız istemci (§7, §13, Faz 5).

`evals/` gibi depo kökünde duruyor, `src/mayen/` altında değil: §4'ün on bir katmanı var
ve `test_layout.py` onları tek tek sayıyor. İstemci bir katman değil, `mayen`'i **import
eden** ikinci bir süreç — tersi asla olmaz. Paylaştığı tek şey tel formatı
(`mayen.transport.frames`/`wire`), ki zaten paylaşılması gereken şey odur.

**Önce metin, sonra ses.** Sahte STT istemcinin metnini transkript sayıyor (P1) ve sahte
TTS cevabı UTF-8 baytı olarak "seslendiriyor"; yani protokolün tamamı — el sıkışma, tur
kimliği, sıra, söz kesme, iptal — bugün mikrofon olmadan koşuyor ve ölçülebiliyor.
Mikrofon ve hoparlör geldiğinde değişen şey `Output`'un uygulaması olacak; tur takibi,
ölü tur filtresi ve söz kesme yolu aynı kalacak. Bu paketin varlık sebebi tam olarak bu:
en zor kısım (§13'ün `turn_id`/`seq` kuralı) donanımdan bağımsız.

**Yazılmayanlar ve nedenleri:** wake word (§19.6 açık — motor ve kelime seçilmedi),
endpointing ve AEC (gerçek mikrofon işi; AEC §18'in kendi deyimiyle fazın en büyük
kalemi). Hiçbiri burada varsayımla kapatılmadı.
"""
