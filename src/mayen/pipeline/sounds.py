"""Sistemin sözsüz sesleri (§2.1, §8.8): sistem konuşmaz, yalnızca ses çıkarır.

Tool bitince çalınan ses tool'un gerçekten çalıştığını gösterir: model "ekledim" der ama ses
gelmezse cevap uydurulmuştur. Ses kodla üretilir; sahibin deneyde seçtiği "soft blip": tek,
yumuşak bir ton (A6) ve arkasında 30 ms'lik hafif bir yansıma, toplam 130 ms.
"""

import numpy as np
from pipecat.frames.frames import Frame, OutputAudioRawFrame
from pipecat.processors.frame_processor import (
    FrameDirection,
    FrameProcessor,
    FrameProcessorSetup,
)


def soft_blip(sample_rate: int) -> bytes:
    t = np.arange(int(sample_rate * 0.10)) / sample_rate
    envelope = np.exp(-t / 0.025)
    attack = int(sample_rate * 0.005)
    envelope[:attack] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, attack))  # yumuşak başlangıç
    release = int(sample_rate * 0.008)
    envelope[-release:] *= np.linspace(1, 0, release)  # sonda tık olmasın
    tone = np.sin(2 * np.pi * 1760 * t) * envelope
    delay = int(sample_rate * 0.03)
    out = np.concatenate([tone, np.zeros(delay)])
    out[delay:] += tone * 0.25  # hafif yansıma
    pcm: bytes = (out / np.max(np.abs(out)) * 0.3 * 32767).astype(np.int16).tobytes()
    return pcm


class ToolSound(FrameProcessor):
    """Hatta TTS'ten sonra durur: ses, sesin efektine girmez ve çıkışın hızında üretilir."""

    def __init__(self) -> None:
        super().__init__()
        self._sample_rate = 0
        self._sound = b""

    # Pipecat'in temel sınıfı aynı adı başka tiple tanımlıyor; çağıran bunu verir.
    async def setup(self, setup: FrameProcessorSetup) -> None:  # type: ignore[override]
        await super().setup(setup)
        self._sample_rate = setup.audio_out_sample_rate
        self._sound = soft_blip(self._sample_rate)

    async def play(self) -> None:
        await self.push_frame(
            OutputAudioRawFrame(
                audio=self._sound, sample_rate=self._sample_rate, num_channels=1
            )
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)
