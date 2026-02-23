"""Unit tests for crud/database.py"""

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session

from mdpub.crud.database import get_session, init_db, make_engine


SQLITE_MEM = "sqlite://"


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
