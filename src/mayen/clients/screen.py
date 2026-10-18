"""Masaüstü istemcisi (`mayen-desktop`): `mayen-mic`'in kendisi, üstünde bir ekranla (§7).

Ses, cihaz komutları ve bağlantı `mayen-mic`'in kodudur; bu modül yalnızca bir pencere açar
ve çekirdeğin ekran mesajlarını ona iletir. Ekran `desktop/` altındaki web arayüzüdür,
pencere pywebview'in Qt motoru. Ekran çekirdeğe hiçbir şey göndermez.

Pencerenin döngüsü ana iş parçacığındadır (Qt bunu ister); bağlantı ayrı bir iş parçacığında
kendi döngüsüyle çalışır, koparsa yeniden bağlanır. Mesajlar sayfaya sırayla, tek bir
gönderici iş parçacığından gider: sayfanın cevabını beklemek sesi bekletmesin.
"""

import argparse
import asyncio
import json
import queue
import sys
import threading
import traceback
from pathlib import Path
from typing import Any

import sounddevice as sd  # type: ignore[import-untyped]  # tip bilgisi yok
import webview
from websockets.exceptions import WebSocketException

from mayen.clients.mic import DEFAULT_URL, Traffic, run

UI = Path(__file__).resolve().parents[3] / "desktop" / "dist" / "index.html"
RETRY_S = 2.0


class Page:
    """Sayfaya giden çağrılar; sayfa yüklenmeden gelenler sırada bekler."""

    def __init__(self, window: webview.Window) -> None:
        self._window = window
        self._calls: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._send, daemon=True).start()

    def screen(self, message: dict[str, Any]) -> None:
        # Mesaj JS'e kod olarak değil dize olarak girer: ikinci json.dumps ASCII'dir ve her
        # JSON dizesi geçerli bir JS dizesidir (U+2028 gibi karakterler de kaçışlı).
        raw = json.dumps(message, ensure_ascii=False)
        self._calls.put(f"window.mayenScreen({json.dumps(raw)})")

    def connection(self, state: str) -> None:
        self._calls.put(f"window.mayenConnection({json.dumps(state)})")

    def night(self, span: str) -> None:
        """Gece yerleşiminin saatleri ("23:00-07:00"); kişinin ayarıdır, çekirdekten gelmez."""
        self._calls.put(f"window.mayenNight({json.dumps(span)})")

    def _send(self) -> None:
        self._window.events.loaded.wait()
        while True:
            call = self._calls.get()
            try:
                self._window.evaluate_js(call)
            except Exception as e:  # ölen gönderici ekranı sessizce dondururdu
                print(f"[screen: {type(e).__name__}: {e}]", file=sys.stderr)


class Api:
    """Sayfanın pencereye çağırabildikleri (pywebview js_api); çekirdeğe gitmez."""

    def __init__(self) -> None:
        self.window: webview.Window | None = None

    def fullscreen(self) -> None:
        if self.window is not None:
            self.window.toggle_fullscreen()


def attempt(url: str, page: Page) -> None:
    """Bir bağlantı denemesi; nasıl biterse bitsin ekran kopukluğu görür. Bu iş parçacığında
    yükselen bir hata onu öldürür ve istemci sessizce sağırlaşırdı (§13); her hata yazılır ve
    yeniden denenir."""
    try:
        asyncio.run(run(url, Traffic(), page.screen, lambda: page.connection("live")))
    except (OSError, ValueError, WebSocketException, sd.PortAudioError) as e:
        print(f"[{e}]", file=sys.stderr)
    except Exception:  # beklenmeyen her hata: iş parçacığı ölmesin
        traceback.print_exc()
    page.connection("lost")


def _connect(url: str, page: Page) -> None:
    while True:
        attempt(url, page)
        threading.Event().wait(RETRY_S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayen-desktop")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    parser.add_argument(
        "--ui", default=str(UI), help="the built screen, or the dev server's address"
    )
    parser.add_argument("--night", help="night layout hours, like 23:00-07:00 (default: none)")
    args = parser.parse_args(argv)
    if not args.ui.startswith("http") and not Path(args.ui).exists():
        print(
            f"[no screen at {args.ui}; build it: cd desktop && npm run build]", file=sys.stderr
        )
        return 1
    api = Api()
    window = webview.create_window(
        "Mayen", args.ui, js_api=api, width=1280, height=760, background_color="#0B0D11"
    )
    assert window is not None  # None, yalnızca açılış olayında iptal edilen pencerede
    api.window = window
    page = Page(window)
    if args.night:
        page.night(args.night)
    threading.Thread(target=_connect, args=(args.url, page), daemon=True).start()
    webview.start(gui="qt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
