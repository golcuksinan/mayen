"""§4'ün katman sınırlarını mekanik olarak zorlar.

Üç kural: katmanlar yalnızca izin tablosundaki katmanları import eder; ödünç alınan çerçeve
yalnızca `pipeline` ve `app`'te import edilir; SQL depo adaptörünün dışında geçmez. Bir
import reddedildiğinde çözüm tabloyu genişletmek değil sınırı düzeltmektir (§4).
"""

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "mayen"
SRC = Path(__file__).resolve().parent.parent / "src"

# §4 "İzin verilen import'lar" tablosu. Katmanın kendi içindeki import'lar her zaman serbest.
ALLOWED: dict[str, frozenset[str]] = {
    "ports": frozenset(),
    "core": frozenset({"ports"}),
    "skills": frozenset({"ports"}),
    "adapters": frozenset({"ports"}),
    "pipeline": frozenset({"ports", "core"}),
    "app": frozenset({"ports", "core", "skills", "adapters", "pipeline", "replay"}),
    "replay": frozenset({"ports", "core", "pipeline", "skills"}),
}

FRAMEWORK = "pipecat"
FRAMEWORK_LAYERS = frozenset({"pipeline", "app"})

# SQL yalnızca depo adaptöründe: hem sürücü import'u hem SQL metni.
STORAGE = ("adapters", "storage")
SQL_MODULES = frozenset({"sqlite3", "aiosqlite", "sqlalchemy", "apsw"})
SQL_TEXT = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\s")


@dataclass(frozen=True)
class Violation:
    rule: str
    file: Path
    line: int
    detail: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: [{self.rule}] {self.detail}"


def _imports(tree: ast.AST) -> Iterator[tuple[str, int]]:
    """Kaynaktaki her import'un tam modül adı, satır numarasıyla."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == PACKAGE:  # from mayen import core
                for alias in node.names:
                    yield f"{PACKAGE}.{alias.name}", node.lineno
            else:
                yield node.module, node.lineno


def _sql_strings(tree: ast.AST) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and SQL_TEXT.match(node.value)
        ):
            yield node.value.strip().split("\n")[0][:60], node.lineno


def find_violations(src: Path) -> list[Violation]:
    found: list[Violation] = []
    for path in sorted((src / PACKAGE).rglob("*.py")):
        parts = path.relative_to(src / PACKAGE).parts
        layer = parts[0].removesuffix(".py")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        in_storage = parts[:2] == STORAGE
        for module, line in _imports(tree):
            head = module.split(".")
            if head[0] == PACKAGE and len(head) > 1:
                target = head[1]
                if target != layer and target not in ALLOWED.get(layer, frozenset()):
                    found.append(Violation("katman", path, line, f"{layer} -> {target}"))
            elif head[0] == FRAMEWORK and layer not in FRAMEWORK_LAYERS:
                found.append(Violation("çerçeve", path, line, f"{layer} -> {module}"))
            elif head[0] in SQL_MODULES and not in_storage:
                found.append(Violation("sql", path, line, f"{layer} -> {module}"))
        if not in_storage:
            for text, line in _sql_strings(tree):
                found.append(Violation("sql", path, line, f"SQL metni: {text}"))
    return found


def test_source_respects_boundaries() -> None:
    violations = find_violations(SRC)
    assert not violations, "\n".join(map(str, violations))


def test_every_layer_is_in_table() -> None:
    """Tabloya yazılmayan bir katman sessizce denetim dışı kalmasın; tersi de bayat tablo."""
    root = SRC / PACKAGE
    on_disk = {p.name for p in root.iterdir() if p.is_dir() and p.name != "__pycache__"}
    modules = {p.stem for p in root.glob("*.py") if p.stem != "__init__"}
    assert not modules, f"paket kökünde katmansız modül: {modules}"
    assert on_disk == set(ALLOWED)


def test_table_is_acyclic() -> None:
    """Döngü, iki katmanın aslında tek katman olduğunu gizler (§4)."""
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(layer: str, path: list[str]) -> None:
        assert layer not in visiting, f"döngü: {' -> '.join([*path, layer])}"
        if layer in done:
            return
        visiting.add(layer)
        for target in ALLOWED[layer]:
            visit(target, [*path, layer])
        visiting.discard(layer)
        done.add(layer)

    for layer in ALLOWED:
        visit(layer, [])


def _write(src: Path, rel: str, code: str) -> None:
    path = src / PACKAGE / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")


def test_detects_each_rule(tmp_path: Path) -> None:
    """Test kendi kurallarını yakalıyor mu: her kural için bir ihlal, bir de izinli örnek."""
    _write(tmp_path, "core/a.py", "from mayen.pipeline import x\nimport mayen.ports\n")
    _write(tmp_path, "skills/b.py", "from mayen import adapters\n")
    _write(tmp_path, "core/c.py", "import pipecat.frames\n")
    _write(tmp_path, "pipeline/d.py", "from pipecat.frames import Frame\n")
    _write(tmp_path, "skills/e.py", "import sqlite3\nQ = 'SELECT * FROM notes'\n")
    _write(tmp_path, "adapters/storage/f.py", "import sqlite3\nQ = 'SELECT 1'\n")
    _write(tmp_path, "adapters/g.py", "Q = '''\n  INSERT INTO t VALUES (1)'''\n")

    got = {(v.rule, v.file.name) for v in find_violations(tmp_path)}
    assert got == {
        ("katman", "a.py"),
        ("katman", "b.py"),
        ("çerçeve", "c.py"),
        ("sql", "e.py"),
        ("sql", "g.py"),
    }
