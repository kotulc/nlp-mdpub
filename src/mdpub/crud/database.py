"""Database engine, session, and schema initialization"""

from sqlmodel import Session, SQLModel, create_engine


def make_engine(url: str):
    """Create SQLAlchemy engine for the given URL."""
    return create_engine(url)


def init_db(engine) -> None:
    """Create all SQLModel tables on the given engine."""
    SQLModel.metadata.create_all(engine)


def get_session(engine):
    """Yield a SQLModel Session for the given engine."""
    with Session(engine) as session:
        yield session
