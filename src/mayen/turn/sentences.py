"""Cümle bölücü (§6).

Amaç tek: **ilk TTS parçasını mümkün olan en erken anda üretmek.** Token akışı burada
parçalara ayrılır; parçaları sıraya koyan yer `turn/speech.py`.

§6 üç ölçüt sayıyor — cümle sonu noktalaması, minimum uzunluk, maksimum bekleme eşiği — ve
bu dosya ikiye ayrılmış hâlde yazıyor:

- `SentenceSplitter` saf: noktalama ve uzunluk. Zaman yok, I/O yok, milisaniyede test edilir.
- `split()` zamanı ekler: eşik dolarsa eldeki yarım cümle olduğu gibi verilir.

Zamanı saf bölücünün içine koymak, noktalama kurallarını ancak saat ilerleterek test
edilebilir hâle getirirdi.

**Sayılar varsayılansız.** §6 ne minimum uzunluk ne de eşik için bir sayı veriyor; §19.4'ün
gecikme hedefi de açık. `ApprovalFlow.timeout_seconds` ve `AgentLoop.max_steps` ile aynı
gerekçe: ölçülmemiş bir sayıyı koda gömmek, sonra kimsenin nereden geldiğini bilemediği bir
varsayım demek.

**Noktalamanın ardından bir karakter beklenir.** "18.5 derece" cümlenin ortasıdır; nokta
ancak arkasından boşluk gelirse cümle sonudur. Bu yüzden akışın sonundaki noktalama, akış
bitene (`flush()`) kadar bölmez — bir karakterlik gecikme, yanlış yerden bölünmüş bir
cümleden ucuzdur.
"""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator

_ENDERS = ".!?…"


class SentenceSplitter:
    """Gelen metni cümlelere böler. Zamanla ilgisi yok."""

    def __init__(self, *, min_chars: int) -> None:
        if min_chars < 1:
            raise ValueError("min_chars en az 1 olmalı")
        self._min_chars = min_chars
        self._buffer = ""

    @property
    def pending(self) -> bool:
        """Elde henüz verilmemiş metin var mı — bekleme eşiği buna bakar."""
        return bool(self._buffer.strip())

    def feed(self, text: str) -> list[str]:
        """Parçayı ekler ve tamamlanan cümleleri döner (çoğu zaman boş liste)."""
        self._buffer += text
        pieces: list[str] = []
        while (cut := self._cut()) is not None:
            pieces.append(self._buffer[:cut].strip())
            self._buffer = self._buffer[cut:].lstrip()
        return pieces

    def flush(self) -> str | None:
        """Eldeki her şeyi verir: akış bitti ya da bekleme eşiği doldu."""
        rest = self._buffer.strip()
        self._buffer = ""
        return rest or None

    def _cut(self) -> int | None:
        """Bölünecek yer: noktalama dizisinin sonu, ardında boşluk, yeterli uzunlukta."""
        index = 0
        while index < len(self._buffer):
            if self._buffer[index] not in _ENDERS:
                index += 1
                continue
            end = index
            while end < len(self._buffer) and self._buffer[end] in _ENDERS:
                end += 1
            if end >= len(self._buffer):
                return None  # ardındaki karakter henüz gelmedi
            if (
                self._buffer[end].isspace()
                and len(self._buffer[:end].strip()) >= self._min_chars
            ):
                return end
            index = end
        return None


async def split(
    chunks: AsyncIterator[str], *, min_chars: int, max_wait_seconds: float
) -> AsyncGenerator[str]:
    """Token akışını cümlelere böler; eşik dolarsa yarım cümleyi de verir (§6).

    **Bekleyen `anext` iptal edilmiyor.** Eşik dolduğunda kaynağı iptal etmek, üreticiyi
    yarıda kesmek ve gelmekte olan parçayı düşürmek olurdu; görev bir sonraki tura devredilir.

    **Kaynağı bu fonksiyon kapatmıyor:** onu kuran taraf sahibi ve `aclosing` orada duruyor.
    """
    if max_wait_seconds <= 0:
        raise ValueError("max_wait_seconds pozitif olmalı")
    splitter = SentenceSplitter(min_chars=min_chars)
    source = chunks.__aiter__()
    pending: asyncio.Task[str] | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.ensure_future(anext(source))
            timeout = max_wait_seconds if splitter.pending else None
            done, _ = await asyncio.wait({pending}, timeout=timeout)
            if not done:
                # Eşik doldu: eldeki yarım cümle sesin başlamasını daha fazla bekletmez.
                piece = splitter.flush()
                if piece is not None:
                    yield piece
                continue
            task, pending = pending, None
            try:
                chunk = task.result()
            except StopAsyncIteration:
                break
            for piece in splitter.feed(chunk):
                yield piece
    finally:
        if pending is not None:
            pending.cancel()
    last = splitter.flush()
    if last is not None:
        yield last
