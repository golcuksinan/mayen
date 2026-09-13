"""Adaptör sözleşmeleri ve sahte uygulamaları (P3).

Testlerin ilki bir çalışma anı testi değil: aşağıdaki dört atama, sahtelerin `Protocol`'e
uyduğunu **mypy'a** doğrulatır. Uymazlarsa `uv run mypy` kırılır ve bu, P3'ün bitti
kriterlerinden biri.
"""

import asyncio

import pytest

from mayen.adapters.audio import Audio, AudioFormat, Codec
from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.fakes.speaker import FakeSpeaker
from mayen.adapters.fakes.stt import FakeSTT
from mayen.adapters.fakes.tts import FakeTTS
from mayen.adapters.llm import LLMClient, PromptMessage
from mayen.adapters.service import ModelService
from mayen.adapters.speaker import SpeakerClient
from mayen.adapters.stt import STTClient
from mayen.adapters.tts import TTSClient

_llm: LLMClient = FakeLLM()
_stt: STTClient = FakeSTT()
_tts: TTSClient = FakeTTS()
_speaker: SpeakerClient = FakeSpeaker()

FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)


def segment(text: str) -> Audio:
    return Audio(format=FORMAT, data=text.encode("utf-8"))


def test_every_fake_is_a_model_service() -> None:
    for fake in (FakeLLM(), FakeSTT(), FakeTTS(), FakeSpeaker()):
        assert isinstance(fake, ModelService)


async def test_llm_streams_queued_response_in_chunks() -> None:
    llm = FakeLLM(["merhaba dünya"], chunk_size=4)
    chunks = [chunk async for chunk in llm.stream([PromptMessage("user", "selam")])]
    assert "".join(chunks) == "merhaba dünya"
    assert len(chunks) > 1


async def test_llm_records_what_it_was_sent() -> None:
    """Sabit önek kuralı (§8.1) ancak modele giden mesajlara bakılarak test edilebilir."""
    llm = FakeLLM(["tamam"])
    prefix = (PromptMessage("system", "sistem"), PromptMessage("user", "soru"))
    async for _ in llm.stream(prefix, grammar="root ::= .+"):
        pass
    assert llm.calls == [prefix]
    assert llm.grammars == ["root ::= .+"]


async def test_llm_stream_is_cancellable_midway() -> None:
    """Kural 12: her aşama iptal edilebilir. Üreteci kapatmak üretimi durdurur."""
    llm = FakeLLM(["bir hayli uzun bir yanıt metni"], chunk_size=1)
    stream = llm.stream([PromptMessage("user", "selam")])
    first = await anext(stream)
    await stream.aclose()
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    assert first == "b"


async def test_llm_counts_tokens_deterministically() -> None:
    llm = FakeLLM()
    assert await llm.count_tokens("bir iki üç") == 3
    assert await llm.count_tokens("bir iki üç") == 3


async def test_stt_prefers_the_queued_transcript() -> None:
    stt = FakeSTT(["hava nasıl"])
    result = await stt.transcribe(segment("ham ses"))
    assert result.text == "hava nasıl"
    assert result.language == "tr"


async def test_stt_falls_back_to_reading_the_payload_as_text() -> None:
    """P1'in ertelenmiş STT kararı: gerçek STT gelmeden uçtan uca yazışılabilir."""
    stt = FakeSTT()
    assert (await stt.transcribe(segment("yarın hava nasıl"))).text == "yarın hava nasıl"


async def test_stt_refuses_real_pcm_with_a_legible_error() -> None:
    """Ses kipinde yükün metin olmadığı ilk yer burası: `UnicodeDecodeError` yerine
    servisin adını ve §19.2'yi taşıyan bir hata."""
    stt = FakeSTT()
    with pytest.raises(ServiceUnavailableError, match=r"§19\.2"):
        await stt.transcribe(Audio(data=b"\xff\xfe\x00\x01", format=FORMAT))


async def test_tts_output_is_readable_and_ordered() -> None:
    tts = FakeTTS(chunk_size=4)
    chunks = [chunk async for chunk in tts.synthesize("iki cümle")]
    # Sonda bir boşluk var: cümleler arka arkaya akıtıldığında ayıraç kalsın diye
    # (gerekçesi `adapters/fakes/tts.py`'de).
    assert b"".join(chunks).decode("utf-8") == "iki cümle "
    assert tts.calls == ["iki cümle"]


async def test_speaker_embedding_is_deterministic_and_normalized() -> None:
    speaker = FakeSpeaker()
    first = await speaker.embed(segment("ali"))
    again = await speaker.embed(segment("ali"))
    other = await speaker.embed(segment("veli"))
    assert first == again
    assert first != other
    assert sum(v * v for v in first.values) == pytest.approx(1.0)


async def test_unavailable_service_raises_instead_of_returning_empty() -> None:
    """Kural 13: sessizce yutulmuş bir hata, boş bir transkriptten ayırt edilemez."""
    stt = FakeSTT(available=False)
    assert await stt.health() is False
    with pytest.raises(ServiceUnavailableError):
        await stt.transcribe(segment("selam"))

    llm = FakeLLM(["tamam"], available=False)
    with pytest.raises(ServiceUnavailableError):
        await anext(llm.stream([PromptMessage("user", "selam")]))


def test_health_check_can_poll_every_service_through_one_type() -> None:
    """§14: core servisleri düzenli yoklar — dört ayrı tip tanıması gerekmeden."""
    services: list[ModelService] = [
        FakeLLM(),
        FakeSTT(),
        FakeTTS(),
        FakeSpeaker(available=False),
    ]
    healthy = asyncio.run(_poll(services))
    assert healthy == [True, True, True, False]


async def _poll(services: list[ModelService]) -> list[bool]:
    return list(await asyncio.gather(*(service.health() for service in services)))
