"""Database engine, session, and schema initialization"""

import os
from sqlmodel import Session, SQLModel, create_engine


SQLITE_DEFAULT = "sqlite:///mdpub.db"


def get_url(explicit: str | None = None) -> str:
    """Resolve DB URL from arg, MDPUB_DB_URL env var, or SQLite default."""
    return explicit or os.getenv("MDPUB_DB_URL") or SQLITE_DEFAULT


def make_engine(url: str | None = None):
    """Create SQLAlchemy engine. Resolves URL via get_url() if not provided."""
    return create_engine(get_url(url))


def init_db(engine) -> None:
    """Create all SQLModel tables on the given engine."""
    SQLModel.metadata.create_all(engine)


def get_session(engine):
    """Yield a SQLModel Session for the given engine."""
    with Session(engine) as session:
        yield session
