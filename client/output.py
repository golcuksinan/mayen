"""İstemcinin duyduklarını nereye verdiği.

`Output` tek arayüz: bugün metin yazan bir uygulaması var, yarın hoparlöre basan bir
tanesi olacak. Tur takibi (`client/core.py`) bu ayrımı hiç görmüyor — §13'ün asıl işi olan
ölü tur filtresi ve sıra denetimi ses geldiğinde olduğu gibi kalıyor.
"""

import sys
from typing import Protocol, TextIO

from mayen.session.state import State


class Output(Protocol):
    """Sunucudan gelenin kullanıcıya ulaştığı yer."""

    async def state(self, state: State, turn_id: str | None) -> None: ...

    async def transcript(self, turn_id: str, text: str) -> None: ...

    async def tool_running(self, turn_id: str, tool_name: str) -> None: ...

    async def announcement(self, turn_id: str, text: str) -> None:
        """Kullanıcı sormadan gelen bildirim (§12). Metni de taşıyor: ses gelmese bile
        —TTS çökmüşse (§14)— hatırlatıcının içeriği kaybolmamalı."""
        ...

    async def reply(self, turn_id: str, text: str) -> None:
        """Seslendirilen cümlenin metni (§13). Sesinden önce geliyor."""
        ...

    async def chunk(self, turn_id: str, seq: int, data: bytes) -> None:
        """Cevabın bir parçası. Sıra ve tur denetimi çağıranda, burada değil."""
        ...

    async def end(self, turn_id: str) -> None: ...

    async def cancelled(self, turn_id: str) -> None: ...

    async def failed(self, code: str, message: str) -> None:
        """§14'ün ayrı kanalı. Sessizce yutulmuyor (Kural 13)."""
        ...


class TextOutput:
    """Metin uçbirimi.

    **Cevabın metni `Reply`'dan geliyor, ses parçalarından değil.** Eskiden parçalar UTF-8
    çözülüyordu — sahte TTS'in yükü metindi (P1) ve bunun geçici olduğu buraya yazılıydı.
    Kokoro bağlanınca o yol kapandı; yükü çözmeye çalışmak artık ham PCM'i ekrana çöp
    olarak basmak olurdu. Ses parçaları burada yalnızca **sayılıyor**: metin istemcisinin
    hoparlörü yok ve "ses geldi ama duyamıyorsun" sessiz kalınacak bir şey değil (Kural 13).
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout
        self._audio_bytes = 0

    async def state(self, state: State, turn_id: str | None) -> None:
        self._line(f"[durum] {state.value}")

    async def transcript(self, turn_id: str, text: str) -> None:
        self._line(f"[anlaşılan] {text}")

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        self._line(f"[tool] {tool_name}")

    async def announcement(self, turn_id: str, text: str) -> None:
        self._line(f"[hatırlatıcı] {text}")

    async def reply(self, turn_id: str, text: str) -> None:
        """Her cümle kendi satırında. Tek satırda biriktirmek denendi ve okunmuyordu:
        durum satırları cevapla aynı anda geliyor ve yarım kalan satırın ortasına
        yazıyorlardı. Cümle zaten kuyruğun birimi (§6)."""
        self._line(f"[cevap] {text}")

    async def chunk(self, turn_id: str, seq: int, data: bytes) -> None:
        self._audio_bytes += len(data)

    async def end(self, turn_id: str) -> None:
        self._finish()

    async def cancelled(self, turn_id: str) -> None:
        self._finish()
        self._line("[iptal edildi]")

    def _finish(self) -> None:
        """Turu kapatır. Gelen sesin boyutu yazılıyor: metin uçbiriminde çalınacak yer
        yok ve sessiz kalmak, sesin hiç gelmediğinden ayırt edilemezdi (Kural 13)."""
        if self._audio_bytes:
            self._line(f"[ses] {self._audio_bytes} bayt")
        self._audio_bytes = 0

    async def failed(self, code: str, message: str) -> None:
        self._line(f"[hata] {code}: {message}")

    def _line(self, text: str) -> None:
        self._write(f"{text}\n")

    def _write(self, text: str) -> None:
        self._stream.write(text)
        self._stream.flush()
