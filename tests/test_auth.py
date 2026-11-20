"""Authentication API contract tests."""

from fastapi.testclient import TestClient
from uuid import uuid4

from moveinsync_ai.app import create_app
from moveinsync_ai.auth.security import password_hasher
from moveinsync_ai.config import Settings
from moveinsync_ai.database.models import Company, User, UserType
from moveinsync_ai.database.session import get_session


def make_client() -> tuple[TestClient, Settings]:
    settings = Settings(
        database_url="sqlite+pysqlite:///file:auth_{}?mode=memory&cache=shared&uri=true".format(uuid4().hex),
        jwt_secret_key="test-secret",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
    )
    return TestClient(create_app(settings)), settings


def create_test_users(settings: Settings) -> None:
    """Create explicit test fixtures; production startup creates no users."""
    with next(get_session(settings)) as session:
        acme = Company(slug="acme", name="Acme India")
        session.add(acme)
        session.flush()
        session.add_all(
            [
                User(
                    email="admin@acme.in",
                    password_hash=password_hasher.hash("demo-password"),
                    user_type=UserType.CLIENT_TRANSPORT_ADMIN,
                    company_id=acme.id,
                ),
                User(
                    email="ops@moveinsync.ai",
                    password_hash=password_hasher.hash("demo-password"),
                    user_type=UserType.INTERNAL_OPS_MANAGER,
                ),
            ]
        )
        session.commit()


def test_transport_admin_receives_single_company_scope() -> None:
    client, settings = make_client()
    with client:
        create_test_users(settings)
        token_response = client.post(
            "/auth/login",
            data={"username": "admin@acme.in", "password": "demo-password"},
        )
        assert token_response.status_code == 200
        token = token_response.json()["access_token"]

        identity_response = client.get("/auth/me", headers={"Authorization": "Bearer " + token})
        assert identity_response.status_code == 200
        assert identity_response.json()["user_type"] == "client_transport_admin"
        assert identity_response.json()["access_scope"] == "single_company"
        assert identity_response.json()["company_id"] == 1


def test_internal_manager_receives_all_company_scope() -> None:
    client, settings = make_client()
    with client:
        create_test_users(settings)
        token_response = client.post(
            "/auth/login",
            data={"username": "ops@moveinsync.ai", "password": "demo-password"},
        )
        token = token_response.json()["access_token"]
        identity_response = client.get("/auth/me", headers={"Authorization": "Bearer " + token})

        assert identity_response.status_code == 200
        assert identity_response.json()["user_type"] == "internal_ops_manager"
        assert identity_response.json()["access_scope"] == "all_companies"
        assert identity_response.json()["company_id"] is None


def test_invalid_password_does_not_issue_token() -> None:
    client, settings = make_client()
    with client:
        create_test_users(settings)
        response = client.post(
            "/auth/login",
            data={"username": "admin@acme.in", "password": "incorrect"},
        )
        assert response.status_code == 401
        assert "access_token" not in response.json()
