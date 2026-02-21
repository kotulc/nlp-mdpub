from __future__ import annotations
import os
from sqlmodel import Session, SQLModel, create_engine
from app.settings import get_settings


# Define database engine
settings = get_settings().database
engine = create_engine(settings.url, connect_args=settings.connect_args)


def init_database():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def make_engine(db_url: str):
    return create_engine(db_url, echo=False, future=True)


def get_db_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.getenv("mdpub_DB_URL")
    if env:
        return env
    return "sqlite:///./mdpub.db"


def create_tables(engine) -> None:
    SQLModel.metadata.create_all(engine)


def session_scope(engine) -> Session:
    return Session(engine)
