"""Sahte adaptörler.

Bunlar oyuncak değil: §4'ün ports & adapters kararı gereği tur akışı, politika ve ajan
mantığının tamamı (P4–P8) bunların üstünde, GPU'suz ve saniyeler içinde test ediliyor.
Ayrıca çalışma anında da bağlanabiliyorlar (`--llm fake`), bu yüzden `tests/` altında
değil paketin içindeler.

Üçü ortak: davranış betikle verilir, çağrılar kaydedilir, hata enjekte edilebilir.
Kaydetme olmadan "önek değişmedi" (§8.1) gibi kurallar test edilemez.
"""
