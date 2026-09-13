"""Qt penceresi: metin girdisi, metin çıktısı. Başka hiçbir şey.

Dördüncü `Output` uygulaması — `core.py` yine bir satır değişmedi (P17'nin gerekçesi).

**Olay döngüsü ayrı bir iş parçacığında.** Qt'nin kendi döngüsü ana iş parçacığını tutuyor;
asyncio'yu ona gömmek (qasync) fazladan bir bağımlılık, iki döngüyü yan yana koşturmak
değil. `Output`'un metotları asyncio iş parçacığından çağrılıyor ve pencereye **sinyalle**
dokunuyor: Qt widget'ına başka bir iş parçacığından doğrudan yazmak tanımsız davranış.
Ters yön `run_coroutine_threadsafe`.

**Sohbet, durum ve tool bildirimi gösteriliyor.** Durum sohbet dökümüne
değil, altta duran kendi satırına yazılıyor: her geçiş bir satır olsaydı üç kelimelik bir
cevap dört satır durum arasında kaybolurdu. Gösterilen metin `State`'in kendi değeri —
ikinci bir Türkçe sözlük, dokümanla kod arasında sürüklenecek bir çeviri katmanı olurdu.

Durum **yayın**: §5 uyarınca aynı anda tek tur var, dolayısıyla başka bir cihazın turu da
bu pencereyi meşgul ediyor. `turn_id` bu yüzden ayıklanmıyor — gösterilen şey sistemin
durumu, bu bağlantının değil.

Hata da **yazılıyor**: sessizce yutulmuş bir hata Kural 13'e aykırı ve kullanıcı boş
pencereye bakar.

**Cevabın metni `Reply` çerçevesinden geliyor, ses parçalarından değil.** Eskiden parçalar
UTF-8 çözülüyordu — sahte TTS'in yükü metindi (P1); Kokoro bağlanınca pencere kendi
sorusunu gösterip cevabı göstermez oldu. Metin artık sesin yanında ayrı bir çerçeve (§13).

**Hoparlör isteğe bağlı ve açıkça veriliyor** (`--gui --ses`): verilmezse pencere yalnızca
yazıyor. Yükün ne olduğu **tahmin edilmiyor**; "UTF-8 çözülüyorsa metindir" bir sezgi
olurdu ve ham PCM'in bir kısmı geçerli UTF-8'dir.
"""

import asyncio
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from client.audio import AudioPlayer
from mayen.session.state import State


class Window(QWidget):
    """Sohbet dökümü ve tek satırlık girdi. Sinyaller pencereyi olay döngüsünden ayırır."""

    said = Signal(str)
    interrupted = Signal()
    appended = Signal(str)
    streamed = Signal(str)
    stated = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mayen")
        self.transcript = QTextEdit(readOnly=True)
        self.entry = QLineEdit()
        self.status = QLabel(State.IDLE.value)
        layout = QVBoxLayout(self)
        layout.addWidget(self.transcript)
        layout.addWidget(self.entry)
        layout.addWidget(self.status)
        self.entry.returnPressed.connect(self._submit)
        self.appended.connect(self._append, Qt.ConnectionType.QueuedConnection)
        self.streamed.connect(self._stream, Qt.ConnectionType.QueuedConnection)
        self.stated.connect(self.status.setText, Qt.ConnectionType.QueuedConnection)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt'nin adı)
        """Esc turu keser (Değişmez 12).

        Girdi satırının kendi Esc davranışı yok, o yüzden tuş pencereye kadar geliyor.
        Yazılanı **silmiyor**: iptal edilen şey tur, kullanıcının cümlesi değil.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.interrupted.emit()
            return
        super().keyPressEvent(event)

    def _submit(self) -> None:
        text = self.entry.text().strip()
        if not text:
            return
        self.entry.clear()
        self.said.emit(text)

    def _append(self, text: str) -> None:
        self.transcript.append(text)

    def _stream(self, text: str) -> None:
        """Cevabın parçasını son satırın sonuna ekler; `append` yeni satır açardı."""
        cursor = self.transcript.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.transcript.setTextCursor(cursor)


class GuiOutput(QObject):
    """`client.output.Output`'un Qt uygulaması. asyncio iş parçacığından çağrılır."""

    def __init__(self, window: Window, player: AudioPlayer | None = None) -> None:
        super().__init__()
        self._window = window
        self._player = player
        self._speaking = False

    async def state(self, state: State, turn_id: str | None) -> None:
        self._window.stated.emit(state.value)

    async def transcript(self, turn_id: str, text: str) -> None:
        self._window.appended.emit(f"› {text}")

    async def tool_running(self, turn_id: str, tool_name: str) -> None:
        self._window.appended.emit(f"[tool] {tool_name}")

    async def announcement(self, turn_id: str, text: str) -> None:
        self._window.appended.emit(text)

    async def reply(self, turn_id: str, text: str) -> None:
        # Ayıraç cümlenin **önüne**: sonuna konsaydı her cevap boşlukla biterdi.
        if self._speaking:
            self._window.streamed.emit(" ")
        else:
            self._window.appended.emit("")
            self._speaking = True
        self._window.streamed.emit(text)

    async def chunk(self, turn_id: str, seq: int, data: bytes) -> None:
        """Ses. Hoparlör yoksa yapacak bir şey yok — cümle zaten `reply` ile yazıldı."""
        if self._player is not None:
            await self._player.play(data)

    async def end(self, turn_id: str) -> None:
        self._finish()

    async def cancelled(self, turn_id: str) -> None:
        """Esc'in duyulur karşılığı: tampondaki ses **atılıyor**, çalınıp bitirilmiyor
        (§13, `portaudio.py`'nin `abort()` gerekçesi)."""
        if self._player is not None:
            await self._player.stop()
        self._finish()
        self._window.appended.emit("[iptal edildi]")

    async def failed(self, code: str, message: str) -> None:
        self._window.appended.emit(f"[hata] {code}: {message}")

    def _finish(self) -> None:
        self._speaking = False


def run(url: str, device_id: str, player: AudioPlayer | None = None) -> int:
    """Pencereyi açar, olay döngüsünü arka planda koşturur. Qt ana iş parçacığında kalır."""
    from client.core import Client, connect

    # Qt tek bir uygulama nesnesine izin veriyor; ikincisini kurmak çökmedir.
    app = QApplication.instance() or QApplication([])
    window = Window()
    output = GuiOutput(window, player)
    #: Bağlantı kurulana kadar gönderecek bir şey yok; kutu ana iş parçacığından okunuyor,
    #: asyncio iş parçacığından yazılıyor. Sinyal bağlantısı ana iş parçacığında kalsın diye.
    live: dict[str, tuple[Client, asyncio.AbstractEventLoop]] = {}

    def send(text: str) -> None:
        pair = live.get("client")
        if pair is None:
            window.appended.emit("[bağlantı yok]")
            return
        client, loop = pair
        asyncio.run_coroutine_threadsafe(client.say(text), loop)

    def interrupt() -> None:
        """Esc: koşan turu keser. Bağlantı yoksa **sessiz kalınmıyor** (Kural 13)."""
        pair = live.get("client")
        if pair is None:
            window.appended.emit("[bağlantı yok]")
            return
        client, loop = pair
        asyncio.run_coroutine_threadsafe(client.interrupt(), loop)

    window.said.connect(send)
    window.interrupted.connect(interrupt)

    async def session() -> None:
        try:
            async with connect(url, device_id, output) as client:
                live["client"] = (client, asyncio.get_running_loop())
                await asyncio.Event().wait()  # pencere kapanınca daemon iş parçacığıyla biter
        except Exception as error:
            # Bağlanamama iş parçacığının içinde kalırsa kullanıcı boş pencere görür.
            window.appended.emit(f"[hata] bağlanılamadı: {error}")

    threading.Thread(target=lambda: asyncio.run(session()), daemon=True).start()
    window.resize(600, 400)
    window.show()
    return app.exec()
