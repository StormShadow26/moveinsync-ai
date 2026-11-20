"""RLS-aware, bounded execution of validated read-only SQL."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database.rls import TenantScopeSetter
from .contracts import QueryResult, QueryScope, SqlExecutor


class RlsSqlExecutor:
    def __init__(self, session: Session, scope_setter: TenantScopeSetter, row_limit: int, timeout_seconds: int):
        self._session = session
        self._scope_setter = scope_setter
        self._row_limit = row_limit
        self._timeout_seconds = timeout_seconds

    def execute(self, sql: str, scope: QueryScope) -> QueryResult:
        self._scope_setter.apply(self._session, scope.user_id, scope.company_id, scope.access_scope)
        if self._session.get_bind().dialect.name == "postgresql":
            self._session.execute(text("SELECT set_config('statement_timeout', :timeout, true)"), {"timeout": f"{self._timeout_seconds}s"})
        result = self._session.execute(text(f"SELECT * FROM ({sql}) AS moveinsync_query LIMIT :limit"), {"limit": self._row_limit})
        return QueryResult(list(result.keys()), [dict(row._mapping) for row in result])
