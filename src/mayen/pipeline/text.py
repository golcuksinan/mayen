"""Yazılı kanal (§7) Pipecat hattında: mesajın tetikleyiciye, cevabın mesaja çevrilmesi.

Taşıma çerçevenindir (§13); bu modül yalnızca serileştiriciyi ve hattın iki ucunu verir.
Gelen yazı `text` tetikleyicisiyle tur açar; yazılı mesaj tek parça gelir ve dinleme
durumundan geçmez (§5.4). Onay beklenirken gelen yazı tur açmaz, cevaptır: yalnızca onay
çözümleyicisine gider (§5.4, §10.5). Her yazı, açtığı ya da cevap verdiği turla transkripte
girer (§11). Cevabın metni istemciye parça parça gider.
"""

import logging
from typing import Protocol

from pipecat.frames.frames import (
    Frame,
    InputTransportMessageFrame,
    LLMAssistantPushAggregationFrame,
    LLMFullResponseEndFrame,
    OutputTransportMessageFrame,
    TextFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.base_serializer import FrameSerializer

from mayen.core.transcript import Transcript
from mayen.pipeline.session import Sessions
from mayen.ports.channels import MessageKind, WireMessage
from mayen.ports.confirmation import Answer
from mayen.ports.events import ref
from mayen.ports.tools import Caller
from mayen.ports.transcript import Utterance
from mayen.ports.triggers import Priority, Trigger, TriggerSource, TurnId

log = logging.getLogger(__name__)


class WireSerializer(FrameSerializer):
    """`ports.channels`'ın mesajları; istemci çerçeveyi tanımadan konuşabilsin diye JSON."""

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputTransportMessageFrame) and isinstance(
            frame.message, WireMessage
        ):
            return frame.message.encode()
        return None  # ses ve diğer kareler yazılı kanala gitmez

    async def deserialize(self, data: str | bytes) -> Frame | None:
        try:
            message = WireMessage.decode(data)
        except ValueError as e:
            # Bozuk bir mesaj bağlantıyı kapatmaz (§13).
            log.warning("dropped a malformed client message: %s", e)
            return None
        return InputTransportMessageFrame(message=message)


class Confirmations(Protocol):
    """Oturumun onay kapısından yazılı kanalın gördüğü kısım."""

    @property
    def awaiting(self) -> bool: ...

    def answer(self, answer: Answer) -> None: ...


class TextInput(FrameProcessor):
    """İstemcinin yazısını oturumun tetikleyicisine çevirir; taşımanın hemen arkasında durur."""

    def __init__(
        self,
        session: str,
        sessions: Sessions,
        confirmations: Confirmations,
        requester: Caller,
        priority: Priority,
        transcript: Transcript,
    ) -> None:
        super().__init__()
        self._session = session
        self._sessions = sessions
        self._confirmations = confirmations
        self._transcript = transcript
        self._requester = requester  # bağlantının cihazından; tur boyunca değişmez
        self._priority = priority

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, InputTransportMessageFrame) and isinstance(
            frame.message, WireMessage
        ):
            if (
                direction is FrameDirection.DOWNSTREAM
                and frame.message.kind is MessageKind.TEXT
            ):
                text = frame.message.text
                if self._confirmations.awaiting:
                    turn = self._sessions.running(self._session)
                    heard = self._heard(None if turn is None else turn.id, text)
                    record = ref("utterance", heard.id)
                    self._confirmations.answer(Answer(text, self._requester.person_id, record))
                    return
                trigger = Trigger(
                    self._session, self._priority, TriggerSource.TEXT, text, self._requester
                )
                await self._sessions.submit(trigger, lambda turn_id: self._heard(turn_id, text))
            return  # mesaj tetikleyici oldu; kare hatta ilerlemez
        await self.push_frame(frame, direction)

    def _heard(self, turn_id: TurnId | None, text: str) -> Utterance:
        return self._transcript.heard(self._session, turn_id, self._requester, text)


class TextOutput(FrameProcessor):
    """Modelin metnini ve okutulacak soruyu (onay, §10.5) istemciye mesaj olarak gönderir.

    Metin kareleri hatta da ilerler: asistan toplayıcısı cevabı geçmişe onlardan yazar.
    Yalnızca tool çağıran bir model cevabı istemciye gitmez; boş bir cevap sonu da gitmez.
    Okutulan soruyu seste geçmişe TTS servisi yazar; yazılı hatta TTS olmadığından aynı
    kareleri bu işlemci verir, yoksa soru ne geçmişe ne transkripte girerdi.
    """

    def __init__(self) -> None:
        super().__init__()
        self._open = False  # son cevap sonundan beri istemciye metin gitti mi

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)
        if direction is not FrameDirection.DOWNSTREAM:
            return
        if isinstance(frame, TTSSpeakFrame):
            await self._send(MessageKind.TEXT, frame.text)
            await self._send(MessageKind.RESPONSE_END)
            if frame.append_to_context:
                await self.push_frame(TTSStartedFrame(append_to_context=True))
                await self.push_frame(TextFrame(frame.text))
                await self.push_frame(LLMAssistantPushAggregationFrame())
        elif isinstance(frame, TextFrame) and frame.text:
            await self._send(MessageKind.TEXT, frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame) and self._open:
            await self._send(MessageKind.RESPONSE_END)

    async def _send(self, kind: MessageKind, text: str = "") -> None:
        self._open = kind is MessageKind.TEXT
        await self.push_frame(OutputTransportMessageFrame(message=WireMessage(kind, text)))
