"""İstemci uçbirimi: `uv run python -m client [--ses]`.

İki kip, tek protokol. **Metin kipi** (varsayılan): satır yaz, segment gider; `/iptal` söz
kesmedir. **Ses kipi** (`--ses`): mikrofon dinlenir, endpointing segmenti kapatır, cevap
hoparlörden çalar — ve `/iptal` yine çalışır, çünkü uçbirim ses kipinde de açık kalıyor.

Girdi ayrı bir iş parçacığından okunuyor: `input()` olay döngüsünü bloklarsa asistan
konuşurken yazılan `/iptal` ancak tur bittikten sonra gönderilirdi — yani tam da işe
yaramayacağı anda.

Ses kipinde `--soz-kesme` **varsayılan olarak kapalı**: AEC yok, yani mikrofon asistanın
kendi sesini duyar ve her cevabı kendi kendine keserdi (§18 bu ödünü adıyla koyuyor).
Wake word de yok — §19.6 açık, motor ve kelime seçilmedi; mikrofon bağlantı boyunca
dinliyor.

**Ses arka ucu bağlanmadan önce yoklanıyor.** Mikrofon akışı ayrı bir görevde koşuyor;
eksik PortAudio orada patlasaydı hata görevin içinde kalır, kullanıcı yalnızca sessizlik
görürdü (Kural 13).
"""

import argparse
import asyncio
import contextlib
import sys

from client.audio import AudioPlayer
from client.core import Client, HandshakeError, connect
from client.output import TextOutput
from mayen.config import load

QUIT = ("/cikis", "/çıkış")
INTERRUPT = ("/iptal",)


async def repl(client: Client) -> None:
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:  # EOF
            return
        text = line.strip()
        if not text:
            continue
        if text in QUIT:
            return
        if text in INTERRUPT:
            if not await client.interrupt():
                print("[kesilecek tur yok]")
            continue
        await client.say(text)


def run(argv: list[str] | None = None) -> int:
    """Süreç girişi. GUI kipi asyncio.run'ın *dışında*: Qt'nin döngüsü ana iş parçacığını
    ister ve `app.exec()` orada bloklar — asyncio döngüsünün içinde çağrılamaz."""
    args = _parse(argv)
    if args.gui:
        from client.gui import run as run_gui

        # `--gui --ses`: pencere metinle yazıyor, cevap hoparlörden çıkıyor. Mikrofon
        # **yok** — girdi hâlâ girdi satırı. Ses kipinin mikrofonu ile karıştırılmasın
        # diye burada tek bir şey yapılıyor: hoparlörü kurmak.
        return run_gui(args.url, args.device, _speaker() if args.ses else None)
    return asyncio.run(main(args))


def _speaker() -> AudioPlayer:
    """Hoparlörü kurar; PortAudio yoksa sessizliğe düşmez, anlaşılır biçimde durur."""
    from client.portaudio import MissingBackendError, Speaker, ensure_backend

    try:
        ensure_backend()
    except MissingBackendError as error:
        print(f"ses kipi kullanılamıyor: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    return Speaker()


def _parse(argv: list[str] | None) -> argparse.Namespace:
    config = load()
    parser = argparse.ArgumentParser(prog="client", description="Mayen istemcisi")
    parser.add_argument("--url", default=f"ws://{config.host}:{config.port}")
    parser.add_argument("--device", default="cli")
    parser.add_argument("--ses", action="store_true", help="mikrofon ve hoparlörü kullan")
    parser.add_argument(
        "--gui", action="store_true", help="Qt penceresi (metin girdi; --ses ile hoparlör)"
    )
    parser.add_argument(
        "--soz-kesme",
        action="store_true",
        help="ses kipinde konuşma algılanınca turu kes (AEC olmadan kendi sesini keser)",
    )
    parser.add_argument("--esik", type=float, help="konuşma enerji eşiği (varsayılan 500)")
    return parser.parse_args(argv)


async def main(args: argparse.Namespace) -> int:
    return await (_voice(args) if args.ses else _text(args))


async def _text(args: argparse.Namespace) -> int:
    try:
        async with connect(args.url, args.device, TextOutput()) as client:
            print(f"bağlandı: {args.url} (çıkış: /cikis, söz kesme: /iptal)")
            await repl(client)
    except (HandshakeError, OSError) as error:
        print(f"bağlanılamadı: {error}", file=sys.stderr)
        return 1
    return 0


async def _voice(args: argparse.Namespace) -> int:
    # Import burada: PortAudio yalnızca ses kipinde gerekiyor ve metin kipi ses kartı
    # olmayan bir makinede de koşmalı.
    from client.endpointing import Settings
    from client.portaudio import Microphone, MissingBackendError, Speaker, ensure_backend
    from client.voice import VoiceOutput, listen

    try:
        ensure_backend()
    except MissingBackendError as error:
        print(f"ses kipi kullanılamıyor: {error}", file=sys.stderr)
        return 1

    settings = Settings() if args.esik is None else Settings(threshold=args.esik)
    speaker = Speaker()
    output = VoiceOutput(speaker)
    try:
        async with connect(args.url, args.device, output) as client:
            print(f"bağlandı: {args.url} — dinliyorum (çıkış: /cikis)")
            if not args.soz_kesme:
                print("[söz kesme kapalı: AEC yok, asistan konuşurken mikrofon dinlenmiyor]")
            listener = asyncio.create_task(
                listen(
                    client, Microphone(), output, settings=settings, barge_in=args.soz_kesme
                ),
                name="mic",
            )
            try:
                await repl(client)
            finally:
                listener.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await listener
    except (HandshakeError, OSError) as error:
        print(f"bağlanılamadı: {error}", file=sys.stderr)
        return 1
    finally:
        await speaker.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    with contextlib.suppress(KeyboardInterrupt):
        raise SystemExit(run())
