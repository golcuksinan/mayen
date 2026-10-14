"""Giriş noktası: config'i okur, depoları açar, çekirdeği kurar.

Kalıcı bir yapılandırma hatası ayrı bir çıkış koduyla biter (§14): servis yöneticisi onu
yeniden başlatma döngüsüne sokmaz. Alt komutlar:

- `check` (varsayılan): açılışı doğrular ve çıkar.
- `setup`: sahibi kurar (§10.2). Makinenin başında çalıştırılır; sahip varsa reddeder.
- `serve`: yazılı kanalı (§7) ve hatırlatmaları çalıştırır. Ses hattını şimdilik deneydeki
  senaryo kurar.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import uvicorn

from mayen.adapters.channel.tailscale import TailscaleIdentity
from mayen.adapters.storage.sqlite import Database, SqlitePersonStore, StorageError
from mayen.app.config import Config, ConfigError, load, storage_path
from mayen.app.server import text_app
from mayen.app.wiring import Core, SkillLoadError
from mayen.ports.people import DeviceId, DevicePairedError, OwnerExistsError

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
    setup.add_argument("--language", required=True, help="output language, e.g. tr")
    setup.add_argument("--address-as", help="how the assistant addresses the owner")
    setup.add_argument(
        "--device",
        action="append",
        default=[],
        # `local` geliştirme istisnasıdır: mimaride bu makinenin ses birimleri ortaktır.
        help="personal device: a Tailscale node StableID, or 'local' (development only)",
    )
    commands.add_parser("serve", help="run the text channel and reminders")
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


async def _serve(core: Core, config: Config) -> None:
    server = uvicorn.Server(
        uvicorn.Config(
            text_app(core, TailscaleIdentity()),
            host=config.channel.host,
            port=config.channel.port,
            log_config=None,
        )
    )
    await server.serve()


if __name__ == "__main__":
    sys.exit(main())
