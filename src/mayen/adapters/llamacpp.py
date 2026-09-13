"""`LLMClient`'ın llama.cpp (`llama-server`) uygulaması (§3, §14).

**Neden OpenAI uyumlu uç:** sohbet şablonunu modelin kendi `gguf`'undan uygulayan taraf
sunucu. Şablonu burada elle kurmak, model değiştiğinde sessizce yanlış biçimde prompt
üretmek demekti — ve §8.1'in sabit öneki tam da baytı baytına aynı kalmasıyla değerli.
`grammar` alanı llama.cpp'nin bu uca eklediği standart dışı alan; GBNF (§8.3) oradan
geçiyor.

**Token sayısı `/tokenize`'dan** (Kural 10). Sunucunun kendi sayacı; `usage` alanına da
bakılmıyor, çünkü `count_tokens` arayüzün sözü ve tek bir kaynaktan cevaplanmalı.

**"Servis yok" ile "servis hata döndürdü" ayrı** (§14): ilki yeniden başlatmaya, ikincisi
yukarı taşınmaya bağlanır. `health()` istisna fırlatmaz — yokluk normal bir cevaptır.

**Taşıma hatasında bir kez yeniden deneniyor — yalnızca `/tokenize` gibi akışsız
uçlarda.** P9'da bir koşu `/tokenize`'da `httpx.ReadError` ile koptu, tekrarı geçti, repro
tutturulamadı; ölçümde yeniden koşulacak bir şey, gerçek turda turu öldüren bir hata.
Yeniden deneme yalnızca `httpx.TransportError` için: durum kodu dönen bir sunucu
çalışıyordur ve aynı isteği tekrarlamak §14'ün "servis hata döndürdü" dalını gizlemek
olurdu. **Akış yeniden denenmiyor:** yarısı tüketilmiş bir üretimin tekrarı, aynı token'ları
ikinci kez akıtmak demek. Bekleme yok — gözlenen kopma anlıktı ve bir bekleme süresi
ölçülmemiş bir sayı olurdu. Deneme tükendiğinde hata yine yükseliyor (Kural 13).

**İptal (Kural 12):** akış bir async üreteç; çağıran `aclose()` çağırdığında ya da görev
iptal edildiğinde HTTP yanıtı kapanır ve sunucu üretimi durdurur. İkinci bir iptal jetonu
yok.

**Örnekleme ayarları istekte, sunucunun bayrağında değil** (2026-08-16, Faz A). Uzun süre
yalnızca `temperature` gönderildi ve geri kalanı `llama-server`'ın açılış bayraklarından
geldi; yani aynı kod, sunucu başka bir bayrakla açıldığı gün başka bir sistem oluyordu ve
bunu okuyanın görebileceği hiçbir yer yoktu. `evals/report.py`'nin `SAMPLERS` listesi bu
ayrışmayı **zaten görmüştü** — `presence_penalty` 35B'de 1.5, 27B'de 0 — ve raporlar
karşılaştırılırken karşılaştırılan şeyin bir bayrak seti olduğu orada yazılı. Sayılar
artık `Sampling`'de duruyor, isteğe yazılıyor ve rapora giriyor.
"""

import json
from collections.abc import AsyncGenerator, Sequence
from dataclasses import asdict, dataclass, fields
from typing import Any

import httpx

from mayen.adapters.errors import ServiceFailedError, ServiceUnavailableError
from mayen.adapters.llm import NativeCall, PromptMessage
from mayen.obs.log import get_logger

log = get_logger(__name__)

_SSE_PREFIX = "data: "
_SSE_DONE = "[DONE]"


def _native_message(message: PromptMessage) -> dict[str, object]:
    """Geçmişteki bir mesajın yerel biçimdeki karşılığı.

    Çağrı taşıyan asistan mesajı `tool_calls` alanıyla gidiyor, `content` içinde metin
    olarak değil. Ölçülerek öğrenildi (Faz B/2): metin olarak yazıldığında model biçimi
    kendi cevabına kopyalıyor ve kullanıcı `{"name": "volume", …}` duyuyor.

    `id` alanı zorunlu ve sunucudan geleni saklamıyoruz; sıra numarası yetiyor çünkü tek
    kullanıcısı aynı istekteki `tool` yanıtının eşleşmesi.
    """
    body: dict[str, object] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        body["tool_calls"] = [
            {
                "id": f"call_{index}",
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(dict(call.arguments), ensure_ascii=False),
                },
            }
            for index, call in enumerate(message.tool_calls)
        ]
    return body


def _arguments(service: str, pieces: Sequence[str]) -> dict[str, Any]:
    """Parça parça gelen argüman JSON'ını birleştirip ayrıştırır.

    Argümanlar akışta bölünerek geliyor; birleştirilmeden ayrıştırılamıyorlar. Bozuk
    JSON yutulmuyor (Kural 13) — sunucu çağrıyı kendi şablonuna göre üretti, ayrıştıramamak
    beklenen bir durum değil. Argümansız çağrı (`date_time`) boş sözlük, ve boş metin
    `json.loads` için hata olduğundan ayrıca ele alınıyor.
    """
    text = "".join(pieces).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ServiceFailedError(service, f"tool argümanları ayrıştırılamadı: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ServiceFailedError(service, "tool argümanları bir nesne değil")
    return parsed


_POST_ATTEMPTS = 2
"""Akışsız bir istek en fazla bu kadar denenir. İki: gözlenen arıza tek seferlikti ve
tekrarında geçti; daha fazlası, gerçekten düşmüş bir servisi turun içinde beklemek olurdu."""


@dataclass(frozen=True, slots=True)
class Sampling:
    """Üretimin örnekleme ayarları — **hepsi**, istek gövdesinde (bkz. modül başlığı).

    Varsayılan **açgözlü ve cezasız**: tek belirleyici `temperature`, geri kalanı etkisiz
    değere sabitlenmiş. Gerekçe alan alan değil, küme olarak yazılıyor çünkü tek tek
    yazılırsa on bir gerekçe yerine on bir tahmin okunur:

    - **Açgözlülük ölçümün varsayımı.** `docs/faz2-olcum.md`'den beri her sayı "aynı girdi
      aynı çıktıyı verir" kabulüyle okundu. `temperature=0` bunu tek başına sağlıyor;
      `top_k`/`top_p`/`min_p`/`typical_p`/`xtc`/`top_n_sigma` bir dağılımı buduyor ve
      budanmış bir dağılımın argmax'ı budanmamışınkiyle aynı. Yani **etkisiz değere
      sabitlendiler, seçilmediler**: burada bir örnekleme kararı yok, bir sunucu bayrağının
      sessizce karar vermesine kapatılan bir kapı var.
    - **Cezalar açgözlü üretimde bile etkili** ve tek gerçek değişiklik onlar:
      `presence_penalty` sunucuda 1.5 açıktı, yani üretimin ve bütün eski ölçümlerin
      arkasında kimsenin seçmediği bir sayı vardı. Sıfırlanması **ölçülecek bir değişiklik**
      (Faz A'nın tekrar oynatma aracı `--ceza` ile ikisini yan yana koyuyor); "1.5 yanlıştı"
      değil, "seçilmemişti" deniyor.
    - **`mirostat` bir kapı, bir ayar değil:** açıkken sıcaklık yok sayılır, yani sunucuda
      açık unutulmuş bir `--mirostat`, `temperature=0`'ı sessizce iptal ederdi.

    §19'da örnekleme maddesi yok; bu bir `main.py` işletim değeri gibi okunmalı — burada
    duruyor çünkü tek okuyucusu istek gövdesi.
    """

    temperature: float = 0.0
    top_k: int = 0
    top_p: float = 1.0
    min_p: float = 0.0
    typical_p: float = 1.0
    top_n_sigma: float = -1.0
    xtc_probability: float = 0.0
    repeat_penalty: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    dry_multiplier: float = 0.0
    mirostat: int = 0

    def body(self) -> dict[str, object]:
        """İstek gövdesine giren alanlar. Alan adları llama.cpp'nin adlarıyla birebir."""
        return dict(asdict(self))


GREEDY = Sampling()
"""Varsayılan örnekleme. Adı var çünkü varsayılan bir argümanda çağrı yapılamıyor ve
adsız bir `Sampling()` her istekte "hangi ayarlar" sorusunu cevapsız bırakırdı."""


class LlamaCppLLM:
    """`llama-server` arkasındaki LLM.

    İstemci dışarıdan veriliyor: bağlantı havuzu ve zaman aşımı çağıranın elinde kalsın,
    testte gerçek ağa çıkmadan taşıma değiştirilebilsin diye (`ToolContext.http` ile aynı
    gerekçe).
    """

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        name: str = "llama.cpp",
        sampling: Sampling = GREEDY,
    ) -> None:
        self._http = http
        self._name = name
        self._sampling = sampling

    @property
    def name(self) -> str:
        return self._name

    @property
    def sampling(self) -> Sampling:
        """Rapor bunu yazıyor: hangi ayarların **istekten**, hangilerinin sunucudan
        geldiği okunabilmeli (bkz. modül başlığı)."""
        return self._sampling

    async def health(self) -> bool:
        try:
            response = await self._http.get("/health")
        except httpx.HTTPError:
            return False
        return response.status_code == httpx.codes.OK

    async def count_tokens(self, text: str) -> int:
        """Kural 10: sayı sunucunun sayacından gelir, tahmin edilmez."""
        payload = await self._post("/tokenize", {"content": text})
        tokens = payload.get("tokens")
        if not isinstance(tokens, list):
            raise ServiceFailedError(self._name, "/tokenize beklenmedik bir yanıt verdi")
        return len(tokens)

    async def context_size(self) -> int:
        """`/props`'tan `n_ctx` (§11.1). Sunucu hangi `-c` ile açıldıysa o.

        Yanıtın biçimi llama.cpp sürümleri arasında gezindi; iki yer de deneniyor ve
        hiçbiri yoksa hata yükseliyor — bir varsayılana düşmek, bütçeyi gerçek bağlamdan
        değil bir tahminden türetmek olurdu (Kural 10, Kural 13).
        """
        payload = await self._get("/props")
        settings = payload.get("default_generation_settings")
        size = settings.get("n_ctx") if isinstance(settings, dict) else payload.get("n_ctx")
        if not isinstance(size, int) or size < 1:
            raise ServiceFailedError(self._name, "/props bağlam boyutunu bildirmedi")
        return size

    async def server_sampling(self) -> Sampling:
        """Sunucunun kendi örnekleme ayarları, `/props`'tan (2026-08-16, sahibin kararı).

        **Değerler llama'nın, ama istekte gidiyorlar** — ve ayrımın tamamı bu. Modelin
        önerilen parametreleri var ve sunucu onlarla açılıyor; onları açgözlü değerlerle
        ezmek, modeli tasarlandığı ayarların dışında koşturmak olurdu. Ama Faz A'nın
        bulgusu da duruyor: bayrakta kalan bir sayı görünmez, ve iki rapor
        karşılaştırılırken karşılaştırılan şeyin bir bayrak seti olduğunu kimse fark
        etmez (`evals/report.py` bunu `presence_penalty` 1.5/0 ayrışmasıyla yakalamıştı).
        Sorulup isteğe yazılınca ikisi birden sağlanıyor: değer sunucunun, kayıt bizim.

        `context_size()` ile **aynı gerekçe**: yapılandırmadan okunan bir kopya, sunucu
        başka bir bayrakla açıldığı gün sessizce ayrışır.

        **Ölçüm bunu kullanmıyor ve bu bilinçli:** `evals` açgözlü kalıyor
        (`Sampling()` varsayılanı), çünkü `docs/faz2-olcum.md`'den beri her sayı "aynı
        girdi aynı çıktıyı verir" kabulüyle okundu — oturum ölçümünün üç koşuda birebir
        aynı çıkması bugün 12/15'in gürültü olmadığını böyle söyledi. Yani üretim ile
        ölçüm bu tek eksende **bilerek** ayrı; raporun `SAMPLERS` bölümü hangisiyle
        koşulduğunu yazıyor. Bir karar üretimin örneklemesine bağlıysa, kapı tekrarla
        koşulur.
        """
        payload = await self._get("/props")
        settings = payload.get("default_generation_settings")
        outer: dict[str, object] = settings if isinstance(settings, dict) else {}
        inner = outer.get("params")
        # Biçim llama.cpp sürümleri arasında geziniyor, `context_size()` ile aynı sebep.
        params: dict[str, object] = inner if isinstance(inner, dict) else outer
        known = {field.name for field in fields(Sampling)}
        values = {k: v for k, v in params.items() if k in known and isinstance(v, int | float)}
        if not values:
            # Kural 13: sessiz varsayılana düşmek, üretimin hangi ayarlarla koştuğunu
            # bilmemek demek — bu yöntemin var olma sebebinin tam tersi.
            raise ServiceFailedError(self._name, "/props örnekleme ayarlarını bildirmedi")
        return Sampling(**values)  # type: ignore[arg-type]

    async def stream_native(
        self,
        messages: Sequence[PromptMessage],
        *,
        tools: Sequence[dict[str, object]],
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str | NativeCall]:
        """Modelin **kendi** tool-calling şablonuyla üretim (2026-08-16, Faz B ölçümü).

        `stream()`'in kardeşi, iki farkla: katalog istek gövdesinin `tools` alanından
        gidiyor (sistem promptundan değil) ve çağrıyı **sunucu** ayrıştırıyor. Gramer
        yok; olsaydı şablonun kendi çağrı sözdizimini ikinci bir kısıtla ezerdi.

        Metin parçaları `str`, çağrılar `NativeCall` olarak akıyor — `agent/loop.py`'nin
        `_generate`'iyle aynı kalıp. **İkisi aynı yanıtta gelebilir**, ve bu yöntemin var
        olma sebebi tam olarak bu: bugünkü gramerde model ya konuşuyor ya çağırıyor, ve
        ikisini birden isteyince çağrıyı düz metin içinde taklit ediyor (`tools/schema.py`).

        **Bugün yalnızca `evals` çağırıyor.** `LLMClient` arayüzünde değil: arayüzü
        ölçüm sonuçlanmadan genişletmek, alınmamış bir kararı imzaya yazmak olurdu.
        """
        body: dict[str, object] = {
            "messages": [_native_message(m) for m in messages],
            "stream": True,
            "tools": list(tools),
            **self._sampling.body(),
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        pending: dict[int, list[str]] = {}
        names: dict[int, str] = {}
        async for payload in self._events(body):
            delta = payload.get("choices", [{}])[0].get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str) and content:
                yield content
            for item in delta.get("tool_calls") or []:
                index = item.get("index", 0)
                function = item.get("function") or {}
                if function.get("name"):
                    names[index] = function["name"]
                    pending.setdefault(index, [])
                if function.get("arguments"):
                    pending.setdefault(index, []).append(function["arguments"])
        for index, name in names.items():
            yield NativeCall(name=name, arguments=_arguments(self._name, pending[index]))

    async def stream(
        self,
        messages: Sequence[PromptMessage],
        *,
        grammar: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str]:
        body: dict[str, object] = {
            # `_native_message` burada da kullanılıyor: metin biçimlerinde `tool_calls`
            # zaten boş, ama yerel biçimin **kapanış üretimi** bu yoldan geçiyor ve
            # geçmişteki çağrı düşerse ardındaki `tool` mesajı sahipsiz kalırdı.
            "messages": [_native_message(m) for m in messages],
            "stream": True,
            "reasoning_format": "none",
            # Örnekleme ayarlarının **tamamı** burada, sunucunun açılış bayrağında değil:
            # gerekçesi `Sampling`'de ve modül başlığında.
            **self._sampling.body(),
        }
        if grammar is not None:
            body["grammar"] = grammar
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        #print("LLM REQUEST GRAMMAR:", repr(body.get("grammar")))

        async for payload in self._events(body):
            content = payload.get("choices", [{}])[0].get("delta", {}).get("content")
            if isinstance(content, str) and content:
                yield content
        # async for payload in self._events(body):
        #     print("LLM PAYLOAD:", repr(payload))

        #     content = payload.get("choices", [{}])[0].get("delta", {}).get("content")
        #     print("LLM CONTENT:", repr(content))

        #     if isinstance(content, str) and content:
        #         yield content


    async def _events(self, body: dict[str, object]) -> AsyncGenerator[dict[str, Any]]:
        """SSE karelerini ayrıştırılmış olarak akıtır. İki akış yöntemi de buradan
        besleniyor: bağlantı kurma, durum kodu ve bozuk JSON kuralları tek yerde.

        Boş satır ve `[DONE]` normaldir; bozuk JSON değildir ve yutulmaz (Kural 13).
        Seçeneksiz kareler (`usage` gibi) geçerlidir ve olduğu gibi geçiyor — okuyan
        taraf ne aradığını biliyor.
        """
        log.info("LLAMACPP ISTEK", body_json=json.dumps(body, ensure_ascii=False))
        try:
            async with self._http.stream("POST", "/v1/chat/completions", json=body) as response:
                if response.status_code != httpx.codes.OK:
                    await response.aread()
                    raise ServiceFailedError(
                        self._name,
                        f"/v1/chat/completions {response.status_code} döndü:"
                        f" {response.text[:200]}",
                    )
                async for line in response.aiter_lines():
                    if not line.startswith(_SSE_PREFIX):
                        continue
                    data = line[len(_SSE_PREFIX) :].strip()
                    if not data or data == _SSE_DONE:
                        continue
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError as exc:
                        raise ServiceFailedError(
                            self._name, f"akışta bozuk JSON: {exc}"
                        ) from exc
                    if payload.get("choices"):
                        yield payload
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError(self._name, f"akış kesildi: {exc}") from exc

    async def _post(self, path: str, body: dict[str, object]) -> dict[str, object]:
        return self._decode(path, await self._post_once(path, body))

    async def _get(self, path: str) -> dict[str, object]:
        try:
            response = await self._http.get(path)
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError(self._name, f"{path}: ulaşılamadı: {exc}") from exc
        return self._decode(path, response)

    def _decode(self, path: str, response: httpx.Response) -> dict[str, object]:
        if response.status_code != httpx.codes.OK:
            raise ServiceFailedError(
                self._name, f"{path} {response.status_code} döndü: {response.text[:200]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ServiceFailedError(self._name, f"{path}: yanıt JSON değil") from exc
        if not isinstance(payload, dict):
            raise ServiceFailedError(self._name, f"{path}: yanıt bir nesne değil")
        return payload

    async def _post_once(self, path: str, body: dict[str, object]) -> httpx.Response:
        """Taşıma koptuğunda sınırlı yeniden deneme. Yalnızca `TransportError`: yanıt veren
        bir sunucunun hatası tekrarlanmaz, yukarı taşınır (§14)."""
        for attempt in range(1, _POST_ATTEMPTS + 1):
            try:
                return await self._http.post(path, json=body)
            except httpx.TransportError as exc:
                if attempt == _POST_ATTEMPTS:
                    raise ServiceUnavailableError(
                        self._name, f"{path}: ulaşılamadı ({attempt} deneme): {exc}"
                    ) from exc
                log.warning("taşıma koptu, yeniden deneniyor", path=path, attempt=attempt)
            except httpx.HTTPError as exc:
                raise ServiceUnavailableError(
                    self._name, f"{path}: ulaşılamadı: {exc}"
                ) from exc
        raise AssertionError("erişilemez")
