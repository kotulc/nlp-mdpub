"""Database engine and schema initialization"""

from sqlmodel import SQLModel, create_engine


def make_engine(url: str):
    """Create SQLAlchemy engine for the given URL."""
    return create_engine(url)


def init_db(engine) -> None:
    """Create all SQLModel tables on the given engine."""
    SQLModel.metadata.create_all(engine)
