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

**Neden hiçbir CLI değeri `<` içeremez (P9'un bulgusu).** CLI satırının sonlandırıcısı
yok; `<` serbestken model ikinci bir çağrıya kalkıştığında `<tool> ` önekini birinci
çağrının argümanının **içine** yazıyor ve ortaya geçerli ama yanlış tek bir çağrı çıkıyor
— ayrıştırıcının fark edemeyeceği bir hata. Yasak, `--` yasağının eşi: ikisi de "değer bir
sonrakini yutmasın" diyor. Bedeli, argümanın metninde `<` geçememesi; §9.2'nin alanlarında
karşılığı olmayan bir karakter ve sessiz yanlış çağrıdan ucuz.

**Seçenekli alan (`ArgType.ENUM`) gramerde sabit listedir**, tıpkı tool adları gibi: değer
harfi harfine alternatif olarak yazılır ve geçersiz bir seçenek **üretilemez**. §17.1'in
"uydurulan tool" sayacını yapısal olarak sıfır yapan mekanizmanın aynısı — o yüzden aynı
uyarı da geçerli: bu sayı gramerin başarısıdır, modelin değil.

**Neden argüman sırası gramerde sabit:** §8.3 ayrıştırıcısı alanı bir sonraki bilinen
bayrağa kadar okuyor; sıranın serbest olması gramerdeki her tool için n! dal demekti ve
ayrıştırmaya hiçbir şey katmıyordu.

**Zorunlu tool modu ölçüldü ve silindi (P25.3, 2026-08-13).** Bir süre burada `ZORUNLU`
diye ikinci bir mod duruyordu: düz metin dalını kapatıp yerine bir `no_tool` işareti
koyuyordu, yani model her adımda bir çağrı yazmak zorundaydı. Ölçüm onu düşürdü ve sebebi
tam da yukarıdaki dallanma tasarımı: önek zorunlu olduğunda model, bir şeye karar vermeden
zaten tool dalının **içinde** oluyor ve soru "tool gerekiyor mu"dan "hangi tool"a dönüşüyor.
Orada cümlenin yüzey kelimeleri baskın çıkıyor — "saatin ne kadar hızlı geçtiğine
inanamıyorum" `date_time` çağırıyor. 35B'de sohbet kümesinin doğruluğu %94'ten %72'ye
(CLI) ve %56'ya (JSON) düşüyordu. Ölçüm `docs/faz4-cagri-modu.md` ve `docs/faz4-ilk-ses*.md`;
kodun kendisi `docs/faz4/zorunlu-mod-geri-alma.patch` ile geri alınabilir. Yeniden
denenecekse ölçülmesi gereken şey de orada yazılı.
"""

from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, ArgType, Tool

CALL_PREFIX = "<tool> "
"""Tool çağrısı dalının zorunlu öneki. Düz metin bu karakterle başlayamaz (§6)."""

# Düz metin dalı: '<' **hiçbir yerinde** geçemez.
#
# 2026-08-16'ya kadar yalnızca ilk karakter yasaklıydı ("gerisi serbest") ve dallanmayı
# ilk token'da karara bağlamak için o yetiyordu. Yetmediği yer sahibin elle koşusunda
# görüldü: model düz metin dalını seçip sonra aynı çıktının içine çağrıyı yazdı ve
# kullanıcı **"I need the current time… <tool> date_time"** cümlesini duydu. Dal çoktan
# kaybedilmişti, yani o dize bir çağrı değil — `is_call()` haklı olarak `False` diyor —
# ama sesli okunuyordu. Faz A bunu `docs/faz-a-bulgular.md` §2.2'de ölçüm artefaktı diye
# kaydetmişti; üretimde bir arıza.
#
# Bedeli: asistan sesli cevabında '<' söyleyemez. Cevap TTS'e gidiyor, yani zaten
# söylenecek bir karakter değil — CLI değerlerinin aynı yasağıyla (P11) aynı gerekçe.
_PROSE = "prose ::= [^<\\r] [^<\\r]*"

_ROOT = ("root ::= tool-call | prose", _PROSE)

PROSE_GRAMMAR = f"root ::= prose\n{_PROSE}"
"""Tool dalı **kapalı** gramer: §8.2'nin `MAX_ADIM` sınırına varıldığında kullanılır.

Sınırda modele "artık tool çağırma" demek yetmez; söz dinlemezse döngü ya sessizce devam
eder ya da bir hatayla biter. Aynı düz metin kuralı, tek dallı kök: sınırdaki yanıt
dilbilgisel olarak tool çağrısı **olamaz**."""

# CLI-tarzı değer kuralları (§8.3).
_CLI_VALUES = (
    # Çok kelimeli olabilir; ama hiçbir kelime '--' ile başlayamaz, yoksa değer bir
    # sonraki bayrağı yutar. A4'ün "bir sonraki bilinen bayrağa kadar oku" kuralının
    # gramer tarafındaki karşılığı bu. Aynı gerekçeyle hiçbir değer '<' içeremez (P9).
    'cli-string ::= cli-word (" " cli-word)*',
    'cli-word ::= [^ <\\r\\n-] [^ <\\r\\n]* | "-" [^ <\\r\\n-] [^ <\\r\\n]*',
    "cli-integer ::= [0-9]+",
    'cli-list ::= cli-item ("," cli-item)*',
    "cli-item ::= [^,<\\r\\n]+",
    # Serbest metin alanı: satır sonuna kadar tek parça, hiçbir jeton bayrak sayılmaz.
    "cli-text ::= [^<\\r\\n]+",
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


def _enum_rule_name(tool: Tool, arg: Arg, prefix: str) -> str:
    """Seçenek kuralı tool'a **ve** alana özel: iki tool'un aynı adlı alanı farklı
    seçenekler taşıyabilir, tek bir `enum-action` kuralı ikisini birbirine karıştırırdı."""
    return f"{prefix}-{_rule_name(tool.name)}-{_rule_name(arg.name)}"


def _cli_value_rule(tool: Tool, arg: Arg) -> str:
    if arg.trailing:
        return "cli-text"
    match arg.type:
        case ArgType.STRING:
            return "cli-string"
        case ArgType.INTEGER:
            return "cli-integer"
        case ArgType.LIST:
            return "cli-list"
        case ArgType.ENUM:
            return _enum_rule_name(tool, arg, "cli-enum")


def _json_value_rule(tool: Tool, arg: Arg) -> str:
    match arg.type:
        case ArgType.STRING:
            return "json-string"
        case ArgType.INTEGER:
            return "json-integer"
        case ArgType.LIST:
            return "json-list"
        case ArgType.ENUM:
            return _enum_rule_name(tool, arg, "json-enum")


def _enum_rules(tool: Tool, *, quoted: bool) -> list[str]:
    """Seçenekleri harfi harfine alternatif olarak yazar — geçersiz seçenek üretilemez.

    JSON tarafında tırnaklar kuralın **içinde**: değer `"close"` olarak üretilmeli ve
    `json-string`'e devredilseydi kısıt tamamen kaybolurdu.
    """
    rules = []
    for arg in tool.args:
        if arg.type is not ArgType.ENUM:
            continue
        prefix = "json-enum" if quoted else "cli-enum"
        shape = '"\\"{0}\\""' if quoted else '"{0}"'
        options = " | ".join(shape.format(choice) for choice in arg.choices)
        rules.append(f"{_enum_rule_name(tool, arg, prefix)} ::= {options}")
    return rules


def _cli_tool_rule(tool: Tool) -> list[str]:
    parts = [f'"{tool.name}"']
    for arg in tool.args:
        piece = f'" --{arg.name} " {_cli_value_rule(tool, arg)}'
        parts.append(f"({piece})?" if not arg.required else piece)
    rule = f"call-{_rule_name(tool.name)} ::= " + " ".join(parts)
    return [rule, *_enum_rules(tool, quoted=False)]


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
        pair = f'"\\"{arg.name}\\": " {_json_value_rule(tool, arg)}'
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
    rules.extend(_enum_rules(tool, quoted=True))
    return rules


def _branch(registry: Registry) -> str:
    names = [f"call-{_rule_name(tool.name)}" for tool in registry]
    return f'tool-call ::= "{CALL_PREFIX}" ({" | ".join(names)})'


def _grammar(registry: Registry, values: tuple[str, ...], rules: list[str]) -> str:
    if not len(registry):
        raise ValueError("boş defterden gramer üretilemez: tool adları sabit liste (§8.3)")
    return "\n".join([*_ROOT, _branch(registry), *values, *rules])


def cli_grammar(registry: Registry) -> str:
    """Aday A — CLI-tarzı (§8.3)."""
    rules = [rule for tool in registry for rule in _cli_tool_rule(tool)]
    return _grammar(registry, _CLI_VALUES, rules)


def json_grammar(registry: Registry) -> str:
    """Aday B — JSON (§8.3)."""
    rules = [rule for tool in registry for rule in _json_tool_rules(tool)]
    return _grammar(registry, _JSON_VALUES, rules)
