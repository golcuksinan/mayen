"""Hava durumu (§9.2, DIŞ). Sağlayıcı: OpenWeatherMap (§19.7).

**Anahtar depoya girmez:** ortamdan `Secret` olarak gelir ve yalnızca sorgu parametresine
yazılırken açılır. Anahtar yoksa tool sessizce çalışmaz — açık hata döner (§14).

**`--fields` §8.3'ün liste kodlamasının defterdeki tek örneği.** Doküman kendi CLI
örneğini `weather --city Denizli --fields temperature,condition` diye yazıyor; defterde
hiç `ArgType.LIST` argümanı olmayınca o kodlama gerçek modelde hiç ölçülmemiş oluyordu.
Alan isteğe bağlı: verilmezse iki alan da döner — yokluğu bir filtre değil, filtre yok
demek. Tanınmayan alan adı sessizce atılmıyor, hata sonucu dönüyor (Kural 13); sessiz
atma, modelin istediğini aldığını sanmasıyla biterdi.

**Kota ve anahtar hataları yutulmuyor** (§14, Kural 13): 401 ve 429 ayrı ayrı, okunabilir
biçimde geri veriliyor; model bunu bilerek yanıt üretebilsin diye hata bir sonuç alanı,
istisna değil (§8.2: tool hatası modele geri beslenir).
"""

from collections.abc import Mapping

import httpx

from mayen.policy.effects import Effect
from mayen.tools.spec import (
    Arg,
    ArgType,
    Tool,
    ToolContext,
    ToolResult,
    optional_strings,
    text,
)

_URL = "https://pro.openweathermap.org/data/2.5/weather"

_FIELDS = ("temperature", "condition")
"""`--fields` ile istenebilecek alanlar. Sabit ve küçük: katalogda tek tek yazılabiliyor,
yani model neyi isteyebileceğini tahmin etmek zorunda kalmıyor."""


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    key = context.config.openweathermap_key
    if key is None:
        return ToolResult(ok=False, error="hava durumu anahtarı yapılandırılmamış (§19.7)")
    city = text(arguments, "city")
    wanted = optional_strings(arguments, "fields")
    if wanted is not None:
        unknown = [field for field in wanted if field not in _FIELDS]
        if unknown:
            return ToolResult(
                ok=False,
                error=f"bilinmeyen alan: {', '.join(unknown)}; geçerli: {', '.join(_FIELDS)}",
            )
    try:
        response = await context.http.get(
            _URL,
            params={"q": city, "appid": key.reveal(), "units": "metric", "lang": "en"},
        )
    except httpx.HTTPError as exc:
        return ToolResult(ok=False, error=f"hava servisine ulaşılamadı: {exc}")
    if response.status_code == httpx.codes.UNAUTHORIZED:
        return ToolResult(ok=False, error="hava servisi anahtarı reddedildi (401)")
    if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
        return ToolResult(ok=False, error="hava servisi kotası aşıldı (429)")
    if response.status_code == httpx.codes.NOT_FOUND:
        return ToolResult(ok=False, error=f"{city}: hava servisi böyle bir yer bulamadı")
    if response.status_code != httpx.codes.OK:
        return ToolResult(ok=False, error=f"hava servisi {response.status_code} döndü")

    try:
        payload = response.json()
        temperature = payload["main"]["temp"]
        condition = payload["weather"][0]["description"]
    except (ValueError, KeyError, IndexError) as exc:
        return ToolResult(ok=False, error=f"hava servisi beklenmedik bir yanıt verdi: {exc}")
    chosen = _FIELDS if wanted is None else tuple(f for f in _FIELDS if f in wanted)
    data: dict[str, object] = {"city": city}
    parts = []
    if "temperature" in chosen:
        data["temperature_c"] = temperature
        parts.append(f"{temperature} degrees")
    if "condition" in chosen:
        data["condition"] = condition
        parts.append(condition)
    return ToolResult(ok=True, data=data, speech=f"{city}: {', '.join(parts)}.")


TOOL = Tool(
    name="weather",
    description="Bir şehrin güncel hava durumunu verir.",
    effect=Effect.DIS,
    timeout_seconds=8.0,
    handler=_run,
    args=(
        Arg("city", ArgType.STRING, "Şehir adı"),
        Arg(
            "fields",
            ArgType.LIST,
            f"İstenen alanlar, virgülle: {', '.join(_FIELDS)}",
            required=False,
        ),
    ),
)
