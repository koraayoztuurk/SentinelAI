"""End-to-end tests for the ES-062 production identity chain.

The JWT authenticator, owner==subject creation and the owner-scoped policy run
together through the real HTTP stack: a minted token establishes a per-subject
identity; the creator owns what they create; a foreign subject is denied on
investigation-scoped surfaces; a missing/expired token is 401 and carries the
``WWW-Authenticate: Bearer`` challenge. In-memory services; the JWT secret comes
through a fake SecretProvider (no env/cache coupling).
"""

from fastapi.testclient import TestClient

from app.application.authorization import OwnerScopedAuthorizer
from app.application.secrets import SecretName
from app.config.auth import JwtSettings
from app.main import create_app
from app.presentation.api.auth import get_authenticator
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.jwt_authenticator import JwtAuthenticator
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from app.shared.secret import Secret
from tests.support.builders import make_investigation_service
from tests.support.jwt import mint_jwt

_SECRET = "jwt-chain-secret-7c31"


class _FixedSecrets:
    def resolve(self, name: SecretName) -> Secret:
        assert name == SecretName("AUTH_JWT_SECRET")
        return Secret(_SECRET)


def _stack() -> TestClient:
    investigation = make_investigation_service()
    app = create_app()
    app.dependency_overrides[get_investigation_service] = lambda: investigation
    app.dependency_overrides[get_authorizer] = lambda: OwnerScopedAuthorizer(
        investigation
    )
    app.dependency_overrides[get_authenticator] = lambda: JwtAuthenticator(
        JwtSettings(), _FixedSecrets()
    )
    return TestClient(app)


def _bearer(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_jwt(_SECRET, subject)}"}


def test_no_token_is_401_with_challenge() -> None:
    response = _stack().get("/api/v1/investigations/inv-1")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "api.unauthenticated"
    # RFC 7235: a 401 must carry an authentication challenge.
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_expired_token_is_401_with_challenge() -> None:
    headers = {
        "Authorization": f"Bearer {mint_jwt(_SECRET, 'alice', expires_in=-3600)}"
    }
    response = _stack().get("/api/v1/investigations/inv-1", headers=headers)
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_owner_flow_and_foreign_subject_denied() -> None:
    client = _stack()

    created = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "priority": "high"},
        headers=_bearer("alice"),
    )
    assert created.status_code == 201
    # owner==subject: the creator owns it, derived from the verified token.
    assert created.json()["data"]["owner"] == "alice"
    investigation_id = created.json()["data"]["id"]

    # The owner reads their investigation.
    assert (
        client.get(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        ).status_code
        == 200
    )
    # A foreign subject is denied on the investigation-scoped surface.
    foreign = client.get(
        f"/api/v1/investigations/{investigation_id}",
        headers=_bearer("bob"),
    )
    assert foreign.status_code == 403
    assert foreign.json()["error"]["code"] == "authorization.denied"


def test_system_identity_token_authenticates() -> None:
    headers = {
        "Authorization": f"Bearer {mint_jwt(_SECRET, 'svc-1', kind='system')}"
    }
    # A system identity may create (creation is open to authenticated identities);
    # the owner is the system subject.
    created = _stack().post(
        "/api/v1/investigations",
        json={"title": "Automated", "priority": "low"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["owner"] == "svc-1"
