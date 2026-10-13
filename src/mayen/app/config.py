"""Config'in okunması (§14): tek YAML, gizli bilgiler ortamda."""

from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, TypeAdapter

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


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path


def storage_path(path: Path) -> Path:
    """YAML'ın `storage` bölümünden veritabanı dosyası (§11.6). Göreli yol config dosyasının
    yanına göredir: çalışma dizinine göre olsaydı, servisi başka yerden başlatmak boş bir
    veritabanı açardı."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    storage = StorageConfig.model_validate(raw.get("storage"))
    return path.parent / storage.path.expanduser()
