"""Additional company-scoped transport tables and their relationships."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Table

from .base import Base


def transport_table(name: str, *columns: Column) -> Table:
    return Table(name, Base.metadata, Column("id", Integer, primary_key=True),
                 Column("company_id", ForeignKey("companies.id"), nullable=False, index=True), *columns)


cities = transport_table("cities", Column("name", String(100), nullable=False))
drivers = transport_table("drivers", Column("vendor_id", ForeignKey("vendors.id"), nullable=False), Column("name", String(100), nullable=False))
shifts = transport_table("shifts", Column("name", String(100), nullable=False), Column("start_hour", Integer, nullable=False), Column("end_hour", Integer, nullable=False))
rosters = transport_table("rosters", Column("route_id", ForeignKey("routes.id"), nullable=False), Column("shift_id", ForeignKey("shifts.id"), nullable=False), Column("name", String(100), nullable=False))
roster_entries = transport_table("roster_entries", Column("roster_id", ForeignKey("rosters.id"), nullable=False), Column("employee_id", ForeignKey("employees.id"), nullable=False))
invoices = transport_table("invoices", Column("vendor_id", ForeignKey("vendors.id"), nullable=False), Column("invoice_number", String(50), nullable=False), Column("issued_at", DateTime(timezone=True), nullable=False))
invoice_lines = transport_table("invoice_lines", Column("invoice_id", ForeignKey("invoices.id"), nullable=False), Column("trip_id", ForeignKey("trips.id"), nullable=False), Column("amount", Numeric(10, 2), nullable=False))
trip_events = transport_table("trip_events", Column("trip_id", ForeignKey("trips.id"), nullable=False), Column("event_type", String(50), nullable=False), Column("occurred_at", DateTime(timezone=True), nullable=False))
