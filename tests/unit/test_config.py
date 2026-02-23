"""Unit tests for config.py"""

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
