"""Kayıt defterinden JSON şema — modelin **kendi** tool-calling şablonu için (§8.3).

`grammar.py`'nin üçüncü kardeşi. O ikisi çağrıyı ham metin olarak *ürettiriyor* ve
katalog sistem promptunda metin olarak duruyor; bu modül aynı defteri sunucunun
`tools` alanına, yani modelin sohbet şablonunun beklediği yere veriyor. Kaynak tek
(§9.1): şema `usage()` gibi imzadan türetiliyor, tool'un yanına elle yazılmıyor —
yazılsaydı `docs/ARCHITECTURE.md` §9.1'in "belge koddan sapar" arızasının üçüncü
kopyası olurdu.

**Neden var.** Bugünkü tasarımda model bir üretimde ya konuşabiliyor ya çağırabiliyor
(§6/C3: dal ilk token'da belli). Sahibin 2026-08-16 koşusunda model ikisini birden
istedi — "anladım, kuruyorum; ama önce saati almam lazım" — ve düz metin dalına
kilitlendiği için çağrıyı **taklit etti**: gramerin yasakladığı `<` yerine
`[tool] date_time` yazdı, hiçbir şey koşmadı ve cümle sesli okundu. Karakter yasaklamak
bu sınıfı çözmüyor, kılığını değiştiriyor. Yerel biçimde çakışma yok: `content` ile
`tool_calls` aynı yanıtta durabiliyor.

**Karar değil, ölçüm.** Bu modül bugün yalnızca `evals` tarafından kullanılıyor;
üretimin çağrı biçimini seçen satır hâlâ `main.py:CALL_FORMAT` ve `CallFormat`'a
yeni bir değer eklenmedi. Sondaj `docs/faz-b-sondaj-yerel.md`'de: yerel biçim tek
başına 91'i çeviriyor, 118'i çevirmiyor ve ölçülebilir bir gecikme bedeli getirmiyor.

**`ENUM` burada `enum` olarak geçiyor** — gramerdeki "geçersiz seçenek üretilemez"
güvencesinin bu taraftaki karşılığı sunucunun şema kısıtı. §17.1'in uyarısı da aynen
geçerli: bu, gramerin (burada şemanın) başarısıdır, modelin değil.

**`trailing` şemada karşılıksız.** O bayrak CLI satırının "buradan sonrası tek parça
metin" kuralı (§8.3); JSON'da alanın sınırı zaten tırnak. Sessizce düşürülüyor, çünkü
şemada karşılığı olmayan bir şey değil — anlamsız bir şey.
"""

from typing import Any

from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool


def _field(arg: Arg) -> dict[str, Any]:
    match arg.type:
        case ArgType.INTEGER:
            field: dict[str, Any] = {"type": "integer"}
        case ArgType.LIST:
            field = {"type": "array", "items": {"type": "string"}}
        case ArgType.ENUM:
            field = {"type": "string", "enum": list(arg.choices)}
        case ArgType.STRING:
            field = {"type": "string"}
    field["description"] = arg.description
    return field


def tool_schema(tool: Tool) -> dict[str, Any]:
    """Tek tool'un OpenAI işlev şeması."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": {arg.name: _field(arg) for arg in tool.args},
                "required": [arg.name for arg in tool.args if arg.required],
            },
        },
    }


def schemas(registry: Registry) -> list[dict[str, Any]]:
    """Defterin tamamı, defterdeki sırayla.

    Sıra korunuyor: `grammar.py`'nin seçenek listelerindeki gerekçenin aynısı — istek
    gövdesi önekin parçası ve sıranın koşudan koşuya değişmesi önbelleği düşürürdü.
    """
    if not len(registry):
        raise ValueError("boş defterden şema üretilemez")
    return [tool_schema(tool) for tool in registry]
