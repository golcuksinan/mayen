"""STT, TTS ve konuşmacı model servislerinin istemcileri (§3): model çekirdekte yüklenmez (§18).

Servisle konuşma `ports.speech` sözleşmesidir. Açılışta servis biçimini bildirir; bildirilen
biçim bekleneni tutmazsa birim kalıcı hatayla düşer (§14): sessiz bir uyuşmazlık "asistan
ince sesle konuşuyor" diye duyulur.

Sözün başı ve sonu olasılıktan Pipecat'in VAD kuralıyla çıkar (eşik, başlama ve bitiş süreleri);
olasılığı veren model STT servisindedir (`ServiceVAD`). Sözün bittiğine dair olasılık da
oradadır (`ServiceTurn`); eşik ve sessizlik süresi Pipecat'in Smart Turn kuralıdır.

VAD sözü her kısa sessizlikte keser; bu kesim sözün bittiğini anlamak içindir. Yazıya dökme ve
konuşmacı tanıma kesik parçayla değil turun bütün sesiyle yapılır (§6): `TurnEndSignal` Smart
Turn'ün kararını STT'ye yayar, `ServiceSTT` turun sesini o ana kadar biriktirir.

TTS'e giden metindeki dil işaretini (`<tr>…</tr>`) model koyar (§7); burada yalnızca okunur ve
parçalara bölünür, dili yorumlanmaz (§2.1). Ses birimine çevirmek sesin işidir, servistedir.
"""

import asyncio
import json
import logging
import re
import time
import urllib.error
import urllib.request
import wave
from collections.abc import AsyncGenerator, Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import numpy as np
from pipecat.audio.turn.smart_turn.base_smart_turn import (
    BaseSmartTurn,
    SmartTurnTimeoutException,
)
from pipecat.audio.utils import create_stream_resampler
from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    ErrorFrame,
    Frame,
    InputAudioRawFrame,
    StartFrame,
    SystemFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.settings import STTSettings, TTSSettings
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService
from pipecat.transcriptions.language import Language
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.utils.time import time_now_iso8601
from websockets.exceptions import WebSocketException
from websockets.sync.client import ClientConnection, connect

from mayen.ports.speech import (
    EMBED,
    HEALTH,
    SPEAK,
    TRANSCRIBE,
    TURN,
    VAD,
    VAD_FRAME,
    WORD_ENDS,
    Embedding,
    Health,
    Part,
    SpeechContractError,
    parse_embedding,
    parse_health,
    parse_stream_hello,
    parse_transcription,
    parse_turn,
    speak_request,
)

log = logging.getLogger(__name__)

# Sözün ses izi (`Embedding`) ya da çıkarılamadıysa `None`; konuşmacı servisi bağlıysa her
# sözün karesinde bulunur. İzden kişiye karar çekirdektedir (`pipeline/speaker.py`).
VOICE = "mayen.voice"
# İzin çıkarıldığı sesin süresi (sn); turun sözleri birlikte tanınırken ağırlığıdır.
VOICE_S = "mayen.voice_s"

TAG = re.compile(r"<(/?)([a-z]{2})>")

# Akıştaki parça boyutu; ilk sesi geciktirmeyecek kadar küçük.
_CHUNK = 4096

# Söz başlamadan önce tutulan ses: VAD sözü geç fark eder (Pipecat'in parçalı STT'sindeki pay).
_PRE_SPEECH_S = 1.0
# Sesin sonuna eklenen sessizlik; ani biten seste model son kelimeyi düşürür (Pipecat'in payı).
_TRAILING_SILENCE_S = 0.5
# Tur dışında biten söz bu kadar bekler: wake word turu sözün bitişinden biraz sonra açar ve
# "Hey Mayen" parçası turun başı olur.
_JOIN_TURN_S = 1.0


class TurnEndSignal(SystemFrame):
    """Smart Turn sözün bittiğine karar verdi; STT turun sesini şimdi yazıya döker."""


class TurnEndToStt(TurnAnalyzerUserTurnStopStrategy):  # type: ignore[no-untyped-call]  # Pipecat'te tipsiz
    """Pipecat'in Smart Turn stratejisi; karar verince STT'ye `TurnEndSignal` yayar.

    Strateji turu bitirmek için metni bekler; metin, işareti alan STT'den gelir. Karar
    Pipecat'in iki yolundan (sessizlik ve model) aynı noktada toplanır.
    """

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self._signalled = False

    async def process_frame(self, frame: Frame) -> Any:  # noqa: ANN401  # ProcessFrameResult
        if isinstance(frame, VADUserStartedSpeakingFrame):
            self._signalled = False  # söz sürüyor; önceki karar geçersiz (Pipecat de atar)
        return await super().process_frame(frame)

    async def handle_user_turn_started(self) -> None:
        self._signalled = False
        await super().handle_user_turn_started()  # type: ignore[no-untyped-call]  # tipsiz

    async def _maybe_trigger_user_turn_stopped(self) -> None:
        # Pipecat 1.12.0'da kararın toplandığı tek yer (sürüm sabit, §3).
        if self._turn_complete and not self._signalled:
            self._signalled = True
            await self.broadcast_frame(TurnEndSignal)
        await super()._maybe_trigger_user_turn_stopped()  # type: ignore[no-untyped-call]  # tipsiz


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


def _record(directory: Path, pcm: bytes, sample_rate: int, text: str) -> None:
    """Sözün sesi `<zaman>.wav`, metni yanında `<zaman>.txt`; adı yerel zamandır."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        stem = directory / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        with wave.open(str(stem.with_suffix(".wav")), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm)
        stem.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
    except OSError as e:
        log.error("recording the words: %s", e)  # kayıt düşse de söz yazıya dökülmüş olur


async def _health(http: aiohttp.ClientSession, url: str) -> Health:
    async with http.get(url + HEALTH) as r:
        r.raise_for_status()
        return parse_health(await r.json())


class ServiceVAD(VADAnalyzer):
    """Her parçanın konuşma olasılığını STT servisindeki modelden alır (§18: çekirdek model
    yüklemez); olasılığı söze çeviren kural Pipecat'in `VADAnalyzer`'ındadır.

    `voice_confidence` analizcinin kendi iş parçacığında çağrılır, bağlantı da orada yaşar.
    Servise ulaşılamazsa parça sessiz sayılır ve hata loga yazılır; bağlantı en çok saniyede
    bir yeniden denenir. Servisin kendisinin düşmesi STT'nin açılış kontrolünde de görünür.
    """

    def __init__(self, url: str, params: VADParams | None = None) -> None:
        super().__init__(params=params)
        self._url = "ws" + url.rstrip("/").removeprefix("http") + VAD
        self._ws: ClientConnection | None = None
        self._retry_at = 0.0

    def num_frames_required(self) -> int:
        return VAD_FRAME

    def voice_confidence(self, buffer: bytes) -> float:
        try:
            ws = self._ws or self._connect()
            if ws is None:
                return 0.0
            ws.send(buffer)
            reply = ws.recv(timeout=1.0)
            if not isinstance(reply, bytes) or len(reply) != 4:
                raise SpeechContractError(f"vad: unexpected reply {reply!r:.40}")
            return float(np.frombuffer(reply, "<f4")[0])
        except (OSError, ValueError, WebSocketException, SpeechContractError) as e:
            log.error("VAD service: %s", e)
            self._drop()
            return 0.0

    def _connect(self) -> ClientConnection | None:
        if time.monotonic() < self._retry_at:
            return None
        self._retry_at = time.monotonic() + 1.0
        ws = connect(self._url, open_timeout=2.0, legacy=True)
        try:
            hello = parse_stream_hello(json.loads(ws.recv(timeout=2.0)), "vad")
            if (hello.sample_rate, hello.frame) != (self.sample_rate, VAD_FRAME):
                raise SpeechContractError(
                    f"vad: service is {hello.sample_rate} Hz / {hello.frame} samples, "
                    f"stream is {self.sample_rate} Hz / {VAD_FRAME}"
                )
        except BaseException:
            ws.close()
            raise
        self._ws = ws
        return ws

    def _drop(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    async def cleanup(self) -> None:
        # Bağlantı analizcinin iş parçacığında yaşar; kapanış el sıkışması döngüyü bekletmez.
        await asyncio.get_running_loop().run_in_executor(self._executor, self._drop)
        await super().cleanup()  # type: ignore[no-untyped-call]  # Pipecat'te tipsiz


COMPLETE_ABOVE = 0.5
"""Pipecat'in yerel Smart Turn'ünün eşiği; model aynı kaldıkça karar da aynı kalır."""


class ServiceTurn(BaseSmartTurn):
    """Sözün bitip bitmediğini STT servisindeki modele sorar (§18: çekirdek model yüklemez);
    sessizlik süresi ve sözün kesitini Pipecat'in `BaseSmartTurn`'ü belirler.

    Analizcinin kendi iş parçacığında çağrılır. Servis cevap vermezse söz bitmemiş sayılır ve
    hata loga yazılır; söz yine de sessizlik süresi dolunca biter. Süre içinde cevap gelmezse
    beklenen sessizlik zaten geçmiştir, söz bitmiş sayılır (Pipecat'in kuralı).
    """

    def __init__(self, url: str, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self._url = url.rstrip("/") + TURN

    def _predict_endpoint(self, audio_array: np.ndarray) -> dict[str, Any]:
        # Servis 32768'e böler; aynı ölçek, aynı olasılık.
        pcm = np.clip(audio_array * 32768, -32768, 32767).astype("<i2").tobytes()
        request = urllib.request.Request(
            f"{self._url}?sample_rate={self.sample_rate}",
            data=pcm,
            headers={"Content-Type": "application/octet-stream"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.params.stop_secs) as r:
                probability = parse_turn(json.load(r))
        except (OSError, ValueError, SpeechContractError) as e:
            # Bağlanırken dolan süre `URLError`'ın içinde gelir.
            reason = e.reason if isinstance(e, urllib.error.URLError) else e
            if isinstance(reason, TimeoutError):
                raise SmartTurnTimeoutException(str(e)) from e
            log.error("turn service: %s", e)
            return {"prediction": 0, "probability": 0.0}
        return {"prediction": int(probability > COMPLETE_ABOVE), "probability": probability}


class ServiceSpeaker:
    """Konuşmacı servisinin istemcisi (§6): sözün sesinden izi.

    Servise ulaşılamazsa iz yoktur ve konuşan tanınmamış sayılır; söz yine yazıya dökülür.
    Hata loga yazılır: sahibin tanınmaması sessiz kalmamalı.
    """

    def __init__(self, url: str) -> None:
        self._url = url.rstrip("/")
        self._http: aiohttp.ClientSession | None = None
        self._rate = 0
        self._resampler = create_stream_resampler()

    async def open(self, http: aiohttp.ClientSession) -> None:
        self._http = http
        try:
            self._rate = (await _health(http, self._url)).sample_rate
        except (aiohttp.ClientError, SpeechContractError) as e:
            log.error("speaker service: %s", e)

    async def embed(self, audio: bytes, sample_rate: int) -> Embedding | None:
        if self._http is None or not self._rate:
            return None
        pcm = await self._resampler.resample(audio, sample_rate, self._rate)
        try:
            async with self._http.post(self._url + EMBED, data=pcm) as r:
                if r.status != 200:
                    log.error("speaker service %s: %s", r.status, await r.text())
                    return None
                return parse_embedding(await r.json())
        except (aiohttp.ClientError, SpeechContractError) as e:
            log.error("speaker service: %s", e)
            return None


class ServiceSTT(STTService):
    """Turun sesi bittiğinde STT servisine gider; metin ve skor döner.

    Bir kullanıcı turu sürerken (`UserStartedSpeakingFrame`'den `TurnEndSignal`'a) VAD'ın
    kestiği parçalar ayrı yazıya dökülmez, ses kesilmeden birikir. Tur yokken (uyanık
    değilken) biten söz `_JOIN_TURN_S` bekler, tur açılmazsa tek başına yazıya dökülür:
    sürekli STT her sözü kaydeder (§6).

    Konuşmacı servisi verilmişse aynı ses ona da gider, iki istek birlikte yürür; iz karenin
    `VOICE` alanına yazılır.
    """

    def __init__(
        self,
        url: str,
        language: str | None,
        speaker: ServiceSpeaker | None = None,
        join_turn_s: float = _JOIN_TURN_S,
        record_dir: Path | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        super().__init__(settings=STTSettings(model=None, language=None), **kwargs)
        self._url = url.rstrip("/")
        self._language = language  # dinleme dili; çıkış dilinden bağımsız (§8.6)
        self._join_turn_s = join_turn_s
        self._record_dir = record_dir  # her sözün sesi ve metni (`SttConfig.record_dir`)
        self._speaker = speaker
        self._http: aiohttp.ClientSession | None = None
        self._rate = 0
        self._resampler = create_stream_resampler()
        self._audio = bytearray()  # tur sürerken turun, yoksa sürmekte olan sözün sesi
        self._speaking = False
        self._in_turn = False
        self._heard = False  # turun sesinde VAD bir söz duydu mu
        self._loose: list[bytes] = []  # tur dışında bitmiş, bekleyen sözler
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

    async def start(self, frame: StartFrame) -> None:
        await super().start(frame)
        self._worker = self.create_task(self._transcribe_queued())
        self._http = aiohttp.ClientSession()
        try:
            self._rate = (await _health(self._http, self._url)).sample_rate
        except (aiohttp.ClientError, SpeechContractError) as e:
            await self.push_error(f"STT service: {e}", e, force_treat_as_permanent=True)
        if self._speaker is not None:
            await self._speaker.open(self._http)

    async def stop(self, frame: EndFrame) -> None:
        if self._worker is not None:
            await self._queue.put(None)  # kuyruktakiler yazıya dökülür, sonra biter
            await self._worker
            self._worker = None
        await super().stop(frame)
        await self._close()

    async def cancel(self, frame: CancelFrame) -> None:
        if self._worker is not None:
            await self.cancel_task(self._worker)
            self._worker = None
        await super().cancel(frame)
        await self._close()

    async def _close(self) -> None:
        if self._http is not None:
            await self._http.close()
            self._http = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, VADUserStartedSpeakingFrame):
            self._speaking = True
            self._heard = True
        elif isinstance(frame, VADUserStoppedSpeakingFrame):
            self._speaking = False
            if not self._in_turn:
                self._set_loose(bytes(self._audio))
                self._audio.clear()
        elif isinstance(frame, UserStartedSpeakingFrame):
            self._in_turn = True
            self._heard = self._speaking or bool(self._loose)
            self._audio[:0] = b"".join(self._loose)
            self._loose.clear()
        elif isinstance(frame, TurnEndSignal) and self._in_turn:
            # Söz duyulmamış ses yazıya dökülmez: Whisper sessizlikten metin uydurur, uydurulan
            # metin Pipecat'te yeni bir tur açar ve tur yine buraya döner.
            if self._heard:
                await self._release(bytes(self._audio))
            self._audio.clear()
            self._heard = self._speaking
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._in_turn = False
            if not self._speaking:
                self._audio = self._audio[-self._pre_speech_bytes() :]

    async def process_audio_frame(
        self, frame: InputAudioRawFrame, direction: FrameDirection
    ) -> None:
        self._audio += frame.audio
        if not self._speaking and not self._in_turn:
            del self._audio[: -self._pre_speech_bytes()]

    async def push_frame(
        self, frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM
    ) -> None:
        if isinstance(frame, TranscriptionFrame):
            frame.finalized = True  # turun ya da sözün bütün sesi; ardından metin gelmez
        await super().push_frame(frame, direction)

    def _pre_speech_bytes(self) -> int:
        return int(self.sample_rate * _PRE_SPEECH_S) * 2

    def _set_loose(self, pcm: bytes) -> None:
        self._loose.append(pcm)
        self.create_task(self._release_loose(pcm))

    async def _release_loose(self, pcm: bytes) -> None:
        await asyncio.sleep(self._join_turn_s)
        if any(p is pcm for p in self._loose):
            self._loose = [p for p in self._loose if p is not pcm]
            await self._release(pcm)

    async def _release(self, pcm: bytes) -> None:
        if pcm:
            await self._queue.put(pcm + bytes(int(self.sample_rate * _TRAILING_SILENCE_S) * 2))

    async def _transcribe_queued(self) -> None:
        while (pcm := await self._queue.get()) is not None:
            try:
                await self.process_generator(self.run_stt(pcm))
            except Exception as e:  # Pipecat'in parçalı STT'si de böyle sürer
                await self.push_error(f"{self}: transcription failed: {e}", exception=e)

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame]:
        voice = (
            None
            if self._speaker is None
            else asyncio.ensure_future(self._speaker.embed(audio, self.sample_rate))
        )
        try:
            async for frame in self._transcribe(audio):
                if isinstance(frame, TranscriptionFrame):
                    if voice is not None:
                        frame.metadata[VOICE] = await voice
                        frame.metadata[VOICE_S] = len(audio) / 2 / self.sample_rate
                    if self._record_dir is not None:
                        await asyncio.to_thread(
                            _record, self._record_dir, audio, self.sample_rate, frame.text
                        )
                yield frame
        finally:
            if voice is not None and not voice.done():
                voice.cancel()

    async def _transcribe(self, audio: bytes) -> AsyncGenerator[Frame]:
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


def word_times(text: str, ends: list[float]) -> list[tuple[str, float]]:
    """Cümlenin her kelimesi ve söylenmiş sayılacağı an (sn, sesin başından).

    Ses kelime gruplarının bitişini verir. Gruplar kelimelerdir ama okunuş kısa kelimeleri
    birleştirebilir ("has been" tek grup); kelime, sırasının vardığı oranda biten gruba
    bağlanır: sayılar eşitse birebir, değilse sapma bir kelimeyi geçmez.
    """
    words = text.split()
    if not words or not ends:
        return [(text, ends[-1] if ends else 0.0)]
    n, m = len(words), len(ends)
    return [(w, ends[max(0, round((i + 1) * m / n) - 1)]) for i, w in enumerate(words)]


def _ends(header: str | None) -> list[float]:
    """Okunamayan başlık yok sayılır: söz yine söylenir, yalnızca cümle bütün sayılır."""
    if not header:
        return []
    try:
        return [float(t) for t in header.split(",")]
    except ValueError:
        log.warning("unreadable %s header ignored", WORD_ENDS)
        return []


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
            # Söz kelime kelime, sesi çalındıkça söylenmiş sayılır: kesilen cevabın geçmişe
            # giren kısmı duyulan kadardır (`word_times`).
            push_text_frames=False,
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
        # Cevabın önceki cümlelerinin ses süresi: Pipecat bir cevabın kelime zamanlarını
        # cevabın başından sayar, cümleler tek bağlamı paylaşır.
        self._offset_s = 0.0

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
            self._offset_s = 0.0
        parts, self._open = split_parts(text, self._open)
        if not parts:
            # Cümle bölücü bir işareti tek başına bırakabilir ("</tr>"); okunacak bir şey yok
            # ama işaret geçmişte yerinde kalır.
            await self.add_word_timestamps([(text, self._offset_s)], context_id)
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
                samples = 0
                ends = _ends(r.headers.get(WORD_ENDS))
                if ends:
                    await self.add_word_timestamps(
                        [(w, t + self._offset_s) for w, t in word_times(text, ends)], context_id
                    )
                async for chunk in r.content.iter_chunked(_CHUNK):
                    await self.stop_ttfb_metrics()
                    # Parça bir örneğin ortasında bölünebilir; yarım bayt sonrakine kalır.
                    data = rest + chunk
                    whole = len(data) - len(data) % 2
                    rest = data[whole:]
                    samples += whole // 2
                    audio = await self._resampler.resample(
                        data[:whole], self._rate, self.sample_rate
                    )
                    yield TTSAudioRawFrame(
                        audio=audio,
                        sample_rate=self.sample_rate,
                        num_channels=1,
                        context_id=context_id,
                    )
                if not ends:  # zaman yoksa cümle bitince bütün olarak
                    await self.add_word_timestamps(
                        [(text, self._offset_s + samples / self._rate)], context_id
                    )
                self._offset_s += samples / self._rate
        except aiohttp.ClientError as e:
            yield ErrorFrame(f"TTS service: {e}")
        finally:
            await self.stop_ttfb_metrics()
