"""Tool kayıt defteri: katalog ve şema ondan üretilir (§9.1, §9.2)."""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from mayen.ports.tools import ToolSpec


class ToolRegistry:
    """Açılışta bütün tool'larla kurulur ve sonra değişmez (§9.2).

    Modül düzeyinde global değil bir nesnedir; testler arası sızıntı oradan gelir (§9.1).
    """

    def __init__(self, specs: Iterable[ToolSpec[Any]]) -> None:
        tools: dict[str, ToolSpec[Any]] = {}
        for spec in specs:
            if spec.name in tools:
                raise ValueError(f"aynı adla iki tool: {spec.name}")
            tools[spec.name] = spec
        self._tools: Mapping[str, ToolSpec[Any]] = tools

    def get(self, name: str) -> ToolSpec[Any] | None:
        return self._tools.get(name)

    def specs(self) -> Sequence[ToolSpec[Any]]:
        return list(self._tools.values())

    def catalog(self) -> list[dict[str, Any]]:
        """Modele giden katalog: kullanım metni argüman modelinden üretilir (§9.1)."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "parameters": s.args.model_json_schema(),
            }
            for s in self._tools.values()
        ]


def parse_args[A: BaseModel](spec: ToolSpec[A], raw: Mapping[str, Any]) -> A | str:
    """Argümanları doğrular; geçersizse modele geri beslenecek hata metnini döndürür.

    Geçersiz argümanla kullanıcıya hiç sorulmaz (§10.5 adım 1).
    """
    try:
        return spec.args.model_validate(raw)
    except ValidationError as e:
        return str(e)
