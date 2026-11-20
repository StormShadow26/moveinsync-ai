"""Deterministic, offline evaluation against the empty-database demo seed.

Run inside the API container: python /app/evaluation/run.py
"""
import json
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from moveinsync_ai.database.rls import tenant_scope_setter
from moveinsync_ai.query_agent.contracts import QueryScope
from moveinsync_ai.query_agent.sql_executor import RlsSqlExecutor
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator


# Expected values are independently calculated from demo_seed.py.
CASES = [
    ("trip_count", "How many trips can this manager see?", "SELECT count(*) AS value FROM trips", [1, 2], None, 2),
    ("client_count", "How many trips does Acme have?", "SELECT count(*) AS value FROM trips", [1], 1, 1),
    ("cross_company", "Show company 3 trips", "SELECT trip_number FROM trips WHERE company_id = 3", [1], 1, []),
    ("manager_subset", "Show company 3 trips across my companies", "SELECT trip_number FROM trips WHERE company_id = 3", [1, 2], None, []),
    ("no_shows", "How many no-shows?", "SELECT count(*) AS value FROM trip_bookings WHERE status = 'no_show'", [1, 2], None, 1),
    ("vendor_cost", "Total vendor cost?", "SELECT sum(vendor_cost) AS value FROM trips", [1, 2], None, 300),
    ("join", "How many trips use Fleet 1?", "SELECT count(*) AS value FROM trips JOIN vendors ON trips.vendor_id = vendors.id WHERE vendors.name = 'Fleet 1'", [1, 2], None, 1),
    ("dates", "How many trips before 2026?", "SELECT count(*) AS value FROM trips WHERE scheduled_pickup_at < '2026-01-01'", [1, 2], None, 0),
    ("nulls", "How many trips have no actual pickup?", "SELECT count(*) AS value FROM trips WHERE actual_pickup_at IS NULL", [1, 2], None, 2),
    ("dedup", "How many different trips have invoice lines?", "SELECT count(DISTINCT trips.id) AS value FROM trips JOIN invoice_lines ON invoice_lines.trip_id = trips.id", [1, 2], None, 2),
    ("occupancy", "What is the occupancy of trip 1?", "SELECT 1.0 * count(*) / max(vehicles.seating_capacity) AS value FROM trip_bookings JOIN trips ON trip_bookings.trip_id = trips.id JOIN vehicles ON trips.vehicle_id = vehicles.id WHERE trips.trip_number = 'TRIP-1' AND trip_bookings.status = 'boarded'", [1], 1, 0.25),
]


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    failures = 0
    with Session(engine) as session:
        executor = RlsSqlExecutor(session, tenant_scope_setter, 100, 10)
        for case_id, question, sql, companies, company, expected in CASES:
            try:
                scope = QueryScope(1, company, "single_company" if company else "all_companies", companies)
                result = executor.execute(ReadOnlySqlValidator().validate(sql), scope)
                actual = result.rows if expected == [] else result.rows[0]["value"]
                actual = float(actual) if actual is not None and expected != [] else actual
                passed = actual == expected
                notes = "Deterministic SQL; does not measure model generation."
            except Exception as error:
                session.rollback()
                actual, passed, notes = None, False, type(error).__name__
            failures += not passed
            print(json.dumps({"id": case_id, "input": question, "expected": expected, "actual": actual, "pass": passed, "notes": notes}))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
