"""Kokoro adaptörü. Gerçek ağa çıkmaz, model yüklemez: HTTP `MockTransport` arkasında.

İlk atama bir çalışma anı testi değil — gerçek adaptörün de `TTSClient`'e uyduğunu mypy'a
doğrulatır (`test_adapters_llamacpp.py` ile aynı gerekçe).
"""

import json
from collections.abc import Callable

import httpx
import pytest

from mayen.adapters.errors import ServiceFailedError, ServiceUnavailableError
from mayen.adapters.kokoro import OUTPUT_FORMAT, KokoroTTS
from mayen.adapters.tts import TTSClient

_contract: TTSClient = KokoroTTS(httpx.AsyncClient())

Handler = Callable[[httpx.Request], httpx.Response]

HEALTHY = {
    "ok": True,
    "codec": "pcm16",
    "sample_rate": 16_000,
    "channels": 1,
}


def _client(handler: Handler) -> KokoroTTS:
    transport = httpx.MockTransport(handler)
    return KokoroTTS(httpx.AsyncClient(transport=transport, base_url="http://tts.invalid"))


async def _collect(tts: KokoroTTS, text: str) -> bytes:
    return b"".join([chunk async for chunk in tts.synthesize(text)])


async def test_health_is_true_when_the_service_answers() -> None:
    assert await _client(lambda request: httpx.Response(200, json=HEALTHY)).health() is True


async def test_health_is_false_when_the_service_is_down() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    assert await _client(handler).health() is False


async def test_health_is_false_before_the_model_is_loaded() -> None:
    """Ayakta ama henüz sentez yapamayan bir servis sağlıklı değildir."""
    payload = HEALTHY | {"ok": False}
    assert await _client(lambda request: httpx.Response(200, json=payload)).health() is False


async def test_health_is_false_when_the_service_reports_another_format() -> None:
    """Adaptörün bildirdiği biçim sabit; servis başka bir hızda üretiyorsa ses tiz ya da
    pes çıkar. Bu sessiz kalmıyor: sağlıksızlık sayılıp kayda geçiyor (Kural 13)."""
    payload = HEALTHY | {"sample_rate": 24_000}
    assert await _client(lambda request: httpx.Response(200, json=payload)).health() is False


async def test_output_format_matches_the_local_audio_format() -> None:
    """Yerelde tek bir ses biçimi var; adaptör onu bildiriyor."""
    from client.audio import FORMAT

    assert OUTPUT_FORMAT == FORMAT


async def test_synthesize_sends_the_text_and_streams_the_payload_back() -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/synthesize"
        seen.append(json.loads(request.content))
        return httpx.Response(200, content=b"\x01\x02\x03\x04")

    assert await _collect(_client(handler), "merhaba") == b"\x01\x02\x03\x04"
    assert seen == [{"text": "merhaba"}]


async def test_synthesize_raises_on_an_error_status() -> None:
    """§14: "servis hata döndürdü" yutulmaz, yukarı taşınır."""
    with pytest.raises(ServiceFailedError):
        await _collect(_client(lambda request: httpx.Response(500, text="patladı")), "merhaba")


async def test_synthesize_raises_when_the_service_is_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    with pytest.raises(ServiceUnavailableError):
        await _collect(_client(handler), "merhaba")


async def test_stream_is_cancellable_midway() -> None:
    """Kural 12: üreteci kapatmak yanıtı kapatır, servis de üretimini bırakır."""
    tts = _client(lambda request: httpx.Response(200, content=b"a" * 64))
    stream = tts.synthesize("merhaba")
    assert await anext(stream)
    await stream.aclose()
