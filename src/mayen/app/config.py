"""Config'in okunması (§14): tek YAML, gizli bilgiler ortamda."""

from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from mayen.core.models import ModelConfigError, ModelRegistry
from mayen.ports.models import ModelRecord

ACTIVE_MODEL_ENV = "MAYEN_MODEL"

_records = TypeAdapter(dict[str, ModelRecord])


def load_models(path: Path, env: Mapping[str, str]) -> ModelRegistry:
    """YAML'ın `models` bölümünden depo; etkin model ortamdan seçilir (§8.9)."""
    if ACTIVE_MODEL_ENV not in env:
        raise ModelConfigError(f"{ACTIVE_MODEL_ENV} is not set")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ModelRegistry(
        _records.validate_python(raw.get("models", {})), env[ACTIVE_MODEL_ENV], env
    )
