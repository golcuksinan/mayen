"""Giriş noktası: config'i okur, depoları açar, çekirdeği kurar.

Kalıcı bir yapılandırma hatası ayrı bir çıkış koduyla biter (§14): servis yöneticisi onu
yeniden başlatma döngüsüne sokmaz. Alt komutlar:

- `check` (varsayılan): açılışı doğrular ve çıkar.
- `setup`: sahibi kurar (§10.2). Makinenin başında çalıştırılır; sahip varsa reddeder.
- `serve`: yazılı kanalı (§7) ve hatırlatmaları çalıştırır. Ses hattını şimdilik deneydeki
  senaryo kurar.
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
from mayen.adapters.storage.sqlite import Database, SqlitePersonStore, StorageError
from mayen.app.config import Config, ConfigError, load, storage_path
from mayen.app.server import LoopbackIsLocal, text_app
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
    commands.add_parser("serve", help="run the text channel and reminders")
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
    return 0


def _setup(path: Path, args: argparse.Namespace) -> int:
    # Model gerekmez: sahibi kurmak için yalnızca veritabanı açılır.
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
    log.info("owner set up: id=%s devices=%s", owner.id, ",".join(owner.devices) or "-")
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
            text_app(core, LoopbackIsLocal(TailscaleIdentity())),
            host=config.channel.host,
            port=config.channel.port,
            log_config=None,
        )
    )
    await server.serve()


if __name__ == "__main__":
    sys.exit(main())
