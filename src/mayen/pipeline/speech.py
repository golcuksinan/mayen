"""STT ve TTS model servislerinin istemcileri (§3): model çekirdekte yüklenmez (§18).

Servisle konuşma `ports.speech` sözleşmesidir. Açılışta servis biçimini bildirir; bildirilen
biçim bekleneni tutmazsa birim kalıcı hatayla düşer (§14): sessiz bir uyuşmazlık "asistan
ince sesle konuşuyor" diye duyulur.

TTS'e giden metindeki dil işaretini (`<tr>…</tr>`) model koyar (§7); burada yalnızca okunur ve
parçalara bölünür, dili yorumlanmaz (§2.1). Ses birimine çevirmek sesin işidir, servistedir.
"""

import re
from collections.abc import AsyncGenerator, Callable, Mapping
from typing import Any

import aiohttp
from pipecat.audio.utils import create_stream_resampler
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    ErrorFrame,
    Frame,
    StartFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
)
from pipecat.services.settings import STTSettings, TTSSettings
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.services.tts_service import TTSService
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601

from mayen.ports.speech import (
    HEALTH,
    SPEAK,
    TRANSCRIBE,
    Health,
    Part,
    SpeechContractError,
    parse_health,
    parse_transcription,
    speak_request,
)

TAG = re.compile(r"<(/?)([a-z]{2})>")

# Akıştaki parça boyutu; ilk sesi geciktirmeyecek kadar küçük.
_CHUNK = 4096


def split_parts(text: str, open_tag: str | None) -> tuple[list[Part], str | None]:
    """Metni dil parçalarına böler; açık kalan işaret sonraki cümleye taşınır.

    Cümle bölücü bir işareti iki cümleye bölebilir; ikinci cümle işaretin içinde başlar.
    """
    parts: list[Part] = []
    position = 0
    for m in TAG.finditer(text):
        if m.start() > position:
            parts.append(Part(open_tag, text[position : m.start()]))
        open_tag = None if m.group(1) else m.group(2)
        position = m.end()
    if position < len(text):
        parts.append(Part(open_tag, text[position:]))
    return [p for p in parts if p.text.strip()], open_tag


async def _health(http: aiohttp.ClientSession, url: str) -> Health:
    async with http.get(url + HEALTH) as r:
        r.raise_for_status()
        return parse_health(await r.json())


class ServiceSTT(SegmentedSTTService):
    """Sözün sesi bittiğinde STT servisine gider; metin ve skor döner."""

    def __init__(self, url: str, language: str | None, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(settings=STTSettings(model=None, language=None), **kwargs)
        self._url = url.rstrip("/")
        self._language = language  # dinleme dili; çıkış dilinden bağımsız (§8.6)
        self._http: aiohttp.ClientSession | None = None
        self._rate = 0
        self._resampler = create_stream_resampler()

    @property
    def wants_wav_segments(self) -> bool:
        return False

    async def start(self, frame: StartFrame) -> None:
        await super().start(frame)
        self._http = aiohttp.ClientSession()
        try:
            self._rate = (await _health(self._http, self._url)).sample_rate
        except (aiohttp.ClientError, SpeechContractError) as e:
            await self.push_error(f"STT service: {e}", e, force_treat_as_permanent=True)

    async def stop(self, frame: EndFrame) -> None:
        await super().stop(frame)
        await self._close()

    async def cancel(self, frame: CancelFrame) -> None:
        await super().cancel(frame)
        await self._close()

    async def _close(self) -> None:
        if self._http is not None:
            await self._http.close()
            self._http = None

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame]:
        if self._http is None or not self._rate:
            yield ErrorFrame("STT service is not available")
            return
        await self.start_processing_metrics()
        pcm = await self._resampler.resample(audio, self.sample_rate, self._rate)
        params = {} if self._language is None else {"language": self._language}
        try:
            async with self._http.post(self._url + TRANSCRIBE, data=pcm, params=params) as r:
                if r.status != 200:
                    yield ErrorFrame(f"STT service {r.status}: {await r.text()}")
                    return
                result = parse_transcription(await r.json())
        except (aiohttp.ClientError, SpeechContractError) as e:
            yield ErrorFrame(f"STT service: {e}")
            return
        finally:
            await self.stop_processing_metrics()
        text = result.text.strip()
        if not text:
            return
        try:
            language: Language | None = Language(result.language)
        except ValueError:
            language = None
        yield TranscriptionFrame(
            text, self._user_id, time_now_iso8601(), language=language, result=result
        )


class ServiceTTS(TTSService):
    """Cümleyi TTS servisine verir, gelen sesi geldikçe çalar.

    Ses, cevabın dilinden seçilir (§16.3): dil her cümlede sorulur, çünkü aynı oturumda
    sıradaki tur başka birinin olabilir.
    """

    def __init__(
        self,
        url: str,
        voices: Mapping[str, str],
        language: Callable[[], str],
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(
            push_start_frame=True,
            push_stop_frames=True,
            settings=TTSSettings(model=None, voice=None, language=None),
            **kwargs,
        )
        self._url = url.rstrip("/")
        self._voices = dict(voices)
        self._language = language
        self._http: aiohttp.ClientSession | None = None
        self._rate = 0
        self._resampler = create_stream_resampler()
        self._context: str | None = None
        self._open: str | None = None

    def can_generate_metrics(self) -> bool:
        return True

    async def start(self, frame: StartFrame) -> None:
        await super().start(frame)
        self._http = aiohttp.ClientSession()
        try:
            health = await _health(self._http, self._url)
        except (aiohttp.ClientError, SpeechContractError) as e:
            await self.push_error(f"TTS service: {e}", e, force_treat_as_permanent=True)
            return
        missing = sorted(set(self._voices.values()) - set(health.voices))
        if missing:
            await self.push_error(
                f"TTS service has no voice {missing}", force_treat_as_permanent=True
            )
            return
        self._rate = health.sample_rate

    async def stop(self, frame: EndFrame) -> None:
        await super().stop(frame)
        await self._close()

    async def cancel(self, frame: CancelFrame) -> None:
        await super().cancel(frame)
        await self._close()

    async def _close(self) -> None:
        if self._http is not None:
            await self._http.close()
            self._http = None

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame]:
        if context_id != self._context:
            # Yeni cevap: önceki cevabın açık kalan işareti buna taşınmaz.
            self._context, self._open = context_id, None
        parts, self._open = split_parts(text, self._open)
        if not parts:
            # Cümle bölücü bir işareti tek başına bırakabilir ("</tr>"); okunacak bir şey yok.
            return
        if self._http is None or not self._rate:
            yield ErrorFrame("TTS service is not available")
            return
        language = self._language()
        voice = self._voices.get(language)
        if voice is None:
            yield ErrorFrame(f"no TTS voice for language {language!r}")
            return
        await self.start_tts_usage_metrics(text)
        try:
            request = speak_request(voice, parts)
            async with self._http.post(self._url + SPEAK, json=request) as r:
                if r.status != 200:
                    yield ErrorFrame(f"TTS service {r.status}: {await r.text()}")
                    return
                rest = b""
                async for chunk in r.content.iter_chunked(_CHUNK):
                    await self.stop_ttfb_metrics()
                    # Parça bir örneğin ortasında bölünebilir; yarım bayt sonrakine kalır.
                    data = rest + chunk
                    whole = len(data) - len(data) % 2
                    rest = data[whole:]
                    audio = await self._resampler.resample(
                        data[:whole], self._rate, self.sample_rate
                    )
                    yield TTSAudioRawFrame(
                        audio=audio,
                        sample_rate=self.sample_rate,
                        num_channels=1,
                        context_id=context_id,
                    )
        except aiohttp.ClientError as e:
            yield ErrorFrame(f"TTS service: {e}")
        finally:
            await self.stop_ttfb_metrics()
