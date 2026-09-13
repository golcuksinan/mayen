"""Yapılandırma okuması ve sırların sızmaması."""

import logging
from pathlib import Path

import pytest

from mayen.config import Config, ConfigError, Secret, ServiceKind, load


def test_defaults_when_env_is_empty() -> None:
    cfg = load({})
    assert cfg == Config()
    assert cfg.openweathermap_key is None


def test_reads_values_from_env() -> None:
    cfg = load(
        {
            "MAYEN_LOG_LEVEL": "debug",
            "MAYEN_LOG_JSON": "true",
            "MAYEN_OPENWEATHERMAP_KEY": " abc123 ",
        }
    )
    assert cfg.log_level == logging.DEBUG
    assert cfg.log_json is True
    assert cfg.openweathermap_key is not None
    assert cfg.openweathermap_key.reveal() == "abc123"


def test_assume_owner_is_off_unless_asked_for() -> None:
    # §19.3'ün geçici kapısı: varsayılan kapalı, yoksa kimlik sessizce SAHİP olurdu.
    assert Config().assume_owner is False
    assert load({"MAYEN_ASSUME_OWNER": "true"}).assume_owner is True


def test_blank_secret_is_absent_not_empty() -> None:
    assert load({"MAYEN_OPENWEATHERMAP_KEY": "   "}).openweathermap_key is None


@pytest.mark.parametrize(
    "env",
    [{"MAYEN_LOG_LEVEL": "chatty"}, {"MAYEN_LOG_JSON": "belki"}],
)
def test_invalid_value_raises_instead_of_defaulting(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        load(env)


def test_reads_llm_url_and_drops_the_trailing_slash() -> None:
    assert (
        load({"MAYEN_LLM_URL": " http://127.0.0.1:9000/ "}).llm_url == "http://127.0.0.1:9000"
    )


def test_schemeless_llm_url_is_rejected() -> None:
    """Şemasız adres `httpx` tarafında göreli yol sayılır; hata ilk istekte, çok uzakta
    çıkardı (Kural 13)."""
    with pytest.raises(ConfigError):
        load({"MAYEN_LLM_URL": "127.0.0.1:8080"})


def test_schemeless_tts_url_is_rejected_and_names_its_own_variable() -> None:
    """Hata mesajı hangi değişkenin bozuk olduğunu söylemeli; iki adres var artık."""
    with pytest.raises(ConfigError, match="MAYEN_TTS_URL"):
        load({"MAYEN_TTS_URL": "127.0.0.1:8081"})


def test_service_kinds_default_to_fake_stt_and_real_tts() -> None:
    """§19.2'nin STT yarısı açık, TTS yarısı kapandı: varsayılanlar bunu söylüyor."""
    cfg = load({})
    assert cfg.stt is ServiceKind.FAKE
    assert cfg.tts is ServiceKind.REAL


def test_service_kinds_are_read_from_the_environment() -> None:
    cfg = load({"MAYEN_STT": " REAL ", "MAYEN_TTS": "fake"})
    assert cfg.stt is ServiceKind.REAL
    assert cfg.tts is ServiceKind.FAKE


def test_an_unknown_service_kind_is_rejected() -> None:
    """`--tts gercek` yazan kişinin sessizce sahteyle koşması fark edilmeyecek bir
    yanlışlık olurdu (Kural 13)."""
    with pytest.raises(ConfigError, match="fake/real"):
        load({"MAYEN_TTS": "gercek"})


def test_reads_database_and_backup_settings() -> None:
    cfg = load(
        {
            "MAYEN_DB_PATH": "/veri/mayen.db",
            "MAYEN_BACKUP_DIR": "/veri/yedek",
            "MAYEN_BACKUP_KEEP": "3",
            "MAYEN_BACKUP_INTERVAL_MINUTES": "60",
        }
    )
    assert cfg.db_path == Path("/veri/mayen.db")
    assert cfg.backup_dir == Path("/veri/yedek")
    assert (cfg.backup_keep, cfg.backup_interval_minutes) == (3, 60)


@pytest.mark.parametrize(
    "env",
    [
        {"MAYEN_BACKUP_KEEP": "üç"},
        {"MAYEN_BACKUP_KEEP": "0"},
        {"MAYEN_BACKUP_KEEP": "-1"},
        {"MAYEN_BACKUP_INTERVAL_MINUTES": "0"},
    ],
)
def test_non_positive_counts_are_rejected(env: dict[str, str]) -> None:
    """`keep=0` sessizce kabul edilirse yedek kalmaz ve bu ancak lazım olunca fark edilir."""
    with pytest.raises(ConfigError):
        load(env)


def test_secret_never_appears_in_repr_or_str() -> None:
    secret = Secret("kesinlikle-gizli")
    assert "kesinlikle-gizli" not in repr(secret)
    assert "kesinlikle-gizli" not in str(secret)
    cfg = load({"MAYEN_OPENWEATHERMAP_KEY": "kesinlikle-gizli"})
    assert "kesinlikle-gizli" not in repr(cfg)
