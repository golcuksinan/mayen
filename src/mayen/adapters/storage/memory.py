"""Bellekte duran depolar; süreç kapanınca içerikleri gider."""

import itertools

from mayen.ports.notes import Note
from mayen.ports.tools import Sensitivity


def _fold(text: str) -> str:
    # "İ".casefold() "i" + birleşen nokta verir; nokta atılmazsa "DİŞÇİ" "dişçi"yi bulamaz.
    return text.casefold().replace("\u0307", "")


class MemoryNoteStore:
    """Kalıcı bir not deposu kararlaşana kadar notlar burada durur."""

    def __init__(self) -> None:
        self._notes: dict[str, Note] = {}
        # Sayaçtan: "not sayısı + 1" silinmiş bir notun numarasını yeniden verirdi.
        self._ids = itertools.count(1)

    def add(self, text: str, sensitivity: Sensitivity) -> Note:
        note = Note(str(next(self._ids)), text, sensitivity)
        self._notes[note.id] = note
        return note

    def search(self, query: str) -> list[Note]:
        needle = _fold(query)
        return [n for n in self._notes.values() if needle in _fold(n.text)]

    def delete(self, note_id: str) -> bool:
        return self._notes.pop(note_id, None) is not None
