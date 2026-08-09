"""Katalog metni ve payının ölçümü (§8.4)."""

import pytest

from mayen.adapters.fakes.llm import FakeLLM
from mayen.tools.catalog import builtin_registry
from mayen.tools.prompt import catalog_text, measure_catalog


def test_every_registered_tool_appears_in_the_catalog() -> None:
    registry = builtin_registry()
    text = catalog_text(registry)
    for tool in registry:
        assert tool.name in text
        for arg in tool.args:
            assert f"--{arg.name}" in text


def test_irreversible_tools_are_marked_as_needing_approval() -> None:
    text = catalog_text(builtin_registry())
    block = next(part for part in text.split("\n\n") if part.startswith("contact_delete"))
    assert "GERİ_ALINAMAZ (onay ister)" in block


def test_catalog_text_is_byte_stable() -> None:
    """Sabit önekin parçası (§8.1): defter aynıysa metnin baytı bile değişmez."""
    assert catalog_text(builtin_registry()) == catalog_text(builtin_registry())


async def test_catalog_share_comes_from_the_counter() -> None:
    """Kural 10: sayı sayaçtan gelir, uzunluktan tahmin edilmez."""
    llm = FakeLLM()
    registry = builtin_registry()

    size = await measure_catalog(registry, llm, budget=8192)

    assert size.tokens == await llm.count_tokens(catalog_text(registry))
    assert size.share == pytest.approx(size.tokens / 8192)


async def test_zero_budget_is_an_error_not_a_division() -> None:
    with pytest.raises(ValueError):
        await measure_catalog(builtin_registry(), FakeLLM(), budget=0)
