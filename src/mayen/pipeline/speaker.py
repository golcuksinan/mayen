"""Sözün konuşanı (§6, §10.5) ve geçmişteki sözün başına yazılan adı (§8.1).

İz sözün karesine STT istemcisinde yazılır (`VOICE`); kişiye karar çekirdektedir. Karar karede
bir kez verilir ve aynı karede tutulur (`SPEAKER`): kapı, onay ve transkript aynı sözü
yeniden tanımaz, hepsi aynı kişiyi görür.
"""

import logging
from collections.abc import Callable, Sequence

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from mayen.core.profile import caller
from mayen.core.speakers import Identified, SpeakerMatcher, VoiceprintModelError, mean
from mayen.pipeline.speech import VOICE, VOICE_S
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


def turn_voice(frames: Sequence[TranscriptionFrame]) -> Embedding | None:
    """Turun sözlerinin ortak izi: her sözün izi sesinin süresiyle ağırlanır. "Hey Mayen" ile
    komut iki söz olarak gelse de turu isteyen ikisinin sesinden birlikte tanınır."""
    voices = [
        (e, f.metadata.get(VOICE_S) or 1.0)
        for f in frames
        if isinstance(e := f.metadata.get(VOICE), Embedding)
    ]
    if not voices:
        return None
    model = voices[-1][0].model
    same = [(e.vector, float(s)) for e, s in voices if e.model == model]
    return Embedding(model, mean([v for v, _ in same], [s for _, s in same]))


def recognized_turn(
    matcher: SpeakerMatcher, people: PersonStore
) -> Callable[[Sequence[TranscriptionFrame]], Caller]:
    """Turu isteyen: turun cevaptan önceki sözlerinin hepsinden (oturum kapısının
    `RequesterSource`'u)."""

    def source(frames: Sequence[TranscriptionFrame]) -> Caller:
        embedding = turn_voice(frames)
        person_id = None
        if embedding is not None:
            try:
                person_id = matcher.identify(embedding).person_id
            except VoiceprintModelError as e:
                log.error("speaker: %s", e)
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
