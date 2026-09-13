"""§4'ün tek yönlü bağımlılık kuralını mekanik olarak zorlar.

Doküman zinciri açıkça veriyor:
`transport → session → turn → agent → tools → adapters`. Alt katman üstü import etmez.

Zincirde adı geçmeyen katmanların yeri buradaki `RANK` tablosunda türetildi; gerekçeler
tablonun yanında. Bir katmanın yeri tartışmalıysa çözüm import eklemek değil, bu tabloyu
düzeltmek ya da sınırı yeniden çizmektir.
"""

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

PACKAGE = "mayen"
SRC = Path(__file__).resolve().parent.parent / "src"

# Küçük sayı = üst katman. Bir katman yalnızca kendinden büyük rütbeyi import edebilir.
#
# Rütbeler bilerek birbirinden farklı: eşit rütbe karşılıklı import demektir, yani iki
# katman arasında sessizce döngü kurulabilir. Sıralamayı yanlış tahmin etmenin bedeli bir
# gün bir import'un reddedilmesi ve sıralamanın konuşulmasıdır; eşit bırakmanın bedeli
# kimsenin haberi olmayan bir döngüdür. İlki gürültülü, ikincisi sessiz.
RANK: dict[str, int] = {
    "main": -1,  # montaj: her şeyi import eder, kimse onu import etmez. Rütbesiz
    #             bırakılsaydı denetim dışı kalırdı — bir katman ondan import etse
    #             bu test görmezdi
    "transport": 0,  # dış dünyanın giriş noktası
    "scheduler": 1,  # zamanlanmış görev de bir turu tetikler, ama sesi kendisi yollamaz;
    #                  §12'ye göre oturumun kuyruğuna girer — transport'a ihtiyacı yok
    # Dokümandaki zincir: transport → session → turn → agent → tools → adapters
    "session": 2,
    "turn": 3,
    "agent": 4,
    "tools": 5,
    # Zincirde adı geçmeyenler.
    "policy": 6,  # tools etki sınıfını policy'den alır (Kural 9), tersi olmaz
    "memory": 7,  # agent kullanır; kendisi data ve adapters üstünde durur
    "data": 8,  # repository'ler; tools, policy ve memory buraya iner
    "adapters": 9,  # ports & adapters
    # Kesişen: herkes import eder, kendileri mayen'den bir şey import etmez.
    #
    # obs en dipte olduğu için P3'te tur izini yazarken data'ya inemeyecek ve bu test onu
    # reddedecek. Çözüm import eklemek değil: obs bir TraceSink `Protocol`'ü tanımlar, data
    # onu uygular, bağımlılık tersine döner. Dokümanın LLM/STT/TTS için kullandığı kalıbın
    # aynısı (§4, ports & adapters).
    "obs": 10,
    "config": 11,  # hiçbir şey import etmez, herkes ondan okur
}


@dataclass(frozen=True)
class Violation:
    source: str
    imports: str
    file: Path
    line: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.source} -> {self.imports}"


def _layer_of_path(path: Path, root: Path) -> str | None:
    """Dosyanın hangi katmana ait olduğu. Paket kökündeki modüller kendi adlarıyla."""
    parts = path.relative_to(root / PACKAGE).parts
    name = parts[0]
    if name.endswith(".py"):
        name = name[: -len(".py")]
    return name if name in RANK else None


def _imported_layers(tree: ast.AST) -> Iterator[tuple[str, int]]:
    """Kaynaktaki `mayen.<katman>` import'ları, satır numarasıyla."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name.split(".")
                if head[0] == PACKAGE and len(head) > 1:
                    yield head[1], node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            head = node.module.split(".")
            if head[0] != PACKAGE:
                continue
            if len(head) > 1:  # from mayen.agent import X
                yield head[1], node.lineno
            else:  # from mayen import agent
                for alias in node.names:
                    yield alias.name, node.lineno


def find_violations(root: Path) -> list[Violation]:
    """`root/mayen` altındaki tüm kaynağı gezer, ters yönlü import'ları döndürür."""
    found: list[Violation] = []
    for path in sorted((root / PACKAGE).rglob("*.py")):
        source_layer = _layer_of_path(path, root)
        if source_layer is None:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for target_layer, line in _imported_layers(tree):
            if target_layer not in RANK or target_layer == source_layer:
                continue
            if RANK[target_layer] < RANK[source_layer]:
                found.append(Violation(source_layer, target_layer, path, line))
    return found


def test_ranks_are_distinct() -> None:
    """Eşit rütbe iki katman arasında sessiz döngüye izin verir; olmamalı."""
    assert len(set(RANK.values())) == len(RANK)


def test_every_layer_package_has_a_rank() -> None:
    """Yeni bir katman eklenip tabloya yazılmazsa sessizce denetim dışı kalmasın."""
    on_disk = {
        p.name for p in (SRC / PACKAGE).iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    missing = on_disk - RANK.keys()
    assert not missing, f"RANK tablosunda yeri olmayan katman: {missing}"


def test_source_has_no_upward_imports() -> None:
    violations = find_violations(SRC)
    assert not violations, "Alt katman üst katmanı import ediyor:\n" + "\n".join(
        str(v) for v in violations
    )


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("import mayen.agent", "agent"),
        ("from mayen.agent import Loop", "agent"),
        ("from mayen import agent", "agent"),
        ("from mayen.agent.loop import Loop", "agent"),
    ],
)
def test_detects_planted_violation(tmp_path: Path, statement: str, expected: str) -> None:
    """Denetim gerçekten yakalıyor mu — her import biçimi için kasıtlı ihlal."""
    layer = tmp_path / PACKAGE / "adapters"
    layer.mkdir(parents=True)
    (tmp_path / PACKAGE / "__init__.py").touch()
    (layer / "__init__.py").touch()
    (layer / "bad.py").write_text(f"{statement}\n", encoding="utf-8")

    violations = find_violations(tmp_path)

    assert [(v.source, v.imports) for v in violations] == [("adapters", expected)]


# --- SQL yalnızca data/ içinde (§16) ---------------------------------------------------

# Bir dizeyi SQL sayan işaret: ifadenin ilk kelimesi. Gövdesinde "select" geçen bir cümle
# yakalanmaz, "SELECT ..." ile başlayan bir dize yakalanır.
SQL_START = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA|BEGIN|COMMIT|ROLLBACK)\s",
    re.IGNORECASE,
)
SQL_HOME = "data"


def _sql_literals(tree: ast.AST) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and SQL_START.match(node.value)
        ):
            yield node.value.split("\n")[0][:60], node.lineno


def find_stray_sql(root: Path) -> list[str]:
    """`data/` dışında kalan SQL. Repository kalıbı ancak buysa gerçek (§16)."""
    stray: list[str] = []
    for path in sorted((root / PACKAGE).rglob("*.py")):
        if _layer_of_path(path, root) == SQL_HOME:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        stray.extend(f"{path}:{line}: {text}" for text, line in _sql_literals(tree))
    return stray


def test_sql_lives_only_in_the_data_layer() -> None:
    stray = find_stray_sql(SRC)
    assert not stray, "data/ dışında SQL:\n" + "\n".join(stray)


def test_stray_sql_is_actually_detected(tmp_path: Path) -> None:
    """Denetim çalışıyor mu — `data/` dışına kasten bir sorgu koy."""
    layer = tmp_path / PACKAGE / "tools"
    layer.mkdir(parents=True)
    (tmp_path / PACKAGE / "__init__.py").touch()
    (layer / "notes.py").write_text(
        'q = "SELECT * FROM notes"\nmesaj = "Bir not seçtim"\n', encoding="utf-8"
    )

    stray = find_stray_sql(tmp_path)

    assert len(stray) == 1
    assert "SELECT * FROM notes" in stray[0]


def test_downward_import_is_allowed(tmp_path: Path) -> None:
    """Doğru yöndeki import (agent -> adapters) denetimi tetiklemez."""
    layer = tmp_path / PACKAGE / "agent"
    layer.mkdir(parents=True)
    (tmp_path / PACKAGE / "__init__.py").touch()
    (layer / "__init__.py").write_text("from mayen.adapters import llm\n", encoding="utf-8")

    assert find_violations(tmp_path) == []
