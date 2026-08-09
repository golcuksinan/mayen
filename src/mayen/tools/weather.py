"""Hava durumu (§9.2, DIŞ). Sağlayıcı: OpenWeatherMap (§19.7).

**Anahtar depoya girmez:** ortamdan `Secret` olarak gelir ve yalnızca sorgu parametresine
yazılırken açılır. Anahtar yoksa tool sessizce çalışmaz — açık hata döner (§14).

**Kota ve anahtar hataları yutulmuyor** (§14, Kural 13): 401 ve 429 ayrı ayrı, okunabilir
biçimde geri veriliyor; model bunu bilerek yanıt üretebilsin diye hata bir sonuç alanı,
istisna değil (§8.2: tool hatası modele geri beslenir).
"""

from collections.abc import Mapping

import httpx

from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text

_URL = "https://api.openweathermap.org/data/2.5/weather"


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    key = context.config.openweathermap_key
    if key is None:
        return ToolResult(ok=False, error="hava durumu anahtarı yapılandırılmamış (§19.7)")
    city = text(arguments, "city")
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
    return ToolResult(
        ok=True,
        data={"city": city, "temperature_c": temperature, "condition": condition},
        speech=f"{city}: {temperature} degrees, {condition}.",
    )


TOOL = Tool(
    name="weather",
    description="Bir şehrin güncel hava durumunu verir.",
    effect=Effect.DIS,
    timeout_seconds=8.0,
    handler=_run,
    args=(Arg("city", ArgType.STRING, "Şehir adı"),),
)
