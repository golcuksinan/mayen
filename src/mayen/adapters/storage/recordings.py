"""Sözlerin ses kayıtları (`stt.record_dir`): her kayıt aynı adla birkaç dosyadır (`.wav`,
`.txt`, `.json`); adı yazıldığı yerel zamandır (`RECORDING_NAME`)."""

from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

from mayen.ports.forget import RECORDING_NAME


class FileRecordings:
    """Kayıt klasörü yoksa (config'te kapalı) silinecek bir şey de yoktur."""

    def __init__(self, directory: Path | None) -> None:
        self._directory = directory

    def delete(self, names: Sequence[str]) -> int:
        if self._directory is None:
            return 0
        return sum(self._unlink(self._directory.glob(f"{n}.*")) for n in names if n)

    def delete_between(self, since: datetime, until: datetime) -> int:
        if self._directory is None or not self._directory.is_dir():
            return 0
        gone = []
        for path in self._directory.iterdir():
            try:
                written = datetime.strptime(path.stem, RECORDING_NAME).astimezone()
            except ValueError:
                continue  # kayıt değil
            if since <= written < until:
                gone.append(path)
        return self._unlink(gone)

    @staticmethod
    def _unlink(paths: Iterable[Path]) -> int:
        count = 0
        for path in paths:
            path.unlink(missing_ok=True)
            count += 1
        return count
