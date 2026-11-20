"""Reproducible demo records; only seeds an empty development database."""

from datetime import datetime, timezone
from sqlalchemy import Engine, insert, select, func

from .models import Base


def seed_demo(engine: Engine) -> None:
    tables = Base.metadata.tables
    with engine.begin() as connection:
        if connection.scalar(select(func.count()).select_from(tables["companies"])):
            return

        def add(table: str, **values) -> int:
            return connection.execute(insert(tables[table]).values(**values).returning(tables[table].c.id)).scalar_one()

        now = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)
        company_ids = []
        for index, name in enumerate(("Acme India", "Globex India", "NBH"), 1):
            company = add("companies", name=name, slug=f"demo-{index}")
            company_ids.append(company)
            common = {"company_id": company}
            vendor = add("vendors", **common, code=f"V{index}", name=f"Fleet {index}")
            city = add("cities", **common, name="Bengaluru" if index < 3 else "Pune")
            add("drivers", **common, vendor_id=vendor, name=f"Driver {index}")
            vehicle = add("vehicles", **common, vendor_id=vendor, registration_number=f"DEMO-{index}", model="Shuttle", seating_capacity=4)
            route = add("routes", **common, city_id=city, code=f"R{index}", origin=f"Origin {index}", destination="Office", distance_km=10 + index)
            shift = add("shifts", **common, name="Morning", start_hour=8, end_hour=17)
            roster = add("rosters", **common, route_id=route, shift_id=shift, name=f"Roster {index}")
            employee = add("employees", **common, employee_code=f"E{index}", display_name=f"Employee {index}", office_location="Office")
            add("roster_entries", **common, roster_id=roster, employee_id=employee)
            trip = add("trips", **common, route_id=route, vendor_id=vendor, vehicle_id=vehicle, trip_number=f"TRIP-{index}", scheduled_pickup_at=now, scheduled_drop_at=now, status="completed", vendor_cost=100 * index)
            add("trip_bookings", **common, trip_id=trip, employee_id=employee, status="boarded" if index != 2 else "no_show")
            invoice = add("invoices", **common, vendor_id=vendor, invoice_number=f"INV-{index}", issued_at=now)
            add("invoice_lines", **common, invoice_id=invoice, trip_id=trip, amount=100 * index)
            if index == 1:
                add("invoice_lines", **common, invoice_id=invoice, trip_id=trip, amount=10)
            add("trip_events", **common, trip_id=trip, event_type="drop", occurred_at=now)
            add("users", email=f"admin{index}@example.com", user_type="client_transport_admin", company_id=company)
        manager = add("users", email="ops@example.com", user_type="internal_ops_manager", company_id=None)
        connection.execute(insert(tables["user_companies"]), [{"user_id": manager, "company_id": company} for company in company_ids[:2]])
