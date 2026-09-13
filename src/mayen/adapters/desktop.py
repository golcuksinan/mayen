"""Masaüstü denetimi: ses, medya, pencere, uygulama açma.

Diğer adaptörlerle aynı gerekçe (§4): tool'lar *ne* istendiğini bilir, *nasıl* yapıldığını
bilmez. Buradaki "nasıl" bu makineye özel ve ölçülerek seçildi — oturum **Wayland + KDE**:

- **Ses:** `wpctl` (PipeWire). `pactl` de var ama seviye okuma/yazma `wpctl`'de tek satır.
- **Medya:** MPRIS, D-Bus üzerinden (`org.mpris.MediaPlayer2.*`). `playerctl` kurulu değil
  ve kurmaya gerek yok; `busctl` zaten sistemde.
- **Pencere:** KWin'in **genel kısayolları** (`org.kde.kglobalaccel`). X11'in `wmctrl`/
  `xdotool`'u Wayland'da çalışmaz; KWin'e script yüklemek (`org.kde.KWin.Scripting`) ise
  ayrı bir JS dosyası ve kırılgan bir yol. Kısayol yolu aktif pencere üzerinde çalışıyor,
  bu yüzden "kapat/küçült/büyüt" ucuz — ama "şu uygulamaya geç" ve "hangi pencereler açık"
  bu yoldan **gelmiyor**, ve o boşluk bilerek doldurulmadı.

**Hiçbir yerde kabuk yok** (Değişmez 8). Her çağrı `exec` ile argv listesi; `shell=True`
ya da dize birleştirme yok. Modelden gelen değer hiçbir argv'ye doğrudan girmiyor: pencere
eylemi sayılı seçeneklerden birine, uygulama adı yapılandırmadaki listeye eşleniyor
(§19.9'un WoL kalıbı). Modelin yazabildiği tek serbest sayı ses seviyesi ve o da sınırlanıyor.

**Yokluk sessiz değil** (Kural 13): `busctl`/`wpctl` yoksa ya da oturum veri yolu
görünmüyorsa `ServiceUnavailableError`. Sonuncusu gerçek bir durum — servis grafik oturum
açılmadan başlatılırsa masaüstü tool'ları çalışmaz ve kullanıcının bunu duyması gerekir.
"""

import asyncio
import shutil
from collections.abc import Mapping, Sequence
from typing import Protocol

from mayen.adapters.errors import ServiceFailedError, ServiceUnavailableError
from mayen.obs.log import get_logger

log = get_logger(__name__)

SERVICE = "desktop"

WINDOW_ACTIONS: Mapping[str, str] = {
    "close": "Window Close",
    "minimize": "Window Minimize",
    "maximize": "Window Maximize",
    "fullscreen": "Window Fullscreen",
    "show-desktop": "Show Desktop",
    "overview": "Overview",
}
"""Seçenek → KWin kısayol adı. **İzin listesi budur**: `Kill Window` da bir kısayol adı ve
listede olmadığı için erişilemez. Eşleme kodda, çünkü kısayol adları KDE'nin sabitleri —
kullanıcının düzenleyeceği bir şey değil, uygulama listesinin aksine."""

MEDIA_ACTIONS: Mapping[str, str] = {
    "play-pause": "PlayPause",
    "pause": "Pause",
    "next": "Next",
    "previous": "Previous",
    "stop": "Stop",
}
"""Seçenek → MPRIS metodu."""

_MPRIS_PREFIX = "org.mpris.MediaPlayer2."
_SINK = "@DEFAULT_AUDIO_SINK@"
_TIMEOUT = 5.0


class Desktop(Protocol):
    """Masaüstünün tool'lara görünen yüzü. Sahtesi testlerde, gerçeği makinede."""

    async def volume(self) -> int:
        """Geçerli ses seviyesi, yüzde."""
        ...

    async def set_volume(self, level: int) -> None: ...

    async def media(self, action: str) -> str:
        """Medya eylemini uygular ve etkilenen oynatıcının adını döner."""
        ...

    async def window(self, action: str) -> None: ...

    async def launch(self, argv: Sequence[str]) -> None: ...


class SystemDesktop:
    """Gerçek masaüstü: `wpctl` ve `busctl` üzerinden, hepsi argv ile."""

    async def volume(self) -> int:
        # `wpctl get-volume` çıktısı: "Volume: 0.45" (kısık ise sonunda " [MUTED]").
        out = await _run("wpctl", "get-volume", _SINK)
        try:
            return round(float(out.split()[1]) * 100)
        except (IndexError, ValueError) as exc:
            raise ServiceFailedError(SERVICE, f"ses seviyesi okunamadı: {out!r}") from exc

    async def set_volume(self, level: int) -> None:
        await _run("wpctl", "set-volume", _SINK, f"{level}%")

    async def media(self, action: str) -> str:
        method = MEDIA_ACTIONS[action]
        player = await self._player()
        await _run(
            "busctl",
            "--user",
            "call",
            player,
            "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2.Player",
            method,
        )
        return player.removeprefix(_MPRIS_PREFIX)

    async def window(self, action: str) -> None:
        await _run(
            "busctl",
            "--user",
            "call",
            "org.kde.kglobalaccel",
            "/component/kwin",
            "org.kde.kglobalaccel.Component",
            "invokeShortcut",
            "s",
            WINDOW_ACTIONS[action],
        )

    async def launch(self, argv: Sequence[str]) -> None:
        """Uygulamayı **ayrı bir oturumda** başlatır ve beklemez.

        `start_new_session`: aksi hâlde açılan uygulama asistanın süreç grubunda kalır ve
        asistan kapandığında onunla birlikte ölürdü. Çıktısı da yutuluyor — açılan
        uygulamanın stdout'u asistanın kayıtlarına karışacak bir şey değil.
        """
        try:
            await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            raise ServiceFailedError(SERVICE, f"{argv[0]} çalıştırılamadı: {exc}") from exc

    async def _player(self) -> str:
        """Çalan ilk MPRIS oynatıcısı. Yoksa bu bir hata: "duraklattım" demek yanlış olur."""
        out = await _run("busctl", "--user", "list", "--no-legend")
        for line in out.splitlines():
            name = line.split(maxsplit=1)[0] if line.split() else ""
            if name.startswith(_MPRIS_PREFIX):
                return name
        raise ServiceFailedError(SERVICE, "çalışan bir medya oynatıcısı yok")


async def _run(*argv: str) -> str:
    """Komutu çalıştırır ve stdout'unu döner. Kabuk yok, dize birleştirme yok."""
    if shutil.which(argv[0]) is None:
        raise ServiceUnavailableError(SERVICE, f"{argv[0]} kurulu değil")
    try:
        process = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), _TIMEOUT)
    except OSError as exc:
        raise ServiceUnavailableError(SERVICE, f"{argv[0]} çalıştırılamadı: {exc}") from exc
    except TimeoutError as exc:
        process.kill()
        raise ServiceFailedError(SERVICE, f"{argv[0]} zamanında bitmedi") from exc
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        # Oturum veri yolu yoksa hata buradan çıkıyor: servis grafik oturum açılmadan
        # başlatıldığında masaüstü tool'ları çalışmaz ve bunun duyulması gerekir.
        raise ServiceFailedError(SERVICE, f"{argv[0]} başarısız: {detail or 'sebep yok'}")
    return stdout.decode("utf-8", errors="replace").strip()
