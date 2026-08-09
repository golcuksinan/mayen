"""Yapılandırma okuması ve sırların sızmaması."""

import logging
from pathlib import Path

import pytest

from mayen.config import Config, ConfigError, Secret, load


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


def test_blank_secret_is_absent_not_empty() -> None:
    assert load({"MAYEN_OPENWEATHERMAP_KEY": "   "}).openweathermap_key is None


@pytest.mark.parametrize(
    "env",
    [{"MAYEN_LOG_LEVEL": "chatty"}, {"MAYEN_LOG_JSON": "belki"}],
)
def test_invalid_value_raises_instead_of_defaulting(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        load(env)


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
