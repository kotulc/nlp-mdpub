"""Unit tests for crud/database.py"""

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session

from mdpub.crud.database import get_session, get_url, init_db, make_engine


SQLITE_MEM = "sqlite://"


def test_get_url_returns_explicit(monkeypatch):
    """get_url returns the explicit URL when provided, ignoring env."""
    monkeypatch.delenv("MDPUB_DB_URL", raising=False)
    assert get_url("postgresql://host/db") == "postgresql://host/db"


def test_get_url_reads_env(monkeypatch):
    """get_url reads MDPUB_DB_URL from the environment when no arg is given."""
    monkeypatch.setenv("MDPUB_DB_URL", "sqlite:///env.db")
    assert get_url() == "sqlite:///env.db"


def test_get_url_defaults_to_sqlite(monkeypatch):
    """get_url returns the SQLite default when no arg or env var is configured."""
    monkeypatch.delenv("MDPUB_DB_URL", raising=False)
    assert get_url() == "sqlite:///mdpub.db"


def test_make_engine_returns_engine():
    """make_engine returns an SQLAlchemy Engine instance."""
    assert isinstance(make_engine(SQLITE_MEM), Engine)


def test_init_db_creates_tables():
    """init_db creates all expected tables on the engine."""
    engine = make_engine(SQLITE_MEM)
    init_db(engine)
    tables = set(SQLModel.metadata.tables.keys())
    for name in ("documents", "document_versions", "sections", "section_blocks"):
        assert name in tables


def test_get_session_yields_session():
    """get_session yields a usable SQLModel Session."""
    engine = make_engine(SQLITE_MEM)
    init_db(engine)
    session = next(get_session(engine))
    assert isinstance(session, Session)
