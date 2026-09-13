"""Çağrı biçimi adaptörü: model çıktısı → `ToolCall` (§8.3).

İki aday biçim var — CLI-tarzı ve JSON — ve **ikisi de aynı iç temsili üretir**. Karar
(§19.1) P7'nin ölçümünden çıkacak; ajanın geri kalanı, politika ve tool'lar o karardan
etkilenmesin diye biçim bilgisi bu dosyanın dışına sızmaz.

**Değerler burada metindir, tiplenmez.** Şemalar `tools`'ta ve tiplemeyi `Tool.validate()`
yapıyor (§8.5 adım 1). Ayrıştırıcının işi sözdizimi; iki ayrı yerde tip dönüştürmek, iki
biçimin iki farklı tipleme davranışı kazanması demekti — oysa ölçüm tam da bunları eşit
koşulda karşılaştırmak için var. JSON tarafındaki sayı ve liste bu yüzden CLI'nin yazdığı
metne çevrilir; ikisi de aynı `validate()`'ten geçer.

**Bilinmeyen tool ve bilinmeyen argüman ayrı istisnalardır.** §17.1'in üç halüsinasyon
sayacından ikisi bunlar; tek bir "ayrıştırma hatası" altında toplanırlarsa sayaçlar
ayrılamaz. JSON'da bilinmeyen alanı `validate()` de yakalardı, ama o zaman iki biçim aynı
hatayı iki farklı yerde ve iki farklı adla verirdi — karşılaştırma bozulurdu.

**Düz metin dalı bir hata değildir** (§6): `is_call()` ile ayırt edilir. "Tool gerektirmeyen"
senaryolar (§18) tam olarak bu dalda ölçülüyor.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from mayen.adapters.llm import NativeCall
from mayen.tools.grammar import CALL_PREFIX
from mayen.tools.registry import Registry
from mayen.tools.spec import Arg, Tool


class CallFormat(StrEnum):
    """§8.3'ün iki adayı. Ölçüm bu iki değer üzerinde koşar."""

    CLI = "cli"
    JSON = "json"
    YEREL = "yerel"
    """Modelin **kendi** tool-calling şablonu (Faz B/2, 2026-08-16).

    Diğer ikisinin kardeşi değil, kuzeni: burada çağrı bir metin biçimi değil, isteğin
    ayrı bir alanı. Katalog `tools` alanında JSON şema (`tools/schema.py`), çağrıyı
    sunucu ayrıştırıyor, gramer yok — bu yüzden `instructions()` ve `parse()` bu değeri
    tanımıyor ve tanımamalı; onların işi metin.

    **Neden var:** metin biçimlerinde dal ilk token'da seçiliyor (§6/C3), yani model bir
    üretimde ya konuşabiliyor ya çağırabiliyor. İkisini birden istediğinde çağrıyı düz
    metnin içinde **taklit ediyor** ve taklit sesli okunuyor; `<` yasaklanınca köşeli
    parantezle aynısını yazdı. Yerel biçimde `content` ile `tool_calls` aynı yanıtta
    durur, yani çakışma yok. Ölçüm: `docs/faz-b-yerel.md`.
    """


@dataclass(frozen=True, slots=True)
class ToolCall:
    """§8.3'ün iç temsili. `arguments` ham metindir; tipli hâli `Tool.validate()`'ten çıkar."""

    name: str
    arguments: Mapping[str, str]


class CallParseError(Exception):
    """Model çıktısı çağrıya çevrilemedi."""


class UnknownToolError(CallParseError):
    """Defterde olmayan bir tool adı — halüsinasyon sayacı 1 (§17.1)."""


class UnknownArgumentError(CallParseError):
    """Tool'un imzasında olmayan bir argüman — halüsinasyon sayacı 2 (§17.1)."""


_INSTRUCTIONS = {
    CallFormat.CLI: (
        f'Bir tool çağırmak için tek satır yaz: "{CALL_PREFIX}" öneki, sonra tool adı,'
        ' sonra "--alan değer" çiftleri. Bir alanın değeri çok kelimeli olabilir;'
        " bir sonraki alana kadar okunur.\n"
        f"Örnek: {CALL_PREFIX}tool_adi --alan değer --başka_alan çok kelimeli değer"
    ),
    CallFormat.JSON: (
        f'Bir tool çağırmak için tek satır yaz: "{CALL_PREFIX}" öneki, sonra JSON nesnesi.\n'
        f'Örnek: {CALL_PREFIX}{{"name": "tool_adi", "arguments": {{"alan": "değer"}}}}'
    ),
}

_PROSE_RULE = 'Tool gerekmiyorsa doğrudan kullanıcıya yanıt yaz; o yanıt "<" ile başlayamaz.'
"""Düz metin dalının modele anlatıldığı yer. **Katalogda değil**, bilerek: katalog §9.1'in
yetenek listesi ve "tool çağırmamak" bir yetenek değil."""


def instructions(call_format: CallFormat) -> str:
    """Sistem promptunun "çağrı nasıl yazılır" bölümü (§8.1'in sabit öneki).

    **Katalogla aynı yerde değil, bilerek:** `tools/prompt.py` hangi tool'ların *var*
    olduğunu yazıyor, burası onların nasıl *çağrılacağını*. İkincisi biçim kararına
    (§19.1) bağlı, `tools` ise `agent`'i import edemez (§4) — yani `CallFormat`'ı görmesi
    zaten mümkün değil. Biçimin tüm yüzü tek dosyada duruyor: gramer önekini kullanan,
    ayrıştıran ve tarif eden metin.

    **Örnekte gerçek tool adı yok.** Katalog hemen altında geliyor; buraya yazılacak
    gerçek bir çağrı, imza değiştiğinde sessizce yalan söyleyen ikinci bir kopya olurdu —
    `usage()`'ın ayrıca yazılmamasıyla aynı gerekçe. Deneyle doğrulandı: şematik örnekle
    de model doğru dalı seçiyor.

    **Bu metnin kendisi bir ölçüm değişkenidir.** §17.1 prompt değişikliğini de değerlendirme
    kapısına bağlıyor; burada değişen bir kelime, P7'nin kapısından geçmek zorundadır.
    """
    return f"{_INSTRUCTIONS[call_format]}\n{_PROSE_RULE}"


def from_native(registry: Registry, call: NativeCall) -> ToolCall:
    """Sunucunun ayrıştırdığı çağrıyı doğrulanmış bir `ToolCall`'a çevirir.

    **Değerler metne çevrilip `Tool.validate`'e veriliyor.** Şema tipli değer üretiyor
    (`{"level": 40}` bir `int`), `validate` ise metin bekliyor — çünkü §8.3'ün iki metin
    biçiminin ürünü. Esneyen taraf burası: `validate` üretimin tek doğrulama noktası
    (§9.1) ve bir çağrı biçimi için gevşetilmesi, kısıtı biçim başına ikiye bölmek olurdu.
    Liste virgülle birleşiyor — `_coerce`'ün ayırdığı yer.
    """
    tool = _lookup(registry, call.name)
    raw = {
        name: ",".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for name, value in call.arguments.items()
    }
    tool.validate(raw)
    return ToolCall(name=call.name, arguments=raw)


def is_call(text: str) -> bool:
    """Çıktı tool dalında mı, düz metin dalında mı (§6: ilk token'da belli)."""
    return text.startswith(CALL_PREFIX)


def parse(registry: Registry, call_format: CallFormat, text: str) -> ToolCall:
    """Tool dalındaki çıktıyı ayrıştırır. Düz metinle çağrılması bir kod hatasıdır."""
    if not is_call(text):
        raise CallParseError(f"çıktı {CALL_PREFIX!r} önekiyle başlamıyor")
    body = text[len(CALL_PREFIX) :].rstrip("\r\n")
    match call_format:
        case CallFormat.CLI:
            return _parse_cli(registry, body)
        case CallFormat.JSON:
            return _parse_json(registry, body)
        case CallFormat.YEREL:
            # Yerel biçimde ayrıştırma taşımanın altında (`from_native`); buraya düşmek
            # kodun hatası, modelin değil.
            raise ValueError("yerel biçimde metin ayrıştırılmaz: from_native() kullanın")


def _lookup(registry: Registry, name: str) -> Tool:
    try:
        return registry.get(name)
    except KeyError as exc:
        raise UnknownToolError(f"defterde böyle bir tool yok: {name!r}") from exc


def _known_arg(tool: Tool, name: str) -> Arg:
    for arg in tool.args:
        if arg.name == name:
            return arg
    raise UnknownArgumentError(f"{tool.name}: imzada böyle bir argüman yok: {name!r}")


def _parse_cli(registry: Registry, body: str) -> ToolCall:
    """`ad --bayrak değer --bayrak değer` (§8.3).

    Değer bir sonraki **bilinen** bayrağa kadar okunur; gramerde hiçbir değer kelimesi
    `--` ile başlayamadığı için `--` gören her jeton bayraktır. Serbest metin alanından
    sonrası satır sonuna kadar tek parçadır ve içindeki hiçbir jeton bayrak sayılmaz.
    """
    name, _, rest = body.partition(" ")
    if not name:
        raise CallParseError("tool adı yok")
    tool = _lookup(registry, name)

    # split(" ") bilerek: boşlukları normalleştiren split() serbest metin alanındaki
    # aralıkları sessizce değiştirirdi. Gramer çift boşluk üretemez, üretmişse hatadır.
    words = rest.split(" ") if rest else []
    arguments: dict[str, str] = {}
    index = 0
    while index < len(words):
        word = words[index]
        if not word.startswith("--"):
            raise CallParseError(f"{name}: bayrak beklenirken {word!r} geldi")
        flag = word[2:]
        arg = _known_arg(tool, flag)
        if flag in arguments:
            raise CallParseError(f"{name}: {flag!r} iki kere verildi")
        if arg.trailing:
            value = " ".join(words[index + 1 :])
            index = len(words)
        else:
            end = index + 1
            while end < len(words) and not words[end].startswith("--"):
                end += 1
            value = " ".join(words[index + 1 : end])
            index = end
        if not value:
            raise CallParseError(f"{name}: {flag!r} değersiz")
        arguments[flag] = value
    return ToolCall(name=name, arguments=arguments)


def _parse_json(registry: Registry, body: str) -> ToolCall:
    """`{"name": ..., "arguments": {...}}` (§8.3)."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CallParseError(f"geçersiz JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise CallParseError("JSON çağrısı bir nesne olmalı")
    if set(payload) != {"name", "arguments"}:
        raise CallParseError(
            f"çağrının alanları 'name' ve 'arguments' olmalı: {sorted(payload)}"
        )
    name = payload["name"]
    if not isinstance(name, str):
        raise CallParseError("'name' bir metin olmalı")
    tool = _lookup(registry, name)
    raw = payload["arguments"]
    if not isinstance(raw, dict):
        raise CallParseError(f"{name}: 'arguments' bir nesne olmalı")

    arguments: dict[str, str] = {}
    for key, value in raw.items():
        _known_arg(tool, key)
        arguments[key] = _json_value_text(name, key, value)
    return ToolCall(name=name, arguments=arguments)


def _json_value_text(tool_name: str, key: str, value: object) -> str:
    """JSON değerini CLI'nin yazdığı metne çevirir — iki biçim aynı `validate()`'e girsin diye.

    Virgül içeren liste öğesi reddediliyor: CLI kodlaması onu temsil edemiyor, sessizce
    ikiye bölmek de argüman doğruluğunu ölçen sayacı yanıltırdı (Kural 13).
    """
    if isinstance(value, bool):
        raise CallParseError(f"{tool_name}: {key!r} mantıksal değer alamaz")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, str):
                raise CallParseError(f"{tool_name}: {key!r} listesinde metin olmayan öğe var")
            if "," in item:
                raise CallParseError(f"{tool_name}: {key!r} liste öğesi virgül içeremez")
            items.append(item)
        return ",".join(items)
    raise CallParseError(f"{tool_name}: {key!r} için beklenmeyen değer tipi")
