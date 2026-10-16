"""Sözün konuşanı (§6, §10.5) ve geçmişteki sözün başına yazılan adı (§8.1).

İz sözün karesine STT istemcisinde yazılır (`VOICE`); kişiye karar çekirdektedir. Karar karede
bir kez verilir ve aynı karede tutulur (`SPEAKER`): kapı, onay ve transkript aynı sözü
yeniden tanımaz, hepsi aynı kişiyi görür.
"""

import logging
from collections.abc import Callable

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from mayen.core.profile import caller
from mayen.core.speakers import Identified, SpeakerMatcher, VoiceprintModelError
from mayen.pipeline.speech import VOICE
from mayen.ports.people import PersonStore
from mayen.ports.speech import Embedding
from mayen.ports.tools import Caller

log = logging.getLogger(__name__)

SPEAKER = "mayen.speaker"

_NOBODY = Identified(None, None)


def identified(frame: TranscriptionFrame, matcher: SpeakerMatcher) -> Identified:
    known = frame.metadata.get(SPEAKER)
    if isinstance(known, Identified):
        return known
    embedding = frame.metadata.get(VOICE)
    known = _NOBODY
    if isinstance(embedding, Embedding):
        try:
            known = matcher.identify(embedding)
        except VoiceprintModelError as e:
            log.error("speaker: %s", e)
    frame.metadata[SPEAKER] = known
    return known


def recognized(
    matcher: SpeakerMatcher, people: PersonStore
) -> Callable[[TranscriptionFrame], Caller]:
    """Sözün konuşanı (oturum kapısının `CallerSource`'u); izi olmayan ya da eşiği geçemeyen
    söz tanınmamış birinindir."""

    def source(frame: TranscriptionFrame) -> Caller:
        person_id = identified(frame, matcher).person_id
        return caller(None if person_id is None else people.get(person_id))

    return source


def score(frame: TranscriptionFrame) -> float | None:
    """Sözün en yüksek puanı (olaya yazılır); tanıma yoksa ya da henüz bakılmadıysa `None`."""
    known = frame.metadata.get(SPEAKER)
    return known.score if isinstance(known, Identified) else None


class SpeakerLabel(FrameProcessor):
    """Sözün başına konuşanın adı (§8.1); toplayıcının önünde durur, söz bağlama böyle girer.

    Onay kapısının ve transkriptin arkasındadır: onay cevabı ve kayıttaki metin etiketsizdir.
    """

    def __init__(self, name: Callable[[TranscriptionFrame], str]) -> None:
        super().__init__()
        self._label_of = name

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and direction is FrameDirection.DOWNSTREAM:
            frame.text = f"{self._label_of(frame)}: {frame.text}"
        await self.push_frame(frame, direction)
