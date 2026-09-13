"""Konuşma başı/sonu tespiti (§7). Saf: içeri çerçeve, dışarı tamamlanmış segment.

Endpointing **istemcide** çalışır ve sunucuya akış değil tamamlanmış segment gider; sunucu
tekrar tespit yapmaz. Bu modül o kararın tek uygulaması.

**Enerji tabanlı, model değil.** Yerel bir VAD modeli yüklemek Kural 2'nin sınırında
dolaşırdı (istemci ayrı bir süreç ama aynı makine) ve şu an ölçülecek bir şey de vermezdi:
karşılaştırma yapılabilmesi için önce çalışan bir zincir gerekiyor. Eşiğin ve sayıların
hepsi **işletim değeri**, ölçülmüş karar değil — §19'da bu sayılar yok.

**Ön tampon (pre-roll) şart.** Konuşmanın başladığına karar verildiğinde ilk hece çoktan
geçmiştir; onu atmak "elam" diye başlayan bir transkript demek. Karar anından önceki birkaç
çerçeve saklanıp segmentin başına konuyor.

**Üst sınır var.** Sessizlik gelmeyen bir ortam (fan, sokak) segmenti sonsuza kadar
büyütürdü; tavan dolduğunda segment olduğu yerde kapanır. Kaybolmaz, geç kalmaz.

**Kesme kararı burada verilmiyor.** Bu sınıf yalnızca "konuşma başladı/bitti" diyor; onunla
ne yapılacağı — tur açmak mı, söz kesmek mi — çağıranın işi (`client/voice.py`).
"""

from dataclasses import dataclass

from client.audio import FRAME_BYTES, FRAME_MS, rms

SPEECH_RMS = 500.0
"""Konuşma sayılan en düşük enerji (0–32767). Sessiz bir odanın taban gürültüsü bunun
epey altında kalıyor. Ölçülmüş bir değer değil, başlangıç değeri — uçbirimden ayarlanabilir
ve §19.4 ölçülürken birlikte bakılacak."""

START_FRAMES = 5
"""Ardışık kaç konuşma çerçevesi başlangıç sayılır (100 ms). Tek çerçeve, kapı çarpmasını
konuşma sanmak olurdu."""

END_FRAMES = 30
"""Segmenti kapatan sessizlik (600 ms). Cümle içi duraklamadan uzun, konuşmacıyı bekletecek
kadar da değil."""

PRE_ROLL_FRAMES = 5
"""Karardan önce saklanan çerçeve sayısı (100 ms); ilk hece bu yüzden kesilmiyor.

Tamponun boyu bu sayı **artı** `start_frames`: kararı verdiren konuşma çerçeveleri de
segmentin parçası. Yalnızca ön tampon kadar tutulsaydı, başlangıcı kanıtlayan çerçeveler
onların yerine geçer ve ilk hece yine kaybolurdu."""

MAX_SECONDS = 15.0
"""Tek segmentin tavanı."""


@dataclass(frozen=True, slots=True)
class Settings:
    threshold: float = SPEECH_RMS
    start_frames: int = START_FRAMES
    end_frames: int = END_FRAMES
    pre_roll_frames: int = PRE_ROLL_FRAMES
    max_seconds: float = MAX_SECONDS


class Endpointer:
    """Çerçeveleri segmentlere böler. Durum burada, karar çağıranda."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings if settings is not None else Settings()
        self._pre_roll: list[bytes] = []
        self._segment: list[bytes] = []
        self._loud = 0
        self._quiet = 0
        self.speaking = False

    @property
    def max_frames(self) -> int:
        return int(self._settings.max_seconds * 1000 / FRAME_MS)

    def feed(self, frame: bytes) -> bytes | None:
        """Bir çerçeve verir; segment tamamlandıysa onu döndürür.

        Çerçeve boyu sabit: değişken boy, enerji eşiğini çerçeveden çerçeveye farklı bir
        şeye çevirirdi.
        """
        if len(frame) != FRAME_BYTES:
            raise ValueError(f"Çerçeve {FRAME_BYTES} bayt olmalı, {len(frame)} geldi")
        loud = rms(frame) >= self._settings.threshold
        if not self.speaking:
            self._silent(frame, loud)
            return None
        return self._talking(frame, loud)

    def flush(self) -> bytes | None:
        """Akış bittiğinde elde kalan segment. Yarım segmenti atmak sözü yutmak olurdu."""
        if not self.speaking:
            return None
        return self._close()

    def reset(self) -> None:
        """Biriken her şeyi atar. Söz kesmeden sonra yeni bir dinlemeye başlarken."""
        self._pre_roll.clear()
        self._segment.clear()
        self._loud = self._quiet = 0
        self.speaking = False

    def _silent(self, frame: bytes, loud: bool) -> None:
        self._pre_roll.append(frame)
        keep = self._settings.pre_roll_frames + self._settings.start_frames
        del self._pre_roll[:-keep]
        self._loud = self._loud + 1 if loud else 0
        if self._loud >= self._settings.start_frames:
            self.speaking = True
            self._segment = list(self._pre_roll)
            self._pre_roll = []
            self._quiet = 0

    def _talking(self, frame: bytes, loud: bool) -> bytes | None:
        self._segment.append(frame)
        self._quiet = 0 if loud else self._quiet + 1
        if self._quiet >= self._settings.end_frames:
            return self._close()
        if len(self._segment) >= self.max_frames:
            return self._close()
        return None

    def _close(self) -> bytes:
        segment = b"".join(self._segment)
        self.reset()
        return segment
