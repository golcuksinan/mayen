"""Giriş noktası: config'i okur, depoları açar, çekirdeği kurar.

Kalıcı bir yapılandırma hatası ayrı bir çıkış koduyla biter (§14): servis yöneticisi onu
yeniden başlatma döngüsüne sokmaz. Kanallar (§7) ve ses hattı (§6) gelene kadar açılış
doğrulamadan ibarettir; oturumları hattı kuran (şimdilik deneydeki senaryo) açar.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from mayen.adapters.storage.sqlite import Database, StorageError
from mayen.app.config import ConfigError, load
from mayen.app.wiring import Core, SkillLoadError

CONFIG_ENV = "MAYEN_CONFIG"
EXIT_CONFIG = 78  # sysexits.h EX_CONFIG

log = logging.getLogger("mayen")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayen")
    parser.add_argument("--config", type=Path, default=os.environ.get(CONFIG_ENV))
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    if args.config is None:
        log.error("no config: pass --config or set %s", CONFIG_ENV)
        return EXIT_CONFIG
    try:
        config = load(args.config, os.environ)
        config.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with Database(config.storage_path) as db:
            core = Core(config, db)
            log.info(
                "ready: model=%s skills=%s",
                config.models.active,
                ",".join(s.name for s in core.registry.specs()),
            )
    except (ConfigError, StorageError, SkillLoadError) as e:
        log.error("configuration error: %s", e)
        return EXIT_CONFIG
    return 0


if __name__ == "__main__":
    sys.exit(main())
