"""Ders programı dosyası (§19.8): depodaki TOML, açılışta DB'ye yükleniyor.

Dönemi **dosya söylüyor**, yapılandırma değil: program dönemde bir kez değişiyor ve
değiştiğinde değişen şey zaten bu dosya. Dönemi ayrı bir ortam değişkenine koymak, iki
yerin aynı anda güncellenmesini gerektiren ve biri unutulduğunda "bugün dersin yok" diyen
sessiz bir yanlış üretirdi (`tools/spec.py`'nin `course_term` notu da bunu söylüyor).

Ayrıştırma yükleme değil: `parse()` saf, `install()` deftere yazıyor. Dosyanın bozuk olup
olmadığını görmek için veritabanı açmak gerekmiyor.

**Boş dosya bir hata**, boş program değil. Programı gerçekten boş bir dönem yok; boş
listeyi kabul etmek, yolu yanlış yazılmış bir dosyayı "ders yok" diye okumak olurdu.
"""

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path

from mayen.config import ConfigError
from mayen.data.repositories.courses import CourseRepository, CourseSession

_TIME = re.compile(r"^([01][0-9]|2[0-3]):[0-5][0-9]$")


def parse(text: str) -> tuple[str, list[CourseSession]]:
    """TOML metnini (dönem, dersler) çiftine çevirir. Hatalar `ConfigError`."""
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"Ders programı dosyası çözümlenemedi: {error}") from error

    term = raw.get("term")
    if not isinstance(term, str) or not term:
        raise ConfigError("Ders programı dosyasında `term` yok ya da boş")

    rows = raw.get("sessions")
    if not isinstance(rows, list) or not rows:
        raise ConfigError(f"{term}: ders programı dosyasında hiç `[[sessions]]` yok")

    return term, [_session(term, index, row) for index, row in enumerate(rows, start=1)]


def install(courses: CourseRepository, path: Path) -> str:
    """Dosyayı okur ve dönemi bir bütün olarak deftere yazar; dönemi döndürür."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"Ders programı dosyası okunamadı: {path}") from error
    term, sessions = parse(text)
    courses.replace_term(term, sessions)
    return term


def _session(term: str, index: int, row: object) -> CourseSession:
    where = f"{term}: {index}. ders"
    if not isinstance(row, dict):
        raise ConfigError(f"{where} bir tablo değil")
    fields: Mapping[str, object] = row
    day = fields.get("day")
    if not isinstance(day, int) or isinstance(day, bool) or not 1 <= day <= 7:
        raise ConfigError(f"{where}: `day` 1 (Pazartesi) ile 7 (Pazar) arasında olmalı")
    location = fields.get("location")
    if location is not None and not isinstance(location, str):
        raise ConfigError(f"{where}: `location` metin olmalı")
    return CourseSession(
        course_code=_text(fields, "course_code", where),
        title=_text(fields, "title", where),
        day_of_week=day,
        start_time=_time(fields, "start", where),
        end_time=_time(fields, "end", where),
        location=location,
    )


def _text(fields: Mapping[str, object], key: str, where: str) -> str:
    value = fields.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{where}: `{key}` yok ya da boş")
    return value


def _time(fields: Mapping[str, object], key: str, where: str) -> str:
    value = _text(fields, key, where)
    if not _TIME.match(value):
        raise ConfigError(f"{where}: `{key}` 'HH:MM' biçiminde olmalı, {value!r} geldi")
    return value
