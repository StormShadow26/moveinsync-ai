"""RLS-aware, bounded execution of validated read-only SQL."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database.rls import TenantScopeSetter
from .contracts import QueryAgentError, QueryResult, QueryScope, SqlExecutor


class RlsSqlExecutor:
    def __init__(self, session: Session, scope_setter: TenantScopeSetter, row_limit: int, timeout_seconds: int):
        self._session = session
        self._scope_setter = scope_setter
        self._row_limit = max(1, min(row_limit, 500))
        self._timeout_seconds = max(1, min(timeout_seconds, 10))

    def execute(self, sql: str, scope: QueryScope) -> QueryResult:
        if self._session.get_bind().dialect.name != "postgresql":
            raise QueryAgentError("Data queries require PostgreSQL row-level security")
        unsafe_role = self._session.execute(text(
            "SELECT rolsuper OR rolbypassrls FROM pg_catalog.pg_roles WHERE rolname = current_user"
        )).scalar_one()
        if unsafe_role:
            raise QueryAgentError("Data queries require a PostgreSQL role that cannot bypass row-level security")
        self._scope_setter.apply(self._session, scope.user_id, scope.company_id, scope.access_scope, scope.company_ids)
        search_path = self._session.execute(text("SELECT pg_catalog.current_setting('search_path')")).scalar_one()
        self._session.execute(text("SELECT pg_catalog.set_config('search_path', 'pg_catalog', true)"))
        self._session.execute(text("SELECT pg_catalog.set_config('statement_timeout', :timeout, true)"), {"timeout": f"{self._timeout_seconds}s"})
        self._session.execute(text("SET LOCAL ROLE moveinsync_query"))
        result = self._session.execute(text(f"SELECT * FROM ({sql}) AS moveinsync_query LIMIT :limit"), {"limit": self._row_limit})
        query_result = QueryResult(list(result.keys()), [dict(row._mapping) for row in result])
        self._session.execute(text("RESET ROLE"))
        self._session.execute(text("SELECT pg_catalog.set_config('search_path', :path, true)"), {"path": search_path})
        return query_result
