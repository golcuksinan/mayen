"""Model deposu (§8.9, §8.10): config'ten rol başına istek ayarları."""

from pathlib import Path

import pytest
from openai import NOT_GIVEN
from pipecat.adapters.services.open_ai_adapter import OpenAILLMInvocationParams
from pydantic import ValidationError

from mayen.app.config import load_models
from mayen.core.models import ModelConfigError, ModelRegistry
from mayen.pipeline.llm import llm_service
from mayen.ports.models import ModelRecord, ModelRole

CONFIG = """
models:
  gemma:
    base_url: http://127.0.0.1:8080/v1
    model: insta-bot-gemma26
    context_tokens: 16384
    slot_field: id_slot
    developer_role: false
    thinking:
      enabled: {chat_template_kwargs: {enable_thinking: true}}
      disabled: {chat_template_kwargs: {enable_thinking: false}}
    roles:
      talker: {thinking: false, slot: 0, sampling: {temperature: 1.0, top_k: 64}}
      reasoner: {thinking: true, slot: 1, sampling: {temperature: 0.6}}
  cloud:
    base_url: https://example.invalid/v1
    model: big
    context_tokens: 131072
    api_key_env: CLOUD_KEY
    roles:
      talker: {thinking: false}
      reasoner: {thinking: false}
"""


def registry(tmp_path: Path, active: str = "gemma", **env: str) -> ModelRegistry:
    path = tmp_path / "config.yaml"
    path.write_text(CONFIG, encoding="utf-8")
    return load_models(path, {"MAYEN_MODEL": active, **env})


def record(**roles: dict[str, object]) -> ModelRecord:
    return ModelRecord.model_validate(
        {
            "base_url": "http://x/v1",
            "model": "m",
            "context_tokens": 8192,
            "slot_field": "id_slot",
            "roles": roles,
        }
    )


def test_each_role_carries_its_own_settings_in_every_request(tmp_path: Path) -> None:
    models = registry(tmp_path)
    talker = models.endpoint(ModelRole.TALKER)
    reasoner = models.endpoint(ModelRole.REASONER)
    assert talker.body == {
        "temperature": 1.0,
        "top_k": 64,
        "chat_template_kwargs": {"enable_thinking": False},
        "id_slot": 0,
    }
    assert reasoner.body == {
        "temperature": 0.6,
        "chat_template_kwargs": {"enable_thinking": True},
        "id_slot": 1,
    }
    assert talker.model == "insta-bot-gemma26"
    assert talker.context_tokens == 16384
    assert not talker.developer_role
    assert talker.api_key is None


def test_active_model_comes_from_the_environment(tmp_path: Path) -> None:
    with pytest.raises(ModelConfigError, match="MAYEN_MODEL"):
        load_models(tmp_path / "missing.yaml", {})
    with pytest.raises(ModelConfigError, match="not in the registry"):
        registry(tmp_path, "nonexistent")


def test_api_key_is_read_from_the_named_variable_and_masked(tmp_path: Path) -> None:
    with pytest.raises(ModelConfigError, match="CLOUD_KEY"):
        registry(tmp_path, "cloud")
    key = registry(tmp_path, "cloud", CLOUD_KEY="sk-secret").endpoint(ModelRole.TALKER).api_key
    assert key is not None
    assert key.get_secret_value() == "sk-secret"
    assert "sk-secret" not in repr(key)


def test_misspelled_setting_is_an_error_not_a_server_default() -> None:
    with pytest.raises(ValidationError):
        ModelRecord.model_validate(
            {"base_url": "x", "model": "m", "context_tokens": 1, "roles": {}, "temprature": 0.1}
        )
    with pytest.raises(ValidationError):
        record(talker={"thinking": False, "temprature": 0.1})


def test_missing_role_fails_at_startup() -> None:
    with pytest.raises(ModelConfigError, match="reasoner"):
        ModelRegistry({"m": record(talker={"thinking": False})}, "m", {})


def test_two_roles_may_not_share_a_slot() -> None:
    shared = record(
        talker={"thinking": False, "slot": 0}, reasoner={"thinking": True, "slot": 0}
    )
    with pytest.raises(ModelConfigError, match="share a server slot"):
        ModelRegistry({"m": shared}, "m", {})


def test_slot_needs_the_servers_field_name() -> None:
    no_field = record(talker={"thinking": False, "slot": 0}, reasoner={"thinking": False})
    no_field = no_field.model_copy(update={"slot_field": None})
    with pytest.raises(ModelConfigError, match="slot_field"):
        ModelRegistry({"m": no_field}, "m", {})


def test_the_same_body_field_from_two_sources_is_an_error() -> None:
    clash = record(
        talker={"thinking": False, "sampling": {"id_slot": 3}, "slot": 0},
        reasoner={"thinking": False, "slot": 1},
    )
    with pytest.raises(ModelConfigError, match="id_slot"):
        ModelRegistry({"m": clash}, "m", {})


def test_pipecat_service_sends_the_role_settings(tmp_path: Path) -> None:
    endpoint = registry(tmp_path).endpoint(ModelRole.TALKER)
    service = llm_service(endpoint, "You are Mayen.")
    params = service.build_chat_completion_params(
        OpenAILLMInvocationParams(messages=[], tools=NOT_GIVEN, tool_choice=NOT_GIVEN)
    )
    assert params["model"] == "insta-bot-gemma26"
    assert params["extra_body"] == endpoint.body
    assert service.supports_developer_role is False
