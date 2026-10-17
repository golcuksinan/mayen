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
from pathlib import Path
from typing import Any

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

    def _send(self) -> None:
        self._window.events.loaded.wait()
        while True:
            self._window.evaluate_js(self._calls.get())


def _connect(url: str, page: Page) -> None:
    while True:
        traffic = Traffic()
        try:
            asyncio.run(run(url, traffic, page.screen, lambda: page.connection("live")))
        except (OSError, ValueError, WebSocketException) as e:
            print(f"[{e}]", file=sys.stderr)
        page.connection("lost")
        threading.Event().wait(RETRY_S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayen-desktop")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    parser.add_argument(
        "--ui", default=str(UI), help="the built screen, or the dev server's address"
    )
    args = parser.parse_args(argv)
    if not args.ui.startswith("http") and not Path(args.ui).exists():
        print(
            f"[no screen at {args.ui}; build it: cd desktop && npm run build]", file=sys.stderr
        )
        return 1
    window = webview.create_window(
        "Mayen", args.ui, width=1280, height=760, background_color="#0B0D11"
    )
    assert window is not None  # None, yalnızca açılış olayında iptal edilen pencerede
    page = Page(window)
    threading.Thread(target=_connect, args=(args.url, page), daemon=True).start()
    webview.start(gui="qt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
