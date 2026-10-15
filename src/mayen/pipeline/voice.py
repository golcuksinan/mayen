"""Sesli kanalın serileştiricisi (§13): istemciyle çekirdek arasında ham PCM.

Biçim `ports.channels`'tadır (`VoiceHello`); selamı bağlantıyı kabul eden yollar, burada
yalnızca ses durur.
"""

import logging

from pipecat.frames.frames import Frame, InputAudioRawFrame, OutputAudioRawFrame
from pipecat.serializers.base_serializer import FrameSerializer

log = logging.getLogger(__name__)


class VoiceSerializer(FrameSerializer):
    def __init__(self, input_sample_rate: int) -> None:
        super().__init__()
        self._input_sample_rate = input_sample_rate
        self._warned = False

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, str) or len(data) % 2:
            # Bozuk mesaj bağlantıyı kapatmaz (§13); akış sürekli olduğundan bir kez yazılır.
            if not self._warned:
                log.warning("dropped a voice message that is not 16-bit PCM")
                self._warned = True
            return None
        return InputAudioRawFrame(
            audio=data, sample_rate=self._input_sample_rate, num_channels=1
        )
