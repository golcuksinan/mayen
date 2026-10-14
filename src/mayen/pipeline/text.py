"""Yazılı kanal (§7) Pipecat hattında: mesajın tetikleyiciye, cevabın mesaja çevrilmesi.

Taşıma çerçevenindir (§13); bu modül yalnızca serileştiriciyi ve hattın iki ucunu verir.
Gelen yazı `text` tetikleyicisiyle tur açar; yazılı mesaj tek parça gelir ve dinleme
durumundan geçmez (§5.4). Onay beklenirken gelen yazı tur açmaz, cevaptır: yalnızca onay
çözümleyicisine gider (§5.4, §10.5). Cevabın metni istemciye parça parça gider.
"""

import logging
from typing import Protocol

from pipecat.frames.frames import (
    Frame,
    InputTransportMessageFrame,
    LLMFullResponseEndFrame,
    OutputTransportMessageFrame,
    TextFrame,
    TTSSpeakFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.base_serializer import FrameSerializer

from mayen.pipeline.session import Sessions
from mayen.ports.channels import MessageKind, WireMessage
from mayen.ports.confirmation import Answer
from mayen.ports.tools import Caller
from mayen.ports.triggers import Priority, Trigger, TriggerSource

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
    ) -> None:
        super().__init__()
        self._session = session
        self._sessions = sessions
        self._confirmations = confirmations
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
                if self._confirmations.awaiting:
                    text, speaker = frame.message.text, self._requester.person_id
                    self._confirmations.answer(Answer(text, speaker))
                    return
                trigger = Trigger(
                    self._session,
                    self._priority,
                    TriggerSource.TEXT,
                    frame.message.text,
                    self._requester,
                )
                await self._sessions.submit(trigger)
            return  # mesaj tetikleyici oldu; kare hatta ilerlemez
        await self.push_frame(frame, direction)


class TextOutput(FrameProcessor):
    """Modelin metnini ve okutulacak soruyu (onay, §10.5) istemciye mesaj olarak gönderir.

    Metin kareleri hatta da ilerler: asistan toplayıcısı cevabı geçmişe onlardan yazar.
    Yalnızca tool çağıran bir model cevabı istemciye gitmez; boş bir cevap sonu da gitmez.
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
        elif isinstance(frame, TextFrame) and frame.text:
            await self._send(MessageKind.TEXT, frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame) and self._open:
            await self._send(MessageKind.RESPONSE_END)

    async def _send(self, kind: MessageKind, text: str = "") -> None:
        self._open = kind is MessageKind.TEXT
        await self.push_frame(OutputTransportMessageFrame(message=WireMessage(kind, text)))
