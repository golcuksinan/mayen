"""Wake word (§6): STT servisindeki modelin puanı ve sözün tur açıp açmadığı (§5.1).

Model STT servisindedir (§18: çekirdek model yüklemez). `ServiceWake` girdinin sesini servise
akıtır; puan eşiği geçince hatta `WakeWordFrame` bırakır. `WakeStart` sözün başladığına karar
veren stratejilerin önünde durur: uyanık değilken sözü durdurur, söz transkripte girer ama
modele gitmez (§5.1: STT'nin sürekli akması LLM'in her sese cevap vermesi demek değildir).

Uyanıklık üç yoldan gelir: wake word, süren bir tur (söz konuşmanın kendisidir, §5.4) ve
asistan sustuktan sonraki takip penceresi. Pencerede söz VAD'ın başladı dediği anla sayılır,
yazıya dökülmesiyle değil: pencerenin son anında başlayan söz de pencerenindir.
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    SystemFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.turns.types import ProcessFrameResult
from pipecat.turns.user_start.base_user_turn_start_strategy import BaseUserTurnStartStrategy
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException

from mayen.ports.speech import WAKE, WAKE_FRAME, SpeechContractError, parse_stream_hello

log = logging.getLogger(__name__)

_RETRY_S = 5.0


@dataclass
class WakeWordFrame(SystemFrame):
    """Wake word duyuldu; `score` eşiği geçen puan."""

    score: float = 0.0


class ServiceWake(FrameProcessor):
    """Girdinin sesini STT servisindeki wake word modeline akıtır; ses hatta aynen devam eder.

    Puan eşiği aşağıdan yukarı geçtiğinde bir kez işaret verir: model aynı söz boyunca birkaç
    adım yüksek kalır. Servise ulaşılamazsa ses yine akar ama kimse uyandıramaz; hata loga
    yazılır, bağlantı `_RETRY_S`'de bir yeniden denenir.
    """

    def __init__(self, url: str, threshold: float) -> None:
        super().__init__()
        self._url = "ws" + url.rstrip("/").removeprefix("http") + WAKE
        self._threshold = threshold
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._rest = b""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            if self._task is None:
                # Hız ilk sesle bilinir; bağlantı onunla açılır.
                self._task = self.create_task(self._stream(frame.sample_rate))
            data = self._rest + frame.audio
            step = WAKE_FRAME * 2
            whole = len(data) - len(data) % step
            for i in range(0, whole, step):
                self._queue.put_nowait(data[i : i + step])
            self._rest = data[whole:]
        await self.push_frame(frame, direction)
        if isinstance(frame, EndFrame | CancelFrame) and self._task is not None:
            await self.cancel_task(self._task)
            self._task = None

    async def _stream(self, sample_rate: int) -> None:
        while True:
            try:
                async with connect(self._url, open_timeout=2.0) as ws:
                    await self._listen(ws, sample_rate)
            except (OSError, WebSocketException, SpeechContractError, ValueError) as e:
                log.error("wake word service: %s", e)
            await asyncio.sleep(_RETRY_S)
            # Bağlantı yokken biriken ses bayattır; sonraki bağlantı şimdiden başlar.
            while not self._queue.empty():
                self._queue.get_nowait()

    async def _listen(self, ws: ClientConnection, sample_rate: int) -> None:
        hello = parse_stream_hello(json.loads(await ws.recv()), "wake")
        if (hello.sample_rate, hello.frame) != (sample_rate, WAKE_FRAME):
            raise SpeechContractError(
                f"wake: service is {hello.sample_rate} Hz / {hello.frame} samples, "
                f"stream is {sample_rate} Hz / {WAKE_FRAME}"
            )
        above = False
        while True:
            await ws.send(await self._queue.get())
            reply = await ws.recv()
            if not isinstance(reply, bytes) or len(reply) != 4:
                raise SpeechContractError(f"wake: unexpected reply {reply!r:.40}")
            score = float(np.frombuffer(reply, "<f4")[0])
            if score >= self._threshold and not above:
                await self.push_frame(WakeWordFrame(score=score))
            above = score >= self._threshold


class WakeStart(BaseUserTurnStartStrategy):  # type: ignore[no-untyped-call]  # Pipecat'te tipsiz
    """Sözün tur açabilmesi için uyanıklık ister; başlangıç stratejilerinin ilkidir.

    `running` oturumda bir tur sürüp sürmediğidir. Uyanık değilken bütün kareler sonraki
    stratejilere geçmeden durur ve duyulan metin toplayıcıdan silinir.
    """

    def __init__(
        self,
        running: Callable[[], bool],
        follow_up_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self._running = running
        self._follow_up_s = follow_up_s
        self._clock = clock
        self._bot_speaking = False
        self._follow_up_until = 0.0

    def awake(self) -> bool:
        return self._running() or self._bot_speaking or self._clock() < self._follow_up_until

    async def process_frame(self, frame: Frame) -> ProcessFrameResult:
        await super().process_frame(frame)
        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            self._follow_up_until = self._clock() + self._follow_up_s
        if isinstance(frame, WakeWordFrame):
            await self.trigger_user_turn_started()
            return ProcessFrameResult.STOP
        if self.awake():
            return ProcessFrameResult.CONTINUE
        if isinstance(frame, TranscriptionFrame):
            await self.trigger_reset_aggregation()  # type: ignore[no-untyped-call]  # tipsiz
        return ProcessFrameResult.STOP
