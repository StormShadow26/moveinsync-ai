"""Query API integration against a disposable, initially empty PostgreSQL database."""

import json
import os
from unittest import skipUnless

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from moveinsync_ai.api.dependencies import database_session
from moveinsync_ai.api.routers.threads import query_agent
from moveinsync_ai.app import create_app
from moveinsync_ai.auth.security import JwtAccessTokenCodec
from moveinsync_ai.config import Settings
from moveinsync_ai.database.rls import tenant_scope_setter
from moveinsync_ai.query_agent.groq import GroqChatModel, GroqSqlGenerator
from moveinsync_ai.query_agent.schema_retrieval import CuratedSchemaRetriever
from moveinsync_ai.query_agent.service import LangGraphQueryAgent
from moveinsync_ai.query_agent.sql_executor import RlsSqlExecutor
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator


QUERIES = {
    "How many trips are there?": "SELECT COUNT(*) AS value FROM trips",
    "How many no-shows are there?": "SELECT COUNT(*) AS value FROM trip_bookings WHERE status = 'no_show'",
    "What is the total vendor cost?": "SELECT SUM(vendor_cost) AS value FROM trips",
    "Show company 3 trips": "SELECT trip_number FROM trips WHERE company_id = 3",
    "What is the occupancy of trip A-1?": (
        "SELECT 1.0 * COUNT(*) / MAX(vehicles.seating_capacity) AS value FROM trip_bookings "
        "JOIN trips ON trip_bookings.trip_id = trips.id JOIN vehicles ON trips.vehicle_id = vehicles.id "
        "WHERE trips.trip_number = 'A-1' AND trip_bookings.status = 'boarded'"
    ),
}


class KnownAnswerModel:
    """Provide fixed SQL while keeping the real graph, validator and executor in use."""

    def complete(self, prompt: str, *, json_output: bool = False) -> str:
        if json_output:
            question = prompt.split("\n\nQuestion: ", 1)[1].split("\n", 1)[0]
            return json.dumps({"sql": QUERIES[question], "reasoning_summary": "Known test query"})
        return "Result returned."


def seed(connection) -> None:
    statements = [
        "INSERT INTO companies (id, slug, name) VALUES (1, 'alpha', 'Alpha'), (2, 'beta', 'Beta'), (3, 'gamma', 'Gamma')",
        "INSERT INTO users (id, email, user_type, company_id) VALUES (1, 'alpha@test.example', 'client_transport_admin', 1), (2, 'beta@test.example', 'client_transport_admin', 2), (3, 'ops@test.example', 'internal_ops_manager', NULL)",
        "INSERT INTO vendors (id, company_id, code, name) VALUES (1, 1, 'VA', 'Alpha Vendor'), (2, 2, 'VB', 'Beta Vendor'), (3, 3, 'VC', 'Gamma Vendor')",
        "INSERT INTO vehicles (id, company_id, vendor_id, registration_number, model, seating_capacity) VALUES (1, 1, 1, 'A-CAB', 'A', 4), (2, 2, 2, 'B-CAB', 'B', 4), (3, 3, 3, 'C-CAB', 'C', 4)",
        "INSERT INTO routes (id, company_id, code, origin, destination, distance_km) VALUES (1, 1, 'RA', 'A', 'Office', 10), (2, 2, 'RB', 'B', 'Office', 20), (3, 3, 'RC', 'C', 'Office', 30)",
        "INSERT INTO employees (id, company_id, employee_code, display_name, office_location) VALUES (1, 1, 'A1', 'A1', 'Office'), (2, 1, 'A2', 'A2', 'Office'), (3, 1, 'A3', 'A3', 'Office'), (4, 2, 'B1', 'B1', 'Office'), (5, 2, 'B2', 'B2', 'Office')",
        "INSERT INTO trips (id, company_id, route_id, vendor_id, vehicle_id, trip_number, scheduled_pickup_at, scheduled_drop_at, status, vendor_cost) VALUES (1, 1, 1, 1, 1, 'A-1', '2026-01-01 08:00Z', '2026-01-01 09:00Z', 'completed', 100), (2, 1, 1, 1, 1, 'A-2', '2026-01-02 08:00Z', '2026-01-02 09:00Z', 'completed', 200), (3, 2, 2, 2, 2, 'B-1', '2026-01-01 08:00Z', '2026-01-01 09:00Z', 'completed', 500)",
        "INSERT INTO trips (id, company_id, route_id, vendor_id, vehicle_id, trip_number, scheduled_pickup_at, scheduled_drop_at, status, vendor_cost) VALUES (4, 3, 3, 3, 3, 'C-1', '2026-01-01 08:00Z', '2026-01-01 09:00Z', 'completed', 900)",
        "INSERT INTO trip_bookings (id, company_id, trip_id, employee_id, status) VALUES (1, 1, 1, 1, 'boarded'), (2, 1, 1, 2, 'boarded'), (3, 1, 1, 3, 'no_show'), (4, 2, 3, 4, 'no_show'), (5, 2, 3, 5, 'no_show')",
    ]
    for statement in statements:
        connection.execute(text(statement))


@skipUnless(os.getenv("TEST_POSTGRES_ADMIN_URL") and os.getenv("TEST_POSTGRES_APP_URL"), "Disposable PostgreSQL database not configured")
def test_postgres_api_scopes_and_queries() -> None:
    settings = Settings(
        database_url=os.environ["TEST_POSTGRES_APP_URL"], schema_database_url=os.environ["TEST_POSTGRES_ADMIN_URL"],
        jwt_secret_key="test-secret-key-with-at-least-thirty-two-characters", jwt_algorithm="HS256", access_token_expire_minutes=30,
        groq_api_key=os.getenv("GROQ_API_KEY"), groq_model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
    )
    app = create_app(settings)
    live = os.getenv("TEST_LIVE_GROQ") == "1"

    def agent(session=Depends(database_session)):
        model = GroqChatModel(settings.groq_api_key, settings.groq_model) if live else KnownAnswerModel()
        return LangGraphQueryAgent(CuratedSchemaRetriever(), GroqSqlGenerator(model), ReadOnlySqlValidator(), RlsSqlExecutor(session, tenant_scope_setter, 100, 10))

    app.dependency_overrides[query_agent] = agent
    with TestClient(app) as client:
        with create_engine(settings.schema_database_url).begin() as connection:
            seed(connection)
        codec = JwtAccessTokenCodec(settings)
        def headers(user_id, role, company_id):
            return {"Authorization": "Bearer " + codec.issue(user_id, role, company_id, [company_id] if company_id else [1, 2])}

        alpha = headers(1, "client_transport_admin", 1)
        beta = headers(2, "client_transport_admin", 2)
        ops = headers(3, "internal_ops_manager", None)
        def thread(auth, scope, company_id=None):
            response = client.post("/query/threads", headers=auth, json={"scope": scope, "company_id": company_id})
            assert response.status_code == 201, response.text
            return response.json()["id"]

        alpha_thread, beta_thread = thread(alpha, "company", 1), thread(beta, "company", 2)
        ops_all, ops_alpha = thread(ops, "all_companies"), thread(ops, "company", 1)
        assert client.post("/query/threads", headers=alpha, json={"scope": "company", "company_id": 2}).status_code == 403
        assert client.get(f"/query/threads/{alpha_thread}/messages", headers=beta).status_code == 404
        assert client.post("/query/threads", headers=ops, json={"scope": "company", "company_id": 3}).status_code == 403
        if not live:
            for auth, thread_id in ((alpha, alpha_thread), (ops, ops_all)):
                response = client.post(f"/query/threads/{thread_id}/ask", headers=auth, json={"content": "Show company 3 trips"})
                assert response.status_code == 201 and response.json()["rows"] == []
        expected = {
            "How many trips are there?": (2, 1, 3, 2),
            "How many no-shows are there?": (1, 2, 3, 1),
            "What is the total vendor cost?": (300, 500, 800, 300),
            "What is the occupancy of trip A-1?": (0.5, None, 0.5, 0.5),
        }
        for question, values in expected.items():
            for index, ((auth, thread_id), value) in enumerate(zip(((alpha, alpha_thread), (beta, beta_thread), (ops, ops_all), (ops, ops_alpha)), values)):
                if live and index not in ({0, 1, 2} if question == "How many trips are there?" else {0}):
                    continue
                response = client.post(f"/query/threads/{thread_id}/ask", headers=auth, json={"content": question})
                assert response.status_code == 201, f"{question}: {response.status_code} {response.text}"
                result = response.json()
                assert result["generated_sql"] and result["content"] and result["columns"]
                actual = next(iter(result["rows"][0].values())) if result["rows"] else None
                valid = (actual is None and value is None) or (actual is not None and value is not None and float(actual) == value)
                if live and question == "What is the occupancy of trip A-1?" and actual is not None:
                    valid = valid or float(actual) == 50
                assert valid, (question, actual, value, result["generated_sql"])
