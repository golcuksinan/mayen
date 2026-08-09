"""Yedekleme (§16): SQLite'ın kendi API'siyle, döndürmeli.

Kişiler, notlar ve ses profilleri geri getirilemez veri; yedek bu yüzden opsiyonel değil.

Sıklık ve hedef konum yapılandırmadan gelir (§19.12). Yedeği **kim tetikler** sorusu bu
paketin işi değil — zamanlayıcı `scheduler`'da, ve `data` ona bakamaz (§4).
"""

import re
from datetime import UTC, datetime
from pathlib import Path

from mayen.data.db import Database, DatabaseError
from mayen.obs.log import get_logger

PREFIX = "mayen-"
SUFFIX = ".db"
# Ada gömülü zaman damgası: dosya sistemi mtime'ına güvenmek, kopyalanan bir yedek
# dizininde rotasyonu yanlış sıradan yapmak demek.
STAMP = re.compile(rf"^{PREFIX}\d{{8}}T\d{{6}}Z{re.escape(SUFFIX)}$")

log = get_logger(__name__)


def run(db: Database, directory: Path, keep: int) -> Path:
    """Bir yedek alır, eskileri döndürür, yazılan dosyayı döndürür."""
    if keep < 1:
        raise DatabaseError(f"En az bir yedek tutulmalı, keep={keep} verildi")
    directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = directory / f"{PREFIX}{stamp}{SUFFIX}"
    # Önce geçici ada yazılır: yarım kalmış bir yedek `mayen-*.db` desenine uymaz, yani
    # rotasyon onu sağlam bir yedek sanıp yerine sağlam olanı silmez.
    partial = target.with_suffix(".partial")
    db.backup_to(partial)
    partial.replace(target)

    removed = _rotate(directory, keep)
    log.info("yedek alındı", target=str(target), removed=removed)
    return target


def existing(directory: Path) -> list[Path]:
    """Mevcut yedekler, eskiden yeniye. Ad biçimi zaman damgası taşıdığı için ad sırası
    zaman sırasıdır."""
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if STAMP.match(p.name))


def _rotate(directory: Path, keep: int) -> int:
    backups = existing(directory)
    stale = backups[: max(0, len(backups) - keep)]
    for path in stale:
        path.unlink()
    return len(stale)
