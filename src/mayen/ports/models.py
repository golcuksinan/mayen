"""Model deposunun sözlüğü (§8.9) ve rolleri (§8.10)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, SecretStr

# Anahtar istemeyen yerel sunucuda da OpenAI istemcisi boş olmayan bir anahtar ister.
NO_KEY = "none"


class ModelRole(StrEnum):
    """Her model isteği bu rollerden biri için gider (§8.10)."""

    REASONER = "reasoner"
    TALKER = "talker"


class _Strict(BaseModel):
    # Yanlış yazılmış bir ayar sessizce yok sayılırsa model sunucunun varsayılanıyla çalışır.
    model_config = ConfigDict(extra="forbid", frozen=True)


class Thinking(_Strict):
    """Düşünmenin bu modelde nasıl açılıp kapandığı: isteğe eklenecek alanlar."""

    # `on`/`off` olmaz: YAML onları anahtar olarak true/false okur.
    enabled: dict[str, Any] = {}
    disabled: dict[str, Any] = {}


class RoleSettings(_Strict):
    """Bir rolün bu modeldeki ayarları; her istekte gönderilir (§8.10)."""

    thinking: bool
    sampling: dict[str, Any] = {}
    slot: int | None = None


class ModelRecord(_Strict):
    """Depodaki tek model (§8.9)."""

    base_url: str
    model: str
    context_tokens: int
    api_key_env: str | None = None  # anahtarın kendisi değil, ortam değişkeninin adı (§14)
    slot_field: str | None = None  # sunucunun yuva seçtiği gövde alanı; yuvası yoksa yok
    thinking: Thinking = Thinking()
    developer_role: bool = True  # şablon ortadaki geliştirici/sistem mesajını kabul ediyor mu
    roles: dict[ModelRole, RoleSettings]


@dataclass(frozen=True)
class Endpoint:
    """Bir rolün tek bir istekte kullandığı her şey; istemci bundan kurulur."""

    role: ModelRole
    base_url: str
    model: str
    context_tokens: int
    developer_role: bool
    body: Mapping[str, Any] = field(default_factory=dict)  # örnekleme, düşünme, yuva
    api_key: SecretStr | None = None


@dataclass(frozen=True)
class ModelCall:
    """Modelin istediği tek tool çağrısı; argümanlar modelin yazdığı ham metindir."""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ModelReply:
    text: str
    calls: Sequence[ModelCall] = ()


class ChatModel(Protocol):
    """Hattın dışından tek bir model isteği (replay, §14). Mesajlar OpenAI biçimindedir;
    sistem promptu ve bağlam bloğu mesajların içindedir."""

    async def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        tool_choice: str,
    ) -> ModelReply: ...
