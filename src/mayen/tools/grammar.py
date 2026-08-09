"""Kayıt defterinden GBNF üretimi — her iki aday çağrı biçimi için (§8.3, §6).

**Biçim kararı burada verilmiyor.** §19.1 açık: CLI-tarzı mı JSON mu, P7'nin ölçümü
söyleyecek. Bu yüzden iki üretici de var ve ikisi de aynı defterden besleniyor; seçilen
biçim, aynı katalogla ölçülmüş iki sayının karşılaştırmasından çıkacak.

**Dallanma ilk token'da belli (C3, §6).** Tool çağrısı dalı sabit ve zorunlu bir önekle
başlar; düz metin dalı ise o öneki başlatan karakterle **başlayamaz**. Böylece üretimin
ilk token'ında hangi dalda olunduğu bellidir ve tampon tek token'da boşalır. Önek iki
adayda da aynı: ölçüm çağrı kodlamasını karşılaştırsın, iki farklı öneki değil.

**Neden `[^\\r]` "her karakter" yerine:** GBNF'de "herhangi bir karakter" atomu yok.
Satır başı karakteri dışlamak pratikte hiçbir şeyi dışlamıyor — modelin `\\r` üretmesi
için bir sebep yok — ama kural yazılabilir hâle geliyor.

**Neden argüman sırası gramerde sabit:** §8.3 ayrıştırıcısı alanı bir sonraki bilinen
bayrağa kadar okuyor; sıranın serbest olması gramerdeki her tool için n! dal demekti ve
ayrıştırmaya hiçbir şey katmıyordu.
"""

from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool

CALL_PREFIX = "<tool> "
"""Tool çağrısı dalının zorunlu öneki. Düz metin bu karakterle başlayamaz (§6)."""

_COMMON = (
    "root ::= tool-call | prose",
    # Düz metin dalı: ilk karakter '<' olamaz, gerisi serbest.
    "prose ::= [^<\\r] [^\\r]*",
)

# CLI-tarzı değer kuralları (§8.3).
_CLI_VALUES = (
    # Çok kelimeli olabilir; ama hiçbir kelime '--' ile başlayamaz, yoksa değer bir
    # sonraki bayrağı yutar. A4'ün "bir sonraki bilinen bayrağa kadar oku" kuralının
    # gramer tarafındaki karşılığı bu.
    'cli-string ::= cli-word (" " cli-word)*',
    'cli-word ::= [^ \\r\\n-] [^ \\r\\n]* | "-" [^ \\r\\n-] [^ \\r\\n]*',
    "cli-integer ::= [0-9]+",
    'cli-list ::= cli-item ("," cli-item)*',
    "cli-item ::= [^,\\r\\n]+",
    # Serbest metin alanı: satır sonuna kadar tek parça, hiçbir jeton bayrak sayılmaz.
    "cli-text ::= [^\\r\\n]+",
)

_JSON_VALUES = (
    'json-string ::= "\\"" json-char* "\\""',
    'json-char ::= [^"\\\\\\r\\n] | "\\\\" ["\\\\/bfnrt]',
    "json-integer ::= [0-9]+",
    'json-list ::= "[" json-string ("," " " json-string)* "]"',
)


def _rule_name(name: str) -> str:
    """GBNF kural adlarında alt çizgi yok; tool adları `note_create` biçiminde."""
    return name.replace("_", "-")


def _cli_value_rule(arg: Arg) -> str:
    if arg.trailing:
        return "cli-text"
    match arg.type:
        case ArgType.STRING:
            return "cli-string"
        case ArgType.INTEGER:
            return "cli-integer"
        case ArgType.LIST:
            return "cli-list"


def _json_value_rule(arg: Arg) -> str:
    match arg.type:
        case ArgType.STRING:
            return "json-string"
        case ArgType.INTEGER:
            return "json-integer"
        case ArgType.LIST:
            return "json-list"


def _cli_tool_rule(tool: Tool) -> str:
    parts = [f'"{tool.name}"']
    for arg in tool.args:
        piece = f'" --{arg.name} " {_cli_value_rule(arg)}'
        parts.append(f"({piece})?" if not arg.required else piece)
    return f"call-{_rule_name(tool.name)} ::= " + " ".join(parts)


def _json_tool_rules(tool: Tool) -> list[str]:
    """İsteğe bağlı alanlar ve virgüller: "henüz alan yazılmadı" (A) ile "yazıldı" (B)
    durumları ayrı kural zincirleri. Tek zincirle yazılırsa, ilk alanı atlanan bir çağrı
    baştaki virgülle geçerli JSON olmaktan çıkardı."""
    stem = _rule_name(tool.name)
    head = (
        f'call-{stem} ::= "{{\\"name\\": \\"{tool.name}\\", \\"arguments\\": {{"'
        f" args-{stem}-0"
        ' "}}"'
    )
    rules = [head]
    count = len(tool.args)
    for index, arg in enumerate(tool.args):
        pair = f'"\\"{arg.name}\\": " {_json_value_rule(arg)}'
        first = f"args-{stem}-{index}"
        more = f"more-{stem}-{index}"
        nxt_first = f"args-{stem}-{index + 1}"
        nxt_more = f"more-{stem}-{index + 1}"
        if arg.required:
            rules.append(f"{first} ::= {pair} {nxt_more}")
            rules.append(f'{more} ::= ", " {pair} {nxt_more}')
        else:
            rules.append(f"{first} ::= ({pair} {nxt_more}) | {nxt_first}")
            rules.append(f'{more} ::= (", " {pair} {nxt_more}) | {nxt_more}')
    rules.append(f'args-{stem}-{count} ::= ""')
    rules.append(f'more-{stem}-{count} ::= ""')
    return rules


def _branch(registry: Registry) -> str:
    names = " | ".join(f"call-{_rule_name(tool.name)}" for tool in registry)
    return f'tool-call ::= "{CALL_PREFIX}" ({names})'


def _grammar(registry: Registry, values: tuple[str, ...], rules: list[str]) -> str:
    if not len(registry):
        raise ValueError("boş defterden gramer üretilemez: tool adları sabit liste (§8.3)")
    return "\n".join([*_COMMON, _branch(registry), *values, *rules])


def cli_grammar(registry: Registry) -> str:
    """Aday A — CLI-tarzı (§8.3)."""
    return _grammar(registry, _CLI_VALUES, [_cli_tool_rule(tool) for tool in registry])


def json_grammar(registry: Registry) -> str:
    """Aday B — JSON (§8.3)."""
    rules = [rule for tool in registry for rule in _json_tool_rules(tool)]
    return _grammar(registry, _JSON_VALUES, rules)
