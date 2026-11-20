"""Authentication API contract tests."""

from uuid import uuid4

from fastapi.testclient import TestClient

from moveinsync_ai.api.routers.auth import get_otp_delivery
from moveinsync_ai.api.routers.threads import query_agent
from moveinsync_ai.app import create_app
from moveinsync_ai.config import Settings
from moveinsync_ai.database.models import Company, User, UserCompany, UserType
from moveinsync_ai.database.session import get_session
from moveinsync_ai.query_agent.contracts import QueryResult
from moveinsync_ai.query_agent.groq import GroqSqlGenerator
from moveinsync_ai.query_agent.schema_retrieval import CuratedSchemaRetriever
from moveinsync_ai.query_agent.service import LangGraphQueryAgent
from moveinsync_ai.query_agent.sql_validator import ReadOnlySqlValidator


class RecordingOtpDelivery:
    """Test implementation of the OTP delivery contract."""

    def __init__(self):
        self.codes: dict[str, str] = {}

    def send(self, recipient: str, code: str) -> None:
        self.codes[recipient] = code


def make_client() -> tuple[TestClient, Settings, RecordingOtpDelivery]:
    settings = Settings(
        database_url="sqlite+pysqlite:///file:auth_{}?mode=memory&cache=shared&uri=true".format(uuid4().hex),
        jwt_secret_key="test-secret-key-with-at-least-thirty-two-characters",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        otp_secret_key="test-otp-secret",
    )
    application = create_app(settings)
    delivery = RecordingOtpDelivery()
    application.dependency_overrides[get_otp_delivery] = lambda: delivery
    return TestClient(application), settings, delivery


def create_test_users(settings: Settings) -> None:
    """Provision users explicitly; startup never creates identities."""
    with next(get_session(settings)) as session:
        acme = Company(slug="acme", name="Acme India")
        session.add(acme)
        session.flush()
        session.add_all(
            [
                User(email="admin@acme.in", user_type=UserType.CLIENT_TRANSPORT_ADMIN, company_id=acme.id),
                User(email="ops@moveinsync.ai", user_type=UserType.INTERNAL_OPS_MANAGER),
            ]
        )
        session.flush()
        manager = session.query(User).filter_by(email="ops@moveinsync.ai").one()
        session.add(UserCompany(user_id=manager.id, company_id=acme.id))
        session.commit()


def test_provisioned_transport_admin_receives_single_company_scope() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        request_response = client.post("/auth/otp/request", json={"email": "admin@acme.in"})
        assert request_response.status_code == 202
        token_response = client.post(
            "/auth/otp/verify", json={"email": "admin@acme.in", "code": delivery.codes["admin@acme.in"]}
        )
        assert token_response.status_code == 200
        token = token_response.json()["access_token"]

        identity_response = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
        assert identity_response.status_code == 200
        assert identity_response.json()["user_type"] == "client_transport_admin"
        assert identity_response.json()["access_scope"] == "single_company"
        assert identity_response.json()["company_id"] == 1


def test_unknown_email_receives_generic_response_without_an_otp() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        response = client.post("/auth/otp/request", json={"email": "unknown@acme.in"})
        assert response.status_code == 202
        assert delivery.codes == {}


def test_internal_ops_manager_receives_all_companies_scope() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        assert client.post("/auth/otp/request", json={"email": "ops@moveinsync.ai"}).status_code == 202
        token = client.post(
            "/auth/otp/verify", json={"email": "ops@moveinsync.ai", "code": delivery.codes["ops@moveinsync.ai"]}
        ).json()["access_token"]
        identity = client.get("/auth/me", headers={"Authorization": "Bearer " + token}).json()
        assert identity["user_type"] == "internal_ops_manager"
        assert identity["access_scope"] == "all_companies"
        assert identity["company_id"] is None


def test_otp_is_single_use() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        client.post("/auth/otp/request", json={"email": "admin@acme.in"})
        verification = {"email": "admin@acme.in", "code": delivery.codes["admin@acme.in"]}
        assert client.post("/auth/otp/verify", json=verification).status_code == 200
        assert client.post("/auth/otp/verify", json=verification).status_code == 401


def test_travel_admin_can_create_a_company_thread_and_messages() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        client.post("/auth/otp/request", json={"email": "admin@acme.in"})
        token = client.post(
            "/auth/otp/verify", json={"email": "admin@acme.in", "code": delivery.codes["admin@acme.in"]}
        ).json()["access_token"]
        headers = {"Authorization": "Bearer " + token}

        thread = client.post("/query/threads", json={"scope": "company", "company_id": 1, "title": "Route review"}, headers=headers)
        assert thread.status_code == 201
        thread_id = thread.json()["id"]
        message = client.post(
            f"/query/threads/{thread_id}/messages", json={"content": "Which route had the most no-shows?"}, headers=headers
        )
        assert message.status_code == 201
        assert client.get("/query/threads", headers=headers).json()[0]["title"] == "Route review"


def test_travel_admin_cannot_create_an_all_companies_thread() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        client.post("/auth/otp/request", json={"email": "admin@acme.in"})
        token = client.post(
            "/auth/otp/verify", json={"email": "admin@acme.in", "code": delivery.codes["admin@acme.in"]}
        ).json()["access_token"]
        response = client.post("/query/threads", json={"scope": "all_companies"}, headers={"Authorization": "Bearer " + token})
        assert response.status_code == 403


def test_internal_manager_can_use_otp_and_choose_all_companies() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        client.post("/auth/otp/request", json={"email": "ops@moveinsync.ai"})
        token = client.post(
            "/auth/otp/verify", json={"email": "ops@moveinsync.ai", "code": delivery.codes["ops@moveinsync.ai"]}
        ).json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        response = client.post("/query/threads", json={"scope": "all_companies", "title": "Portfolio review"}, headers=headers)
        assert response.status_code == 201
        assert response.json()["company_id"] is None
        assert client.get("/query/companies", headers=headers).status_code == 200


def test_ask_returns_rows_and_keeps_message_history() -> None:
    class Model:
        def complete(self, prompt, *, json_output=False):
            if json_output:
                assert "trips(id," in prompt and "employees(id," not in prompt
                return '{"sql": "SELECT id FROM trips", "reasoning_summary": "List trips"}'
            return "One trip."

    class Executor:
        def execute(self, sql, scope):
            assert scope.company_id == 1 and scope.access_scope == "single_company"
            assert sql == "SELECT id FROM public.trips"
            return QueryResult(["id"], [{"id": 7}])

    client, settings, delivery = make_client()
    client.app.dependency_overrides[query_agent] = lambda: LangGraphQueryAgent(
        CuratedSchemaRetriever(), GroqSqlGenerator(Model()), ReadOnlySqlValidator(), Executor()
    )
    with client:
        create_test_users(settings)
        client.post("/auth/otp/request", json={"email": "admin@acme.in"})
        token = client.post("/auth/otp/verify", json={"email": "admin@acme.in", "code": delivery.codes["admin@acme.in"]}).json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        thread_id = client.post("/query/threads", json={"scope": "company", "company_id": 1}, headers=headers).json()["id"]
        response = client.post(f"/query/threads/{thread_id}/ask", json={"content": "Show trips"}, headers=headers)
        assert response.status_code == 201
        assert response.json()["columns"] == ["id"] and response.json()["rows"] == [{"id": 7}]
        assert response.json()["generated_sql"] == "SELECT id FROM public.trips"
        messages = client.get(f"/query/threads/{thread_id}/messages", headers=headers).json()
        assert [message["role"] for message in messages] == ["user", "assistant"]
