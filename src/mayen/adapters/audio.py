"""Ses yükünün adaptör tarafındaki temsili.

Kodek seçimi §19.5'te açık. Açık olan şey **hangi** kodek kullanılacağı; sesin bir biçimi
olduğu değil. Bu yüzden biçim burada bir alan olarak var ve seçim sonra yapılıyor —
`transport` da çerçeve başlığında bu alanı taşır, iki yerde iki liste tutulmaz.
"""

from dataclasses import dataclass
from enum import StrEnum


class Codec(StrEnum):
    """§19.5 açık: yerelde ham PCM, uzakta sıkıştırma — ama karar ölçüme bağlı.

    Her iki aday da burada bildiriliyor; hangisinin kullanılacağı yapılandırma ve ölçüm
    işi. `OPUS` bildirilmiş olması onu destekleyen bir kod yazıldığı anlamına gelmez.
    """

    PCM16 = "pcm16"
    OPUS = "opus"


@dataclass(frozen=True, slots=True)
class AudioFormat:
    codec: Codec
    sample_rate: int
    channels: int


@dataclass(frozen=True, slots=True)
class Audio:
    """Tamamlanmış bir ses parçası. Segment tespiti istemcide (§7); sunucu geleni olduğu
    gibi kabul eder."""

    format: AudioFormat
    data: bytes
