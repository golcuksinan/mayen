"""Konuşmacı tanıma kararı (§6, §10.5): ses izinden kişiye.

İzi servis çıkarır (§3); kayıtlı izle karşılaştırıp puanı bulan ve eşikle karar veren burasıdır.
Sonuç bir iddia değil puandır: eşiği geçen en yüksek puanlı kişi konuşandır, geçen yoksa konuşan
tanınmamıştır. Eşik config'tedir.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from mayen.ports.people import Person, Voiceprint, VoiceprintStore
from mayen.ports.speech import Embedding

# Geçmişteki sözün başında tanınmayan konuşanın adı (§8.1).
UNKNOWN_LABEL = "unknown"


class VoiceprintModelError(Exception):
    """Kayıtlı iz başka bir modelle çıkarılmış; iki modelin izleri karşılaştırılamaz."""


@dataclass(frozen=True)
class Identified:
    person_id: str | None  # eşiği geçen yoksa `None`
    score: float | None  # en yüksek puan; kayıtlı iz yoksa `None`


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"vectors of length {len(a)} and {len(b)}")
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return 0.0 if norm == 0 else sum(x * y for x, y in zip(a, b, strict=True)) / norm


def best(embedding: Embedding, prints: Sequence[Voiceprint], threshold: float) -> Identified:
    top: tuple[float, str] | None = None
    for p in prints:
        if p.model != embedding.model:
            # Sessizce atlanırsa sahip "tanınmayan" olur ve sebebi hiçbir yerde görünmez.
            raise VoiceprintModelError(
                f"voiceprint of person {p.person_id} is from {p.model!r}, "
                f"the service runs {embedding.model!r}"
            )
        score = cosine(embedding.vector, p.vector)
        if top is None or score > top[0]:
            top = (score, p.person_id)
    if top is None:
        return Identified(None, None)
    score, person_id = top
    return Identified(person_id if score >= threshold else None, score)


class SpeakerMatcher:
    """Kayıtlı izler her sözde depodan okunur: kayıt değişince yeniden açmak gerekmez."""

    def __init__(self, store: VoiceprintStore, threshold: float) -> None:
        if not 0 < threshold < 1:
            raise ValueError(f"threshold {threshold} is not between 0 and 1")
        self._store = store
        self.threshold = threshold

    def identify(self, embedding: Embedding) -> Identified:
        return best(embedding, self._store.all(), self.threshold)


def mean(
    vectors: Sequence[Sequence[float]], weights: Sequence[float] | None = None
) -> tuple[float, ...]:
    """Birden çok örneğin izi (§10.4): birim uzunluğa getirilmiş izlerin ortalaması, birim
    uzunlukta. Uzun bir örnek kısalarını bastırmasın diye her biri önce normalleştirilir;
    ağırlık verilirse (sesin süresi gibi) ortalama ona göredir."""
    if not vectors:
        raise ValueError("no samples")
    if weights is None:
        weights = [1.0] * len(vectors)
    if len(weights) != len(vectors) or min(weights) < 0 or sum(weights) == 0:
        raise ValueError(f"weights {list(weights)} do not fit {len(vectors)} samples")
    units = [[w * x for x in _unit(v)] for v, w in zip(vectors, weights, strict=True)]
    return _unit([sum(column) for column in zip(*units, strict=True)])


def _unit(v: Sequence[float]) -> tuple[float, ...]:
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        raise ValueError("zero vector")
    return tuple(x / norm for x in v)


def label(person: Person | None) -> str:
    """Geçmişteki sözün başına yazılan ad (§8.1)."""
    return UNKNOWN_LABEL if person is None else person.name
