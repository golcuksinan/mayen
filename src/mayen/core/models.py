"""Model deposu: rol için model, yuva ve ayarları çözer (§8.9, §8.10)."""

from collections.abc import Mapping
from typing import Any

from pydantic import SecretStr

from mayen.ports.models import Endpoint, ModelRecord, ModelRole


class ModelConfigError(ValueError):
    """Depo, etkin model ya da rol eşlemesi tutarsız; açılışta yükselir."""


class ModelRegistry:
    def __init__(
        self, records: Mapping[str, ModelRecord], active: str, env: Mapping[str, str]
    ) -> None:
        if active not in records:
            raise ModelConfigError(f"active model {active!r} is not in the registry")
        self._record = records[active]
        self._name = active
        self._api_key = self._key(env)
        self._check_slots()
        # Eksik rol, ilk istekte değil açılışta görünsün.
        self._endpoints = {role: self._endpoint(role) for role in ModelRole}

    @property
    def active(self) -> str:
        return self._name

    def endpoint(self, role: ModelRole) -> Endpoint:
        return self._endpoints[role]

    def _key(self, env: Mapping[str, str]) -> SecretStr | None:
        name = self._record.api_key_env
        if name is None:
            return None
        if name not in env:
            raise ModelConfigError(f"environment variable {name} is not set")
        return SecretStr(env[name])

    def _check_slots(self) -> None:
        """İki rol tek yuvayı paylaşırsa her geçiş ötekinin önbelleğini düşürür (§8.10)."""
        slots = [s.slot for s in self._record.roles.values() if s.slot is not None]
        if len(slots) != len(set(slots)):
            raise ModelConfigError(f"{self._name}: two roles share a server slot")
        if slots and self._record.slot_field is None:
            raise ModelConfigError(f"{self._name}: slots are set but slot_field is not")

    def _endpoint(self, role: ModelRole) -> Endpoint:
        record = self._record
        settings = record.roles.get(role)
        if settings is None:
            raise ModelConfigError(f"{self._name}: no settings for role {role}")
        thinking = record.thinking.enabled if settings.thinking else record.thinking.disabled
        parts: list[Mapping[str, Any]] = [settings.sampling, thinking]
        if settings.slot is not None:
            assert record.slot_field is not None
            parts.append({record.slot_field: settings.slot})
        return Endpoint(
            role=role,
            base_url=record.base_url,
            model=record.model,
            context_tokens=record.context_tokens,
            developer_role=record.developer_role,
            body=_merge(self._name, parts),
            api_key=self._api_key,
        )


def _merge(name: str, parts: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aynı alanı iki kaynak verirse hangisinin kazandığı belirsiz kalmasın diye hata."""
    body: dict[str, Any] = {}
    for part in parts:
        clash = body.keys() & part.keys()
        if clash:
            raise ModelConfigError(f"{name}: {sorted(clash)} set twice in the request body")
        body.update(part)
    return body
