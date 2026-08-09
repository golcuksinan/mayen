"""Repository modülleri. SQL yalnızca burada; dışarı dataclass çıkar, `sqlite3.Row` değil.

`Row` döndürmek sütun adlarını üst katmanlara sızdırır ve "SQL `data/` dışına çıkmaz"
kuralını kâğıt üstünde bırakır: şemadaki bir yeniden adlandırma tool gövdelerini kırar.
"""
