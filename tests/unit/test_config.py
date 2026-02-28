"""Unit tests for config.py"""

import pytest

from mdpub.config import load_config


def test_load_config_uses_env_db_url(monkeypatch):
    """MDPUB_DB_URL env var is picked up by load_config."""
    monkeypatch.setenv("MDPUB_DB_URL", "sqlite:///env.db")
    settings = load_config()
    assert settings.db_url == "sqlite:///env.db"


def test_load_config_env_overrides_config_yaml(tmp_path, monkeypatch):
    """MDPUB_DB_URL takes precedence over config.yaml db_url."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("db_url: 'sqlite:///project.db'\n")
    monkeypatch.setenv("MDPUB_DB_URL", "sqlite:///override.db")
    settings = load_config()
    assert settings.db_url == "sqlite:///override.db"


def test_load_config_cli_overrides_env(monkeypatch):
    """A non-None CLI override beats the MDPUB_DB_URL env var."""
    monkeypatch.setenv("MDPUB_DB_URL", "sqlite:///env.db")
    settings = load_config(overrides={"db_url": "sqlite:///cli.db"})
    assert settings.db_url == "sqlite:///cli.db"


def test_load_config_defaults_to_sqlite(monkeypatch):
    """Settings default is used when no config.yaml, env var, or CLI override exists."""
    monkeypatch.delenv("MDPUB_DB_URL", raising=False)
    settings = load_config()
    assert settings.db_url == "sqlite:///mdpub.db"


def test_load_config_invalid_yaml(tmp_path, monkeypatch):
    """load_config raises ValueError when config.yaml contains invalid YAML."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("key: [unclosed\n")
    with pytest.raises(ValueError, match="Invalid config.yaml"):
        load_config()


# --- generalized env var pattern ---

def test_load_config_env_max_nesting(monkeypatch):
    """MDPUB_MAX_NESTING env var is coerced to int and applied to settings."""
    monkeypatch.setenv("MDPUB_MAX_NESTING", "3")
    settings = load_config()
    assert settings.max_nesting == 3


def test_load_config_env_output_format(monkeypatch):
    """MDPUB_OUTPUT_FORMAT env var is applied to settings."""
    monkeypatch.setenv("MDPUB_OUTPUT_FORMAT", "md")
    settings = load_config()
    assert settings.output_format == "md"


def test_load_config_env_max_tags(monkeypatch):
    """MDPUB_MAX_TAGS env var is coerced to int and applied to settings."""
    monkeypatch.setenv("MDPUB_MAX_TAGS", "5")
    settings = load_config()
    assert settings.max_tags == 5


def test_load_config_env_max_metrics(monkeypatch):
    """MDPUB_MAX_METRICS env var is coerced to int and applied to settings."""
    monkeypatch.setenv("MDPUB_MAX_METRICS", "2")
    settings = load_config()
    assert settings.max_metrics == 2


def test_load_config_env_overrides_config_yaml_max_nesting(tmp_path, monkeypatch):
    """MDPUB_MAX_NESTING env var takes precedence over config.yaml."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("max_nesting: 4\n")
    monkeypatch.setenv("MDPUB_MAX_NESTING", "2")
    settings = load_config()
    assert settings.max_nesting == 2


def test_load_config_cli_overrides_env_max_nesting(monkeypatch):
    """A non-None CLI override beats the MDPUB_MAX_NESTING env var."""
    monkeypatch.setenv("MDPUB_MAX_NESTING", "3")
    settings = load_config(overrides={"max_nesting": 1})
    assert settings.max_nesting == 1
