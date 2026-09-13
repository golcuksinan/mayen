"""Qt penceresi (§19.11). Ekransız koşuyor: `QT_QPA_PLATFORM=offscreen`.

Ölçülen şey arayüzün görüntüsü değil, `Output` sözleşmesi: gelen çerçeveler pencerede
doğru metne dönüyor mu, ve girdi satırı segmenti dışarı veriyor mu. Sinyaller doğrudan
sürülüyor — ayrı iş parçacığı ve gerçek soket `test_client.py`'nin işi.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="gui ekstrası kurulu değil")

from client.gui import GuiOutput, Window
from client.output import Output

from mayen.session.state import State


@pytest.fixture(scope="module")
def app() -> object:
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _drain() -> None:
    """Kuyruğa alınmış sinyaller pencereye ancak olay döngüsü dönünce ulaşır."""
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()


def test_gui_output_satisfies_the_protocol(app: object) -> None:
    output: Output = GuiOutput(Window())
    assert output is not None


async def test_answer_sentences_become_one_line(app: object) -> None:
    """Cevap `Reply`'dan geliyor ve cümleler tek satırda birikiyor."""
    window = Window()
    output = GuiOutput(window)
    await output.transcript("t1", "hava nasıl")
    await output.reply("t1", "Sunny today.")
    await output.reply("t1", "Nothing else.")
    await output.end("t1")
    _drain()
    assert window.transcript.toPlainText().splitlines()[-1] == "Sunny today. Nothing else."


async def test_error_is_shown_not_swallowed(app: object) -> None:
    window = Window()
    await GuiOutput(window).failed("turn_failed", "servis kapalı")
    _drain()
    assert "turn_failed" in window.transcript.toPlainText()


async def test_state_goes_to_its_own_line_not_the_transcript(app: object) -> None:
    window = Window()
    before = window.transcript.toPlainText()
    await GuiOutput(window).state(State.DUSUNUYOR, "t1")
    _drain()
    assert window.status.text() == "DÜŞÜNÜYOR"
    assert window.transcript.toPlainText() == before


async def test_state_of_another_turn_is_shown_too(app: object) -> None:
    """Tek tur küreseldir (§5): başka bir cihazın turu da bu pencereyi meşgul eder."""
    window = Window()
    await GuiOutput(window).state(State.KONUSUYOR, "başka-tur")
    _drain()
    assert window.status.text() == "KONUŞUYOR"


def test_entry_emits_and_clears(app: object) -> None:
    window = Window()
    said: list[str] = []
    window.said.connect(said.append)
    window.entry.setText("  selam  ")
    window.entry.returnPressed.emit()
    assert said == ["selam"]
    assert window.entry.text() == ""


async def test_running_tool_is_shown(app: object) -> None:
    """Tool çalışırken pencere sessiz kalırsa kullanıcı donmuş bir arayüz görür."""
    window = Window()
    await GuiOutput(window).tool_running("t1", "weather")
    _drain()
    assert "weather" in window.transcript.toPlainText()


def test_escape_asks_for_an_interrupt(app: object) -> None:
    """Değişmez 12: her tur her aşamada iptal edilebilir — bu yüzeyde de."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    window = Window()
    asked: list[None] = []
    window.interrupted.connect(lambda: asked.append(None))
    window.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )
    assert asked == [None]


def test_escape_does_not_clear_what_was_typed(app: object) -> None:
    """İptal edilen şey tur; kullanıcının yazdığı cümle değil."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    window = Window()
    window.entry.setText("yarım cümle")
    window.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )
    assert window.entry.text() == "yarım cümle"


def test_blank_entry_sends_nothing(app: object) -> None:
    window = Window()
    said: list[str] = []
    window.said.connect(said.append)
    window.entry.setText("   ")
    window.entry.returnPressed.emit()
    assert said == []


async def test_chunks_go_to_the_speaker_when_one_is_given(app: object) -> None:
    """Hoparlör verilince pencere ses baytını metne çevirmeye **çalışmıyor**: gerçek PCM'in
    bir kısmı geçerli UTF-8 olurdu ve sohbet dökümüne çöp yazardı."""
    from client.audio import FakePlayer

    player = FakePlayer()
    window = Window()
    output = GuiOutput(window, player)
    await output.chunk("t1", 0, b"\x01\x02\x03\x04")
    _drain()
    assert player.played == [b"\x01\x02\x03\x04"]
    assert window.transcript.toPlainText() == ""


async def test_cancelling_drops_the_queued_audio(app: object) -> None:
    """§13: iptalin duyulur karşılığı, tampondakini çalmamak."""
    from client.audio import FakePlayer

    player = FakePlayer()
    output = GuiOutput(Window(), player)
    await output.chunk("t1", 0, b"\x01\x02")
    await output.cancelled("t1")
    assert player.played == []
    assert player.stops == 1


async def test_without_a_speaker_audio_is_not_shown_as_text(app: object) -> None:
    """Hoparlörsüz pencere sesi yok sayıyor: cümle zaten `reply` ile yazıldı, yükü
    çözmeye çalışmak gerçek PCM'i sohbet dökümüne çöp olarak basardı."""
    window = Window()
    output = GuiOutput(window)
    await output.reply("t1", "merhaba")
    await output.chunk("t1", 0, b"merhaba")
    _drain()
    assert window.transcript.toPlainText().strip() == "merhaba"
