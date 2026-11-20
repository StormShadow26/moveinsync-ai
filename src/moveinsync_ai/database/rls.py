"""PostgreSQL row-level security for tenant-owned operational data."""

from typing import Protocol

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

TENANT_TABLE_COLUMNS = {
    "companies": ("id", None),
    "vendors": ("company_id", None),
    "vehicles": ("company_id", None),
    "routes": ("company_id", None),
    "employees": ("company_id", None),
    "trips": ("company_id", None),
    "trip_bookings": ("company_id", None),
    **{table: ("company_id", None) for table in ("cities", "drivers", "shifts", "rosters", "roster_entries", "invoices", "invoice_lines", "trip_events")},
    "query_threads": ("company_id", "user_id"),
    "query_messages": ("company_id", "user_id"),
}
POLICY_NAME = "tenant_isolation"


class RlsPolicyInstaller(Protocol):
    """Install tenant-isolation policies for a database engine."""

    def install(self, engine: Engine) -> None: ...


class TenantScopeSetter(Protocol):
    """Apply the authenticated scope to the current database transaction."""

    def apply(self, session: Session, user_id: int, company_id: int | None, access_scope: str, company_ids: list[int]) -> None: ...


class PostgresRlsPolicyInstaller:
    """Enable and force PostgreSQL RLS on tables containing client data."""

    def install(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            return
        with engine.begin() as connection:
            for table, (company_column, user_column) in TENANT_TABLE_COLUMNS.items():
                connection.exec_driver_sql(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                connection.exec_driver_sql(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
                tenant_predicate = (
                    f"{company_column} = ANY(string_to_array(NULLIF(current_setting('app.company_ids', true), ''), ',')::integer[]) "
                    "AND (current_setting('app.access_scope', true) = 'all_companies' "
                    f"OR {company_column} = NULLIF(current_setting('app.company_id', true), '')::integer)"
                )
                predicate = f"({tenant_predicate})"
                if user_column:
                    predicate = f"({company_column} IS NULL OR {predicate}) AND {user_column} = NULLIF(current_setting('app.user_id', true), '')::integer"
                connection.exec_driver_sql(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table}")
                connection.exec_driver_sql(f"CREATE POLICY {POLICY_NAME} ON {table} USING ({predicate}) WITH CHECK ({predicate})")


class PostgresTenantScopeSetter:
    """Set PostgreSQL RLS variables for a single request transaction."""

    def apply(self, session: Session, user_id: int, company_id: int | None, access_scope: str, company_ids: list[int]) -> None:
        if session.get_bind().dialect.name != "postgresql":
            return
        session.execute(text("SELECT set_config('app.access_scope', :scope, true)"), {"scope": access_scope})
        session.execute(text("SELECT set_config('app.user_id', :user_id, true)"), {"user_id": str(user_id)})
        session.execute(text("SELECT set_config('app.company_ids', :company_ids, true)"), {"company_ids": ",".join(map(str, company_ids))})
        session.execute(
            text("SELECT set_config('app.company_id', :company_id, true)"),
            {"company_id": "" if company_id is None else str(company_id)},
        )


rls_policy_installer: RlsPolicyInstaller = PostgresRlsPolicyInstaller()
tenant_scope_setter: TenantScopeSetter = PostgresTenantScopeSetter()
