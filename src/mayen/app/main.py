"""Giriş noktası: config'i okur, depoları açar, çekirdeği kurar.

Kalıcı bir yapılandırma hatası ayrı bir çıkış koduyla biter (§14): servis yöneticisi onu
yeniden başlatma döngüsüne sokmaz. Alt komutlar:

- `check` (varsayılan): açılışı doğrular ve çıkar.
- `setup`: sahibi kurar (§10.2). Makinenin başında çalıştırılır; sahip varsa reddeder.
  `--voice` verilirse sahibin ses izi de yazılır (konuşmacı servisi açık olmalı).
- `voice`: kurulmuş sahibin ses izini dosyalardan yazar; eskisinin yerine. `setup` gibi
  makinenin başında çalışır; iz sesle verilemez (§10.2).
- `serve`: yazılı ve sesli kanalı (§7, §13) ve hatırlatmaları çalıştırır. Sesli kanal,
  config'te STT ve TTS servisleri varsa açılır.
- `replay`: kayıttaki turları listeler; bir tur verilirse onu bugünkü prompt ve modelle
  yeniden oynatır (§14). Veritabanının tek sahibi olduğundan `serve` açıkken çalışmaz.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import uvicorn
import yaml

from mayen.adapters.channel.tailscale import TailscaleIdentity
from mayen.adapters.storage.sqlite import (
    Database,
    SqlitePersonStore,
    SqliteVoiceprintStore,
    StorageError,
)
from mayen.app.config import Config, ConfigError, load, speaker_url, storage_path
from mayen.app.server import LoopbackIsLocal, core_app
from mayen.app.voice import VoiceError, voiceprint
from mayen.app.wiring import Core, SkillLoadError, replayer
from mayen.ports.people import DeviceId, DevicePairedError, OwnerExistsError
from mayen.replay.run import render

CONFIG_ENV = "MAYEN_CONFIG"
EXIT_CONFIG = 78  # sysexits.h EX_CONFIG
EXIT_REFUSED = 1

log = logging.getLogger("mayen")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayen")
    parser.add_argument("--config", type=Path, default=os.environ.get(CONFIG_ENV))
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("check", help="validate the configuration and exit")
    setup = commands.add_parser("setup", help="set up the owner (once, on this machine)")
    setup.add_argument("--name", required=True)
    setup.add_argument("--language", required=True, help="output language, e.g. English")
    setup.add_argument("--address-as", help="how the assistant addresses the owner")
    setup.add_argument(
        "--device",
        action="append",
        default=[],
        # `local` geliştirme istisnasıdır: mimaride bu makinenin ses birimleri ortaktır.
        help="personal device: a Tailscale node StableID, or 'local' (development only)",
    )
    setup.add_argument(
        "--voice", nargs="+", type=Path, default=[], help="the owner's voice samples (WAV)"
    )
    voice = commands.add_parser(
        "voice", help="replace the owner's voiceprint (on this machine)"
    )
    voice.add_argument("samples", nargs="+", type=Path, help="voice samples (WAV)")
    commands.add_parser("serve", help="run the text and voice channels and reminders")
    replay = commands.add_parser("replay", help="list recorded turns, or replay one")
    replay.add_argument("turn", nargs="?", help="turn id or a unique prefix of it")
    replay.add_argument(
        "--mocks", type=Path, help="YAML: tool name -> the result the model sees"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    if args.config is None:
        log.error("no config: pass --config or set %s", CONFIG_ENV)
        return EXIT_CONFIG
    try:
        if args.command == "setup":
            return _setup(args.config, args)
        if args.command == "voice":
            return _voice(args.config, args.samples)
        config = load(args.config, os.environ)
        config.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with Database(config.storage_path) as db:
            core = Core(config, db)
            log.info(
                "ready: model=%s skills=%s",
                config.models.active,
                ",".join(s.name for s in core.registry.specs()),
            )
            if args.command == "serve":
                asyncio.run(_serve(core, config))
            elif args.command == "replay":
                return asyncio.run(_replay(core, db, args))
    except (ConfigError, StorageError, SkillLoadError) as e:
        log.error("configuration error: %s", e)
        return EXIT_CONFIG
    except VoiceError as e:
        log.error("voice refused: %s", e)
        return EXIT_REFUSED
    return 0


def _setup(path: Path, args: argparse.Namespace) -> int:
    # Model gerekmez: sahibi kurmak için yalnızca veritabanı açılır. İz önce çıkarılır: servis
    # hata verirse izsiz bir sahip kalmaz.
    owner_voice = None if not args.voice else voiceprint(speaker_url(path), args.voice)
    db_path = storage_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with Database(db_path) as db:
        try:
            owner = SqlitePersonStore(db).create_owner(
                args.name, args.language, args.address_as, tuple(map(DeviceId, args.device))
            )
        except (OwnerExistsError, DevicePairedError) as e:
            log.error("setup refused: %s", e)
            return EXIT_REFUSED
        if owner_voice is not None:
            SqliteVoiceprintStore(db).set(owner.id, owner_voice.model, owner_voice.vector)
    log.info(
        "owner set up: id=%s devices=%s voice=%s",
        owner.id,
        ",".join(owner.devices) or "-",
        "-" if owner_voice is None else f"{len(args.voice)} samples, {owner_voice.model}",
    )
    return 0


def _voice(path: Path, samples: list[Path]) -> int:
    owner_voice = voiceprint(speaker_url(path), samples)
    with Database(storage_path(path)) as db:
        owner = SqlitePersonStore(db).owner()
        if owner is None:
            log.error("voice refused: no owner; run setup first")
            return EXIT_REFUSED
        SqliteVoiceprintStore(db).set(owner.id, owner_voice.model, owner_voice.vector)
    log.info("owner voiceprint set: %d samples, %s", len(samples), owner_voice.model)
    return 0


async def _replay(core: Core, db: Database, args: argparse.Namespace) -> int:
    player = replayer(core, db)
    if args.turn is None:
        for turn in player.turns():
            print(
                f"{turn.id}  {turn.time.astimezone():%Y-%m-%d %H:%M:%S}"
                f"  {turn.source.value:6} {turn.session}"
            )
        return 0
    try:
        turn = player.find(args.turn)
    except LookupError as e:
        log.error("replay refused: %s", e)
        return EXIT_REFUSED
    mocks = {} if args.mocks is None else yaml.safe_load(args.mocks.read_text(encoding="utf-8"))
    print(render(await player.replay(turn.id, mocks or {})))
    return 0


async def _serve(core: Core, config: Config) -> None:
    server = uvicorn.Server(
        uvicorn.Config(
            core_app(core, LoopbackIsLocal(TailscaleIdentity())),
            host=config.channel.host,
            port=config.channel.port,
            log_config=None,
        )
    )
    await server.serve()


if __name__ == "__main__":
    sys.exit(main())
