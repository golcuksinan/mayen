"""Config'in okunması (§14): tek YAML, gizli bilgiler ortamda, prompt ayrı dosyada.

Göreli yollar config dosyasının yanına göredir: çalışma dizinine göre olsaydı, servisi başka
yerden başlatmak boş bir veritabanı ya da başka bir prompt açardı.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from mayen.core.models import ModelConfigError, ModelRegistry
from mayen.core.turns import TurnConfigError, Turns
from mayen.ports.models import ModelRecord
from mayen.ports.triggers import Fate, Priority, TriggerSource

ACTIVE_MODEL_ENV = "MAYEN_MODEL"

_records = TypeAdapter(dict[str, ModelRecord])


class ConfigError(Exception):
    """Kalıcı yapılandırma hatası: yeniden başlatmak düzeltmez (§14)."""


class _Strict(BaseModel):
    # Yanlış yazılmış bir anahtar sessizce yok sayılırsa varsayılanla çalışılır.
    model_config = ConfigDict(extra="forbid", frozen=True)


class StorageConfig(_Strict):
    path: Path


class PromptConfig(_Strict):
    system: Path


class TriggerConfig(_Strict):
    voice_priority: Priority
    max_running: int = Field(ge=1)
    settle_s: float = Field(gt=0)
    response_timeout_s: float = Field(gt=0)
    fates: dict[TriggerSource, Fate]


class ConfirmationConfig(_Strict):
    timeout_s: float = Field(gt=0)


class _File(_Strict):
    storage: StorageConfig
    prompts: PromptConfig
    output_language: str  # modelin kullanıcıya konuştuğu dil (§8.6)
    triggers: TriggerConfig
    confirmation: ConfirmationConfig
    models: dict[str, ModelRecord]


@dataclass(frozen=True)
class Config:
    models: ModelRegistry
    storage_path: Path
    system_prompt: str
    output_language: str
    triggers: TriggerConfig
    confirmation: ConfirmationConfig

    def turns(self) -> Turns:
        return Turns(self.triggers.fates, self.triggers.max_running)


def _read(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return raw


def _relative(config: Path, path: Path) -> Path:
    return config.parent / path.expanduser()


def load(path: Path, env: Mapping[str, str]) -> Config:
    """Bütün config; her hata `ConfigError` olarak, açılışta yükselir."""
    try:
        file = _File.model_validate(_read(path))
        if ACTIVE_MODEL_ENV not in env:
            raise ModelConfigError(f"{ACTIVE_MODEL_ENV} is not set")
        config = Config(
            models=ModelRegistry(file.models, env[ACTIVE_MODEL_ENV], env),
            storage_path=_relative(path, file.storage.path),
            system_prompt=_relative(path, file.prompts.system).read_text(encoding="utf-8"),
            output_language=file.output_language,
            triggers=file.triggers,
            confirmation=file.confirmation,
        )
        config.turns()  # eksik ya da hatta karşılığı olmayan akıbet açılışta görünsün (§5.3)
    except (OSError, yaml.YAMLError, ValidationError, ModelConfigError, TurnConfigError) as e:
        raise ConfigError(str(e)) from e
    return config


def load_models(path: Path, env: Mapping[str, str]) -> ModelRegistry:
    """YAML'ın `models` bölümünden depo; etkin model ortamdan seçilir (§8.9)."""
    if ACTIVE_MODEL_ENV not in env:
        raise ModelConfigError(f"{ACTIVE_MODEL_ENV} is not set")
    raw = _read(path)
    return ModelRegistry(
        _records.validate_python(raw.get("models", {})), env[ACTIVE_MODEL_ENV], env
    )


def storage_path(path: Path) -> Path:
    """YAML'ın `storage` bölümünden veritabanı dosyası (§11.6)."""
    return _relative(path, StorageConfig.model_validate(_read(path).get("storage")).path)
