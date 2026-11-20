"""Curated transport schema and deterministic question-based retrieval."""

import re
import hashlib
from functools import lru_cache

TABLES = {
    "companies": "companies(id, slug, name)",
    "vendors": "vendors(id, company_id, code, name, contact_email)",
    "vehicles": "vehicles(id, company_id, vendor_id, registration_number, model, seating_capacity, is_active)",
    "routes": "routes(id, company_id, city_id, code, origin, destination, distance_km, is_active)",
    "employees": "employees(id, company_id, employee_code, display_name, office_location, is_active)",
    "trips": "trips(id, company_id, route_id, vendor_id, vehicle_id, trip_number, scheduled_pickup_at, scheduled_drop_at, actual_pickup_at, actual_drop_at, status, vendor_cost)",
    "trip_bookings": "trip_bookings(id, company_id, trip_id, employee_id, status)",
    "cities": "cities(id, company_id, name)",
    "drivers": "drivers(id, company_id, vendor_id, name)",
    "shifts": "shifts(id, company_id, name, start_hour, end_hour)",
    "rosters": "rosters(id, company_id, route_id, shift_id, name)",
    "roster_entries": "roster_entries(id, company_id, roster_id, employee_id)",
    "invoices": "invoices(id, company_id, vendor_id, invoice_number, issued_at)",
    "invoice_lines": "invoice_lines(id, company_id, invoice_id, trip_id, amount)",
    "trip_events": "trip_events(id, company_id, trip_id, event_type, occurred_at)",
}

TOPICS = {
    "companies": {"company", "companies", "client", "clients"},
    "vendors": {"vendor", "vendors", "supplier", "suppliers", "fleet", "fleets", "cost", "costs", "spend", "spending"},
    "vehicles": {"vehicle", "vehicles", "cab", "cabs", "car", "cars", "capacity", "occupancy"},
    "routes": {"route", "routes", "distance", "origin", "destination"},
    "employees": {"employee", "employees", "staff", "passenger", "passengers"},
    "trips": {"trip", "trips", "journey", "journeys", "pickup", "drop", "delay", "delayed"},
    "trip_bookings": {"booking", "bookings", "attendance", "boarded", "noshow", "noshows", "occupancy"},
    "cities": {"city", "cities", "bangalore", "bengaluru"},
    "drivers": {"driver", "drivers"},
    "shifts": {"shift", "shifts", "night"},
    "rosters": {"roster", "rosters"},
    "roster_entries": {"roster", "rosters"},
    "invoices": {"invoice", "invoices", "billing"},
    "invoice_lines": {"invoice", "invoices", "billing"},
    "trip_events": {"event", "events", "drop", "drops"},
}

RELATIONS = (
    ("trips", "routes", "trips.route_id -> routes.id"),
    ("routes", "cities", "routes.city_id -> cities.id"),
    ("trips", "vendors", "trips.vendor_id -> vendors.id"),
    ("trips", "vehicles", "trips.vehicle_id -> vehicles.id"),
    ("trip_bookings", "trips", "trip_bookings.trip_id -> trips.id"),
    ("trip_bookings", "employees", "trip_bookings.employee_id -> employees.id"),
    ("vehicles", "vendors", "vehicles.vendor_id -> vendors.id"),
    ("drivers", "vendors", "drivers.vendor_id -> vendors.id"),
    ("rosters", "routes", "rosters.route_id -> routes.id"),
    ("rosters", "shifts", "rosters.shift_id -> shifts.id"),
    ("roster_entries", "rosters", "roster_entries.roster_id -> rosters.id"),
    ("roster_entries", "employees", "roster_entries.employee_id -> employees.id"),
    ("invoices", "vendors", "invoices.vendor_id -> vendors.id"),
    ("invoice_lines", "invoices", "invoice_lines.invoice_id -> invoices.id"),
    ("invoice_lines", "trips", "invoice_lines.trip_id -> trips.id"),
    ("trip_events", "trips", "trip_events.trip_id -> trips.id"),
)


class CuratedSchemaRetriever:
    """Select reviewed tables and joins, falling back to all tables for unknown terms."""

    def retrieve(self, question: str) -> str:
        words = set(re.findall(r"[a-z0-9]+", question.lower()))
        selected = {table for table, terms in TOPICS.items() if words & terms}
        if "no" in words and words & {"show", "shows"}:
            selected.add("trip_bookings")
        if words & {"cost", "costs", "spend", "spending"}:
            selected.add("trips")
        if "employees" in selected and selected & {"trips", "routes", "vehicles", "vendors"}:
            selected.add("trip_bookings")
        if not selected:
            selected = set(TABLES)
        elif len(selected) > 1 or "trip_bookings" in selected:
            selected.add("trips")
        sections = [
            "PostgreSQL RLS applies company scope; do not add a company filter.",
            "\n".join(description for table, description in TABLES.items() if table in selected),
        ]
        relations = [relation for left, right, relation in RELATIONS if {left, right} <= selected]
        if "companies" in selected:
            relations.extend(f"{table}.company_id -> companies.id" for table in TABLES if table in selected and table != "companies")
        if relations:
            sections.append("Allowed joins: " + "; ".join(relations) + ".")
        if "trip_bookings" in selected:
            sections.append("Booking status is booked, boarded, no_show, or cancelled. No-shows have status 'no_show'.")
        if "vendors" in selected:
            sections.append("vendors.name is the vendor or fleet display name; vendors.code is its short identifier.")
        if "companies" in selected:
            sections.append("companies.name is the company display name; companies.slug is its identifier.")
        if "trips" in selected:
            sections.append("Trip status is scheduled, completed, delayed, or cancelled. Vendor cost is trips.vendor_cost.")
        if {"trip_bookings", "vehicles"} <= selected:
            sections.append(
                "Occupancy = boarded employees / vehicle seating capacity; join bookings to trips and trips to vehicles. "
                "For one trip, use 1.0 * COUNT(*) / NULLIF(MAX(vehicles.seating_capacity), 0) "
                "with booking status 'boarded'. When combining aggregates with other selected columns, group those columns."
            )
        return "\n\n".join(sections)


def _embedding(value: str) -> list[float]:
    vector = [0.0] * 256
    for word in re.findall(r"[a-z0-9]+", value.lower()):
        index = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big") % len(vector)
        vector[index] += 1.0
    return vector


@lru_cache(maxsize=1)
def _schema_collection():
    import chromadb
    collection = chromadb.EphemeralClient().get_or_create_collection("transport_schema", metadata={"hnsw:space": "cosine"})
    documents = [f"{table} {description} {' '.join(sorted(TOPICS.get(table, set())))}" for table, description in TABLES.items()]
    collection.upsert(ids=list(TABLES), documents=documents, embeddings=[_embedding(document) for document in documents])
    return collection


class ChromaSchemaRetriever:
    """Retrieve related schema documents from Chroma and reuse reviewed join rules."""

    def __init__(self):
        self._curated = CuratedSchemaRetriever()

    def retrieve(self, question: str) -> str:
        result = _schema_collection().query(query_embeddings=[_embedding(question)], n_results=3)
        relevant = [table for table, distance in zip(result["ids"][0], result["distances"][0]) if distance < 0.8]
        terms = [sorted(TOPICS[table])[0] for table in relevant if table in TOPICS]
        return self._curated.retrieve(question + " " + " ".join(terms))
