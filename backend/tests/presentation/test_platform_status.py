"""Tests for the platform status surface (ES-070).

The milestone's user-visible leg: everything ES-067/068/069 added works
silently, so the deliverable is a surface that makes the posture legible. The
tests hold what makes it trustworthy — that it reports the *same* readiness the
orchestrator's probe reports, that it never carries business data, and that it
tells a caller what it may actually do.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.authorization import (
    ERASE_SHARED_KNOWLEDGE,
    OwnerScopedAuthorizer,
)
from app.main import create_app
from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    get_authenticator,
)
from app.presentation.api.authorization import get_authorizer

pytestmark = pytest.mark.operational


class _Registry:
    def __init__(self, *, unreachable: frozenset[str] = frozenset()) -> None:
        self._unreachable = unreachable

    async def ping_postgres(self) -> None:
        self._probe("postgres")

    async def ping_neo4j(self) -> None:
        self._probe("neo4j")

    async def ping_qdrant(self) -> None:
        self._probe("qdrant")

    def _probe(self, store: str) -> None:
        if store in self._unreachable:
            raise ConnectionError(store)


def _client(
    *unreachable: str, capabilities: frozenset[str] = frozenset()
) -> TestClient:
    identity = AuthenticatedIdentity(
        subject="analyst", kind=IdentityKind.HUMAN, capabilities=capabilities
    )

    class _Authenticator:
        async def authenticate(self, request: object) -> AuthenticatedIdentity:
            return identity

    app = create_app()
    app.state.persistence = _Registry(unreachable=frozenset(unreachable))
    app.dependency_overrides[get_authenticator] = _Authenticator
    app.dependency_overrides[get_authorizer] = lambda: OwnerScopedAuthorizer(
        None  # type: ignore[arg-type]
    )
    return TestClient(app)


def _status(client: TestClient) -> dict[str, object]:
    response = client.get("/api/v1/platform/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, dict)
    return data


def test_the_posture_covers_every_hardening_leg() -> None:
    data = _status(_client())

    assert set(data) == {
        "environment",
        "version",
        "readiness",
        "resilience",
        "data_lifecycle",
        "audit",
        "capabilities",
    }


def test_readiness_matches_the_orchestrator_probe() -> None:
    # Two surfaces disagreeing about whether the platform is ready would be
    # worse than either being wrong alone.
    client = _client("qdrant")

    probe = client.get("/health/ready").json()
    surface = _status(client)["readiness"]

    assert isinstance(surface, dict)
    assert surface["status"] == probe["status"] == "degraded"
    assert surface["qdrant"] == probe["qdrant"] == "unavailable"


def test_the_surface_names_which_stores_gate() -> None:
    readiness = _status(_client())["readiness"]

    assert isinstance(readiness, dict)
    assert readiness["gating"] == ["postgres", "neo4j"]


def test_the_lifecycle_posture_reports_this_deployment_s_policy() -> None:
    # Retention is deployment policy, so an unset duration is reported as
    # "not enforced" rather than as a number that looks like a platform
    # default.
    lifecycle = _status(_client())["data_lifecycle"]

    assert isinstance(lifecycle, dict)
    assert lifecycle["retention_enforced"] is False
    assert lifecycle["retention_days"] == 0
    assert lifecycle["payload_erasure_strategy"] == "delete"


def test_the_audit_posture_reports_durability() -> None:
    audit = _status(_client())["audit"]

    assert isinstance(audit, dict)
    assert audit["sink"] == "durable"
    assert audit["durable"] is True


def test_the_caller_sees_its_own_capabilities() -> None:
    # "What may I do here" is the one caller-specific question the surface
    # answers — and what lets a client avoid offering a control that would
    # only ever be refused.
    data = _status(
        _client(capabilities=frozenset({ERASE_SHARED_KNOWLEDGE}))
    )

    assert data["capabilities"] == [ERASE_SHARED_KNOWLEDGE]


def test_the_surface_requires_authentication() -> None:
    response = TestClient(create_app()).get("/api/v1/platform/status")

    assert response.status_code == 401
