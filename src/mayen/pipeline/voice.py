"""Sesli kanalın serileştiricisi (§13): istemciyle çekirdek arasında ham PCM.

Biçim `ports.channels`'tadır (`VoiceHello`); selamı bağlantıyı kabul eden yollar. Sesin
yanındaki metin mesajları cihaz komutlarıdır (§9.7, biçim `ports.devices`'ta): gelenler
`on_text`'e verilir, çekirdeğin gönderdiği komut acil taşıma mesajı olarak çıkar.
"""

import logging
from collections.abc import Callable

from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    OutputTransportMessageUrgentFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer

log = logging.getLogger(__name__)


class VoiceSerializer(FrameSerializer):
    def __init__(
        self, input_sample_rate: int, on_text: Callable[[str], None] = lambda _: None
    ) -> None:
        super().__init__()
        self._input_sample_rate = input_sample_rate
        self._on_text = on_text
        self._warned = False

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        if isinstance(frame, OutputTransportMessageUrgentFrame) and isinstance(
            frame.message, str
        ):
            return frame.message
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, str):
            self._on_text(data)
            return None
        if len(data) % 2:
            # Bozuk mesaj bağlantıyı kapatmaz (§13); akış sürekli olduğundan bir kez yazılır.
            if not self._warned:
                log.warning("dropped a voice message that is not 16-bit PCM")
                self._warned = True
            return None
        return InputAudioRawFrame(
            audio=data, sample_rate=self._input_sample_rate, num_channels=1
        )
