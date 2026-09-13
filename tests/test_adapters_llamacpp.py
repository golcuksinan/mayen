"""`llama-server` adaptörü. Gerçek ağa çıkmaz: HTTP `MockTransport` arkasında.

İlk atama bir çalışma anı testi değil — gerçek adaptörün de `LLMClient`'e uyduğunu
mypy'a doğrulatır; sahteyle gerçeğin aynı sözleşmede olduğu ancak böyle bilinir.
"""

import json
from collections.abc import Callable, Iterable

import httpx
import pytest

from mayen.adapters.errors import ServiceFailedError, ServiceUnavailableError
from mayen.adapters.llamacpp import LlamaCppLLM, Sampling
from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage

_contract: LLMClient = LlamaCppLLM(httpx.AsyncClient())

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler) -> LlamaCppLLM:
    transport = httpx.MockTransport(handler)
    return LlamaCppLLM(httpx.AsyncClient(transport=transport, base_url="http://llm.invalid"))


def _sse(chunks: Iterable[str]) -> str:
    lines = []
    for chunk in chunks:
        frame = {"choices": [{"delta": {"content": chunk}}]}
        lines.append(f"data: {json.dumps(frame)}\n\n")
    lines.append("data: [DONE]\n\n")
    return "".join(lines)


async def test_health_is_true_when_the_server_answers() -> None:
    llm = _client(lambda request: httpx.Response(200, json={"status": "ok"}))
    assert await llm.health() is True


async def test_health_is_false_when_the_server_is_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    assert await _client(handler).health() is False


async def test_health_does_not_raise_on_an_error_status() -> None:
    """§14: yokluk normal bir cevap, istisna değil — yoklayıcı her turda yakalamasın."""
    llm = _client(lambda request: httpx.Response(503))
    assert await llm.health() is False


async def test_count_tokens_asks_the_server() -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/tokenize"
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"tokens": [1, 2, 3, 4]})

    assert await _client(handler).count_tokens("bir iki") == 4
    assert seen == [{"content": "bir iki"}]


async def test_count_tokens_refuses_an_unexpected_answer() -> None:
    llm = _client(lambda request: httpx.Response(200, json={"nope": True}))
    with pytest.raises(ServiceFailedError):
        await llm.count_tokens("bir")


async def test_count_tokens_separates_unreachable_from_failed() -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    with pytest.raises(ServiceUnavailableError):
        await _client(unreachable).count_tokens("bir")

    llm = _client(lambda request: httpx.Response(500, text="patladı"))
    with pytest.raises(ServiceFailedError):
        await llm.count_tokens("bir")


async def test_a_dropped_transport_is_retried_once() -> None:
    """P9: `/tokenize` bir kez `ReadError` ile koptu, tekrarı geçti. Gerçek turda turu
    öldüren hata; yeniden deneme onu yutmuyor, sadece bir şans daha veriyor."""
    attempts = 0

    def flaky(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadError("okuma koptu", request=request)
        return httpx.Response(200, json={"tokens": [1, 2, 3]})

    assert await _client(flaky).count_tokens("bir iki üç") == 3
    assert attempts == 2


async def test_a_persistent_transport_failure_still_raises() -> None:
    """Kural 13: deneme tükenince hata yükseliyor, sessizce sıfır dönmüyor."""
    attempts = 0

    def broken(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadError("okuma koptu", request=request)

    with pytest.raises(ServiceUnavailableError):
        await _client(broken).count_tokens("bir")
    assert attempts == 2


async def test_an_error_status_is_not_retried() -> None:
    """§14: yanıt veren bir sunucunun hatası tekrarlanmaz, yukarı taşınır."""
    attempts = 0

    def failing(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="patladı")

    with pytest.raises(ServiceFailedError):
        await _client(failing).count_tokens("bir")
    assert attempts == 1


async def test_stream_yields_the_deltas() -> None:
    llm = _client(lambda request: httpx.Response(200, text=_sse(["mer", "haba"])))
    chunks = [chunk async for chunk in llm.stream([PromptMessage("user", "selam")])]
    assert chunks == ["mer", "haba"]


async def test_stream_sends_the_grammar_and_the_messages() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        seen.update(json.loads(request.content))
        return httpx.Response(200, text=_sse(["tamam"]))

    llm = _client(handler)
    messages = [PromptMessage("system", "önek"), PromptMessage("user", "selam")]
    async for _ in llm.stream(messages, grammar="root ::= .+", max_tokens=64):
        pass

    assert seen["grammar"] == "root ::= .+"
    assert seen["max_tokens"] == 64
    assert seen["stream"] is True
    assert seen["messages"] == [
        {"role": "system", "content": "önek"},
        {"role": "user", "content": "selam"},
    ]


async def test_stream_pins_every_sampling_setting_in_the_request() -> None:
    """A4: örnekleme sunucunun açılış bayrağından değil, istekten geliyor.

    Tek tek değerler değil **eksiksizlik** sınanıyor: gönderilmeyen bir alan sunucudan
    gelir ve o gün sunucunun nasıl açıldığına bağlı bir sistem koşar. Eski hâlde yalnızca
    `temperature` gönderiliyordu ve `presence_penalty` 1.5'ti — kimsenin seçmediği bir sayı.
    """
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, text=_sse(["tamam"]))

    async for _ in _client(handler).stream([PromptMessage("user", "selam")]):
        pass

    assert seen.items() >= Sampling().body().items()
    assert seen["temperature"] == 0.0
    assert seen["presence_penalty"] == 0.0


async def test_sampling_can_be_overridden_for_a_measurement() -> None:
    """Tekrar oynatma aracı geçmişin ayarıyla koşabilmeli (`evals/replay.py --ceza`)."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, text=_sse(["tamam"]))

    llm = LlamaCppLLM(
        httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://llm.invalid"
        ),
        sampling=Sampling(presence_penalty=1.5),
    )
    async for _ in llm.stream([PromptMessage("user", "selam")]):
        pass

    assert seen["presence_penalty"] == 1.5
    assert llm.sampling.presence_penalty == 1.5


async def test_stream_omits_the_grammar_when_there_is_none() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, text=_sse(["tamam"]))

    async for _ in _client(handler).stream([PromptMessage("user", "selam")]):
        pass
    assert "grammar" not in seen


async def test_stream_ignores_frames_without_text() -> None:
    """`usage` gibi seçeneksiz kareler geçerlidir ve metin taşımazlar."""
    body = 'data: {"usage": {"completion_tokens": 3}}\n\n' + _sse(["tamam"])
    llm = _client(lambda request: httpx.Response(200, text=body))
    assert [chunk async for chunk in llm.stream([PromptMessage("user", "s")])] == ["tamam"]


async def test_stream_does_not_swallow_broken_json() -> None:
    llm = _client(lambda request: httpx.Response(200, text="data: {bozuk\n\n"))
    with pytest.raises(ServiceFailedError):
        async for _ in llm.stream([PromptMessage("user", "selam")]):
            pass


async def test_stream_reports_an_error_status() -> None:
    llm = _client(lambda request: httpx.Response(400, text="gramer geçersiz"))
    with pytest.raises(ServiceFailedError):
        async for _ in llm.stream([PromptMessage("user", "selam")]):
            pass


async def test_stream_reports_an_unreachable_server() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    with pytest.raises(ServiceUnavailableError):
        async for _ in _client(handler).stream([PromptMessage("user", "selam")]):
            pass


async def test_context_size_comes_from_the_server() -> None:
    """§11.1: bütçe modelin **gerçek** bağlam boyutundan türetilir; sayı sorulur."""
    llm = _client(
        lambda request: httpx.Response(
            200, json={"default_generation_settings": {"n_ctx": 49152}}
        )
    )
    assert await llm.context_size() == 49152


async def test_context_size_reads_the_flat_field_too() -> None:
    """Yanıtın biçimi llama.cpp sürümleri arasında gezindi."""
    llm = _client(lambda request: httpx.Response(200, json={"n_ctx": 8192}))
    assert await llm.context_size() == 8192


async def test_a_missing_context_size_is_not_guessed() -> None:
    """Varsayılana düşmek, bütçeyi bir tahminden türetmek olurdu (Kural 10, Kural 13)."""
    llm = _client(lambda request: httpx.Response(200, json={"nope": True}))
    with pytest.raises(ServiceFailedError):
        await llm.context_size()


async def test_server_sampling_is_read_from_props() -> None:
    """Değerler sunucunun, kayıt bizim (2026-08-16, sahibin kararı).

    Modelin önerilen parametreleri var ve sunucu onlarla açılıyor; açgözlü değerlerle
    ezmek modeli tasarlandığı ayarların dışında koşturmak olurdu. Ama sayılar yine de
    isteğe yazılıyor, çünkü bayrakta kalan bir sayı görünmez (Faz A).
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "default_generation_settings": {
                    "n_ctx": 16384,
                    "params": {"temperature": 0.7, "top_k": 20, "top_p": 0.8},
                }
            },
        )

    sampling = await _client(handler).server_sampling()
    assert sampling.temperature == 0.7
    assert sampling.top_k == 20
    assert sampling.top_p == 0.8
    # Bildirilmeyen alanlar `Sampling`'in kendi varsayılanında kalır, uydurulmaz.
    assert sampling.mirostat == 0


async def test_server_sampling_reads_the_flat_shape_too() -> None:
    """Yanıt biçimi llama.cpp sürümleri arasında geziniyor — `context_size()` ile aynı."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"default_generation_settings": {"temperature": 0.6, "top_k": 40}}
        )

    sampling = await _client(handler).server_sampling()
    assert (sampling.temperature, sampling.top_k) == (0.6, 40)


async def test_server_sampling_fails_loudly_rather_than_falling_back() -> None:
    """Sessizce açgözlüye düşmek, üretimin hangi ayarlarla koştuğunu bilmemek olurdu —
    yani bu yöntemin var olma sebebinin tersi (Kural 13)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"default_generation_settings": {"n_ctx": 16384}})

    with pytest.raises(ServiceFailedError):
        await _client(handler).server_sampling()


def _native_sse(frames: Iterable[dict[str, object]]) -> str:
    lines = [f"data: {json.dumps({'choices': [{'delta': frame}]})}\n\n" for frame in frames]
    lines.append("data: [DONE]\n\n")
    return "".join(lines)


async def test_native_stream_sends_the_tools_and_no_grammar() -> None:
    """Yerel biçimde katalog `tools` alanından gidiyor; gramer gönderilirse şablonun kendi
    çağrı sözdizimini ikinci bir kısıt ezerdi."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, text=_native_sse([{"content": "tamam"}]))

    tools: list[dict[str, object]] = [{"type": "function", "function": {"name": "date_time"}}]
    async for _ in _client(handler).stream_native([PromptMessage("user", "saat")], tools=tools):
        pass

    assert seen["tools"] == tools
    assert "grammar" not in seen


async def test_native_stream_yields_text_and_the_call_together() -> None:
    """Ölçümün asıl konusu: model aynı yanıtta hem konuşabiliyor hem çağırabiliyor.
    Bugünkü gramerde bu imkânsız ve model çağrıyı düz metin içinde taklit ediyor."""
    frames: list[dict[str, object]] = [
        {"content": "Bakıyorum."},
        {"tool_calls": [{"index": 0, "function": {"name": "weather", "arguments": '{"ci'}}]},
        {"tool_calls": [{"index": 0, "function": {"arguments": 'ty": "Denizli"}'}}]},
    ]
    llm = _client(lambda request: httpx.Response(200, text=_native_sse(frames)))
    events = [
        event async for event in llm.stream_native([PromptMessage("user", "hava")], tools=[])
    ]

    assert events[0] == "Bakıyorum."
    assert events[1] == NativeCall(name="weather", arguments={"city": "Denizli"})


async def test_a_call_with_no_arguments_is_an_empty_mapping() -> None:
    """`date_time` argümansız; boş metin `json.loads` için hatadır ve ayrıca ele alınıyor."""
    frames: list[dict[str, object]] = [
        {"tool_calls": [{"index": 0, "function": {"name": "date_time", "arguments": ""}}]}
    ]
    llm = _client(lambda request: httpx.Response(200, text=_native_sse(frames)))
    events = [
        event async for event in llm.stream_native([PromptMessage("user", "saat")], tools=[])
    ]

    assert events == [NativeCall(name="date_time", arguments={})]


async def test_broken_call_arguments_are_not_swallowed() -> None:
    """Kural 13: sunucu çağrıyı kendi şablonuna göre üretti; ayrıştıramamak beklenen bir
    durum değil ve sessizce argümansız bir çağrıya dönüşmemeli."""
    frames: list[dict[str, object]] = [
        {"tool_calls": [{"index": 0, "function": {"name": "weather", "arguments": "{bozuk"}}]}
    ]
    llm = _client(lambda request: httpx.Response(200, text=_native_sse(frames)))
    with pytest.raises(ServiceFailedError):
        async for _ in llm.stream_native([PromptMessage("user", "hava")], tools=[]):
            pass
