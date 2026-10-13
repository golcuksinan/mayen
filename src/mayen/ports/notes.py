"""Not deposu portu: not skill'leri yalnızca bunu görür (§9.1, §9.5)."""

from dataclasses import dataclass
from typing import Protocol

from mayen.ports.tools import Sensitivity


@dataclass(frozen=True)
class Note:
    id: str
    text: str
    sensitivity: Sensitivity


class NoteStore(Protocol):
    def add(self, text: str, sensitivity: Sensitivity) -> Note: ...

    def search(self, query: str) -> list[Note]:
        """Metni içeren notlar, büyük/küçük harfe bakmadan; boş sorgu hepsini döndürür."""
        ...

    def delete(self, note_id: str) -> bool:
        """Not vardıysa siler; yoksa `False`."""
        ...
