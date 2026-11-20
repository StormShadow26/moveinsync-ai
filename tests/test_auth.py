"""Authentication API contract tests."""

from uuid import uuid4

from fastapi.testclient import TestClient

from moveinsync_ai.api.routers.auth import get_otp_delivery
from moveinsync_ai.app import create_app
from moveinsync_ai.config import Settings
from moveinsync_ai.database.models import Company, User, UserType
from moveinsync_ai.database.session import get_session


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


def test_otp_is_single_use() -> None:
    client, settings, delivery = make_client()
    with client:
        create_test_users(settings)
        client.post("/auth/otp/request", json={"email": "admin@acme.in"})
        verification = {"email": "admin@acme.in", "code": delivery.codes["admin@acme.in"]}
        assert client.post("/auth/otp/verify", json=verification).status_code == 200
        assert client.post("/auth/otp/verify", json=verification).status_code == 401
