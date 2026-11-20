"""Database setup and session helpers."""

from functools import lru_cache
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from ..config import Settings
from .models import Base


@lru_cache()
def get_engine(database_url: str):
    """Create a reusable engine for one database URL."""
    options: Dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, pool_pre_ping=True, **options)


def create_schema(settings: Settings) -> None:
    """Create tables and apply the temporary passwordless-auth compatibility change."""
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(engine)
    password_column = next((column for column in inspect(engine).get_columns("users") if column["name"] == "password_hash"), None)
    if password_column and not password_column["nullable"] and engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))


def get_session(settings: Settings) -> Generator[Session, None, None]:
    """Yield a transaction-scoped database session."""
    factory = sessionmaker(bind=get_engine(settings.database_url), autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
