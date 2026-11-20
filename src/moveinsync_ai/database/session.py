"""Database setup and session helpers."""

from functools import lru_cache
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from ..config import Settings
from .models import Base
from .rls import rls_policy_installer
from .demo_seed import seed_demo
import os


@lru_cache()
def get_engine(database_url: str):
    """Create a reusable engine for one database URL."""
    options: Dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, pool_pre_ping=True, **options)


def create_schema(settings: Settings) -> None:
    """Create tables and apply the temporary passwordless-auth compatibility change."""
    engine = get_engine(settings.schema_database_url or settings.database_url)
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql" and "city_id" not in {column["name"] for column in inspect(engine).get_columns("routes")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE routes ADD COLUMN city_id INTEGER REFERENCES cities(id)"))
    password_column = next((column for column in inspect(engine).get_columns("users") if column["name"] == "password_hash"), None)
    if password_column and not password_column["nullable"] and engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))
    if engine.dialect.name == "postgresql":
        from ..query_agent.sql_validator import ALLOWED_TABLES
        app_role = engine.dialect.identifier_preparer.quote(make_url(settings.database_url).username)
        tables = ", ".join(f"public.{engine.dialect.identifier_preparer.quote(name)}" for name in sorted(ALLOWED_TABLES))
        with engine.begin() as connection:
            connection.exec_driver_sql("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'moveinsync_query') THEN CREATE ROLE moveinsync_query NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS; END IF; END $$")
            connection.exec_driver_sql(f"GRANT moveinsync_query TO {app_role}")
            connection.exec_driver_sql("GRANT USAGE ON SCHEMA public TO moveinsync_query")
            connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {app_role}")
            connection.exec_driver_sql(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {app_role}")
            connection.exec_driver_sql(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {app_role}")
            connection.exec_driver_sql(f"GRANT INSERT, UPDATE, DELETE ON public.login_otps, public.query_threads, public.query_messages TO {app_role}")
            connection.exec_driver_sql(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_role}")
            connection.exec_driver_sql("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM moveinsync_query")
            connection.exec_driver_sql(f"GRANT SELECT ON {tables} TO moveinsync_query")
    rls_policy_installer.install(engine)
    if os.getenv("SEED_DEMO") == "1":
        seed_demo(engine)


def get_session(settings: Settings) -> Generator[Session, None, None]:
    """Yield a transaction-scoped database session."""
    factory = sessionmaker(bind=get_engine(settings.database_url), autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
