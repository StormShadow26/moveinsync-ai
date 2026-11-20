"""Integration test; TEST_POSTGRES_* URLs must point to a disposable database."""

import os
from unittest import skipUnless

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from moveinsync_ai.database.models import Base
from moveinsync_ai.database.rls import PostgresRlsPolicyInstaller, PostgresTenantScopeSetter
from moveinsync_ai.database.session import create_schema
from moveinsync_ai.config import Settings
from moveinsync_ai.query_agent.contracts import QueryAgentError, QueryScope
from moveinsync_ai.query_agent.sql_executor import RlsSqlExecutor
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator


@skipUnless(os.getenv("TEST_POSTGRES_ADMIN_URL") and os.getenv("TEST_POSTGRES_APP_URL"), "Disposable PostgreSQL database not configured")
def test_postgres_scopes_and_privileged_role_rejection() -> None:
    admin = create_engine(os.environ["TEST_POSTGRES_ADMIN_URL"])
    app = create_engine(os.environ["TEST_POSTGRES_APP_URL"])
    create_schema(Settings(database_url=os.environ["TEST_POSTGRES_APP_URL"], schema_database_url=os.environ["TEST_POSTGRES_ADMIN_URL"], jwt_secret_key="test", jwt_algorithm="HS256", access_token_expire_minutes=30))
    with admin.begin() as connection:
        connection.execute(text("INSERT INTO companies (id, slug, name) VALUES (1001, 'rls-one', 'One'), (1002, 'rls-two', 'Two')"))

    sql = ReadOnlySqlValidator().validate("SELECT id FROM companies WHERE id IN (1001, 1002) ORDER BY id")
    with Session(app) as session:
        executor = RlsSqlExecutor(session, PostgresTenantScopeSetter(), 100, 10)
        assert executor.execute(sql, QueryScope(1, 1001, "single_company", [1001])).rows == [{"id": 1001}]
        assert executor.execute(sql, QueryScope(1, 1002, "single_company", [1002])).rows == [{"id": 1002}]
        assert executor.execute(sql, QueryScope(1, None, "all_companies", [1001])).rows == [{"id": 1001}]
        assert executor.execute(sql, QueryScope(1, None, "all_companies", [1001, 1002])).rows == [{"id": 1001}, {"id": 1002}]
        session.execute(text("SET LOCAL ROLE moveinsync_query"))
        assert not session.scalar(text("SELECT has_table_privilege(current_user, 'public.trips', 'INSERT,UPDATE,DELETE')"))
        assert not session.scalar(text("SELECT has_table_privilege(current_user, 'public.users', 'SELECT')"))
        session.execute(text("RESET ROLE"))
    with Session(admin) as session:
        try:
            RlsSqlExecutor(session, PostgresTenantScopeSetter(), 100, 10).execute(sql, QueryScope(1, 1, "single_company", [1]))
        except QueryAgentError:
            pass
        else:
            raise AssertionError("A superuser must not execute generated SQL")
