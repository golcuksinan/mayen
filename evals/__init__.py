"""Faz 0 ölçümü ve §17.1'in tool seçim değerlendirmesi.

**Neden `src/mayen/` altında değil:** §4'ün on bir katmanı sayılıdır ve `tests/test_layout.py`
onları tek tek arar. Değerlendirme aracı bir katman değil; uygulamayı *dışarıdan* kullanan
bir tüketici. `mayen`'i import eder, `mayen` onu asla import etmez.

**Atılmıyor:** §18 Faz 0'ın kararı buradan çıkıyor, ama araç Faz 1'de §17.1'in değerlendirme
kapısı olarak kalıyor — her prompt, tool açıklaması ve model değişikliğinin geçmesi gereken
yer burası.
"""
