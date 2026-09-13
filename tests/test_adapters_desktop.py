"""Masaüstü adaptörü: komut kurulumu ve çıktı ayrıştırma.

Gerçek `wpctl`/`busctl` **çağrılmıyor** — bu testlerin ölçtüğü şey makinenin ses seviyesi
değil, hangi argv'nin kurulduğu ve çıktının nasıl okunduğu. Gerçek yol elle koşuldu
(`docs/faz8-tool.md`); burada koşulsaydı test makinenin masaüstüne bağlı olurdu ve CI'da
zaten bir oturum yok.
"""

import asyncio
import shutil
from collections.abc import Sequence

import pytest

from mayen.adapters import desktop as module
from mayen.adapters.desktop import SystemDesktop
from mayen.adapters.errors import ServiceFailedError, ServiceUnavailableError


class Calls:
    """`_run`'ın yerine geçer: çağrıyı yazar, hazır çıktıyı döner."""

    def __init__(self, output: str = "") -> None:
        self.argv: list[Sequence[str]] = []
        self.output = output

    async def __call__(self, *argv: str) -> str:
        self.argv.append(argv)
        return self.output


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Calls:
    recorder = Calls()
    monkeypatch.setattr(module, "_run", recorder)
    return recorder


async def test_volume_is_read_as_a_percentage(calls: Calls) -> None:
    """`wpctl get-volume` çıktısı "Volume: 0.45"."""
    calls.output = "Volume: 0.45"
    assert await SystemDesktop().volume() == 45


async def test_a_muted_sink_still_reports_its_level(calls: Calls) -> None:
    """Kısıkken çıktının sonuna " [MUTED]" ekleniyor; seviye yine okunmalı."""
    calls.output = "Volume: 0.30 [MUTED]"
    assert await SystemDesktop().volume() == 30


async def test_unparsable_volume_is_an_error_not_a_guess(calls: Calls) -> None:
    calls.output = "bilinmeyen çıktı"
    with pytest.raises(ServiceFailedError):
        await SystemDesktop().volume()


async def test_the_window_action_becomes_a_kwin_shortcut(calls: Calls) -> None:
    await SystemDesktop().window("close")
    assert calls.argv[0][-2:] == ("s", "Window Close")


async def test_media_targets_the_first_mpris_player(calls: Calls) -> None:
    # `busctl --user list --no-legend`'in gerçek biçimi: ad ilk sütun, gerisi boşlukla ayrık.
    calls.output = (
        "org.kde.KWin                                   2100 kwin_wayland amnesia\n"
        "org.mpris.MediaPlayer2.firefox.instance_1_53   2408 firefox amnesia\n"
    )
    player = await SystemDesktop().media("next")
    assert player == "firefox.instance_1_53"
    assert "org.mpris.MediaPlayer2.firefox.instance_1_53" in calls.argv[1]
    assert calls.argv[1][-1] == "Next"


async def test_no_player_is_an_error(calls: Calls) -> None:
    """ "Duraklattım" demek, hiçbir oynatıcı yokken yanlış olur."""
    calls.output = ":1.4 org.kde.KWin 1 kwin amnesia :1.4 user\n"
    with pytest.raises(ServiceFailedError):
        await SystemDesktop().media("pause")


async def test_a_missing_binary_is_reported_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kural 13. Aynı yol oturum veri yolu görünmediğinde de işliyor."""
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ServiceUnavailableError):
        await SystemDesktop().volume()


async def test_launch_never_goes_through_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """Değişmez 8. argv olduğu gibi `exec`'e gidiyor; birleştirilmiş bir dize yok."""
    seen: dict[str, object] = {}

    async def fake_exec(*argv: str, **kwargs: object) -> object:
        seen["argv"] = argv
        seen["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    await SystemDesktop().launch(("firefox", "--new-window"))
    assert seen["argv"] == ("firefox", "--new-window")
    # Ayrı oturum: aksi hâlde açılan uygulama asistan kapanınca onunla birlikte ölürdü.
    assert seen["kwargs"]["start_new_session"] is True  # type: ignore[index]
