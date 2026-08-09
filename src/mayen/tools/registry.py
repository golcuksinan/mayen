"""Tool kayıt defteri (§9.1).

Yeni tool eklemek: bir dosya oluştur, `register()` ile kaydol. Başka hiçbir dosyaya
dokunulmaz.

Defter tek bir modül düzeyi sözlük değil, açıkça kurulan bir nesne: testler kendi
defterlerini kurabilsin ve global durum sızmasın diye. Katalog metni ve gramer aynı
defterden üretilir — tool listesinin iki ayrı kopyası olmaz.
"""

from collections.abc import Iterator

from mayen.tools.spec import Tool, ToolSpecError


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        """Aynı ad iki kere kaydedilemez: gramerde tool adı sabit listedir (§8.3)."""
        if tool.name in self._tools:
            raise ToolSpecError(f"{tool.name}: bu adla bir tool zaten kayıtlı")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        """Bilinmeyen ad `KeyError`'dır; sessizce `None` dönmez (Kural 13)."""
        return self._tools[name]

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self) -> Iterator[Tool]:
        """Kayıt sırasında gezinir: katalog metni ve gramer belirlenimci olsun diye."""
        return iter(self._tools.values())
