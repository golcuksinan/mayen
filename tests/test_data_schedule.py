"""Ders programı dosyası (§19.8): ayrıştırma saf, yükleme deftere yazıyor."""

from pathlib import Path

import pytest

from mayen.config import ConfigError
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.courses import CourseRepository
from mayen.data.schedule import install, parse

VALID = """
term = "2026-guz"

[[sessions]]
course_code = "BIL301"
title = "İşletim Sistemleri"
day = 1
start = "09:00"
end = "10:50"
location = "A-201"

[[sessions]]
course_code = "BIL305"
title = "Yapay Zekâ"
day = 3
start = "13:00"
end = "14:50"
"""


def test_parse_reads_term_and_sessions() -> None:
    term, sessions = parse(VALID)
    assert term == "2026-guz"
    assert [s.course_code for s in sessions] == ["BIL301", "BIL305"]
    assert sessions[0].location == "A-201"
    assert sessions[1].location is None


@pytest.mark.parametrize(
    "text",
    [
        'term = ""\n[[sessions]]\ncourse_code = "X"\ntitle = "Y"\nday = 1\n'
        'start = "09:00"\nend = "10:00"\n',
        'term = "t"\n',  # hiç ders yok
        'term = "t"\n[[sessions]]\ncourse_code = "X"\ntitle = "Y"\nday = 8\n'
        'start = "09:00"\nend = "10:00"\n',
        'term = "t"\n[[sessions]]\ncourse_code = "X"\ntitle = "Y"\nday = 1\n'
        'start = "9:00"\nend = "10:00"\n',
        'term = "t"\n[[sessions]]\ntitle = "Y"\nday = 1\nstart = "09:00"\nend = "10:00"\n',
        "term = ",
    ],
)
def test_broken_file_raises(text: str) -> None:
    """Sessizce boş programa düşmek "bugün dersin yok" diyen bir yanlış olurdu."""
    with pytest.raises(ConfigError):
        parse(text)


def test_install_replaces_the_term(tmp_path: Path) -> None:
    db = Database(tmp_path / "mayen.db")
    migrate(db)
    courses = CourseRepository(db)
    path = tmp_path / "dersler.toml"
    path.write_text(VALID, encoding="utf-8")

    assert install(courses, path) == "2026-guz"
    assert len(courses.for_term("2026-guz")) == 2
    assert [s.course_code for s in courses.for_day("2026-guz", 1)] == ["BIL301"]
    db.close()


def test_missing_file_raises(tmp_path: Path) -> None:
    db = Database(tmp_path / "mayen.db")
    migrate(db)
    with pytest.raises(ConfigError):
        install(CourseRepository(db), tmp_path / "yok.toml")
    db.close()
