"""Curated transport schema context retrieval for the first agent version."""

from .contracts import SchemaContextRetriever


SCHEMA_CONTEXT = """
All operational tables are tenant-scoped by company_id. Never add a company filter yourself: PostgreSQL row-level security applies it.

companies(id, slug, name)
vendors(id, company_id, code, name, contact_email)
vehicles(id, company_id, vendor_id, registration_number, model, seating_capacity, is_active)
routes(id, company_id, code, origin, destination, distance_km, is_active)
employees(id, company_id, employee_code, display_name, office_location, is_active)
trips(id, company_id, route_id, vendor_id, vehicle_id, trip_number, scheduled_pickup_at, scheduled_drop_at, actual_pickup_at, actual_drop_at, status, vendor_cost)
trip_bookings(id, company_id, trip_id, employee_id, status)

Relations: trips.route_id -> routes.id; trips.vendor_id -> vendors.id; trips.vehicle_id -> vehicles.id;
trip_bookings.trip_id -> trips.id; trip_bookings.employee_id -> employees.id; vehicles.vendor_id -> vendors.id.
Trip status is scheduled, completed, delayed, or cancelled. Booking status is booked, boarded, no_show, or cancelled.
For attendance metrics use trip_bookings.status. For no-shows use status = 'no_show'. For boarded passengers use status = 'boarded'.
Use PostgreSQL SQL. Return data only from the listed tables. Prefer explicit columns, appropriate joins, grouping, and dates derived from scheduled_pickup_at.
""".strip()


class CuratedSchemaRetriever:
    """Provides the reviewed schema contract; replaceable with vector retrieval later."""

    def retrieve(self, question: str) -> str:
        return SCHEMA_CONTEXT
