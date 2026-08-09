"""§4'teki katmanların hepsi var ve import edilebiliyor."""

import importlib

import pytest

LAYERS = [
    "transport",
    "session",
    "turn",
    "agent",
    "tools",
    "policy",
    "memory",
    "adapters",
    "data",
    "scheduler",
    "obs",
]


@pytest.mark.parametrize("layer", LAYERS)
def test_layer_is_importable(layer: str) -> None:
    importlib.import_module(f"mayen.{layer}")
