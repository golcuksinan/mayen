"""Unutulan turu oturumun canlı bağlamından çıkarır (§11.4, §8.4).

Bağlamdaki mesajlar Pipecat'in sözlükleridir ve hangi tura ait olduklarını taşımaz. Bu yüzden
her tur başlarken bağlamdaki yeri not edilir: bir turun mesajları, başladığı yerden bir sonraki
turun başladığı yere kadardır (söz, cevap, tool çağrıları, kesilme notu). Tur dışında duyulan
söz bağlama hiç girmez (§6), çıkarılacak bir şeyi yoktur.
"""

from pipecat.processors.aggregators.llm_context import LLMContext

from mayen.core.turns import Turn
from mayen.ports.forget import Forgotten
from mayen.ports.triggers import TurnId


class ContextTurns:
    def __init__(self) -> None:
        self._context: LLMContext | None = None
        self._starts: list[tuple[TurnId, int]] = []

    def bind(self, context: LLMContext) -> None:
        self._context = context

    def started(self, turn: Turn) -> None:
        if self._context is None:
            return
        self._starts.append((turn.id, len(self._context.messages)))

    def forget(self, forgotten: Forgotten) -> None:
        if self._context is None or not self._starts or not forgotten.turns:
            return
        gone = set(forgotten.turns)
        messages = list(self._context.messages)
        keep: list[object] = []
        starts: list[tuple[TurnId, int]] = []
        ends = [start for _, start in self._starts[1:]] + [len(messages)]
        # İlk turdan önceki mesajlar (varsa) hiçbir tura ait değildir, kalır.
        first = self._starts[0][1] if self._starts else len(messages)
        keep.extend(messages[:first])
        for (turn_id, start), end in zip(self._starts, ends, strict=True):
            if turn_id in gone:
                continue
            starts.append((turn_id, len(keep)))
            keep.extend(messages[start:end])
        if len(keep) == len(messages):
            return
        self._starts = starts
        self._context.set_messages(keep)  # type: ignore[arg-type]
