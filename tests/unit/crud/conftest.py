"""Shared fixtures for crud unit tests"""

import pytest
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from mdpub.crud.models import Document
from mdpub.core.utils.hashing import sha256


@pytest.fixture(name="engine")
def engine_fixture():
    """In-memory SQLite engine with all tables created."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    """Fresh session per test; changes are not committed."""
    with Session(engine) as s:
        yield s


@pytest.fixture(name="doc")
def doc_fixture(session):
    """A minimal Document persisted to the session."""
    d = Document(slug="test-doc", markdown="# Hello\n\nWorld", hash=sha256("# Hello\n\nWorld"), path="docs/test-doc.md")
    session.add(d)
    session.flush()
    return d
