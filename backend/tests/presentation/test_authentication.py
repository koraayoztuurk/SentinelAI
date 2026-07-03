"""Tests for Authentication (ES-019).

Verifies the secure-by-default enforcement seam: protected ``/api/v1`` endpoints
reject unauthenticated requests, the public ``/health`` endpoint stays open, and a
configured authenticator lets requests through. No concrete identity provider is
required — tests inject doubles.
"""

import asyncio

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.application.authorization import AuthorizationRequest
from app.application.investigation import InvestigationService
from app.domain.evidence import Evidence
from app.domain.finding import Finding
from app.domain.identifiers import EvidenceId, FindingId, InvestigationId, ReportId
from app.domain.investigation import Investigation
from app.domain.report import Report
from app.main import create_app
from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    UnconfiguredAuthenticator,
    current_identity,
    get_authenticator,
    require_identity,
)
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.errors import AuthenticationError
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from tests.support.doubles import (
    InMemoryOutcomeRepository,
    InMemoryTraceRepository,
)

_IDENTITY = AuthenticatedIdentity(subject="test-analyst", kind=IdentityKind.HUMAN)


class _AllowAuthenticator:
    async def authenticate(self, request: Request) -> AuthenticatedIdentity:
        return _IDENTITY


class _AllowAllAuthorizer:
    async def authorize(self, request: AuthorizationRequest) -> None:
        return None


class _InvestigationRepo:
    def __init__(self) -> None:
        self.items: dict[str, Investigation] = {}

    async def add(self, investigation: Investigation) -> None:
        self.items[investigation.id.value] = investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation | None:
        return self.items.get(investigation_id.value)

    async def update(self, investigation: Investigation) -> None:
        self.items[investigation.id.value] = investigation


class _EvidenceRepo:
    async def add(self, evidence: Evidence) -> None: ...
    async def get(self, evidence_id: EvidenceId) -> Evidence | None:
        return None
    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        return ()


class _FindingRepo:
    async def add(self, finding: Finding) -> None: ...
    async def get(self, finding_id: FindingId) -> Finding | None:
        return None
    async def update(self, finding: Finding) -> None: ...
    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        return ()


class _ReportRepo:
    async def add(self, report: Report) -> None: ...
    async def get(self, report_id: ReportId) -> Report | None:
        return None
    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        return ()


def _service() -> InvestigationService:
    return InvestigationService(
        _InvestigationRepo(),
        _EvidenceRepo(),
        _FindingRepo(),
        _ReportRepo(),
        InMemoryOutcomeRepository(),
        InMemoryTraceRepository(),
    )


# ----------------------------------------------------------------- enforcement


def test_protected_endpoint_denies_unauthenticated() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "a", "priority": "high"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "api.unauthenticated"
    assert body["meta"]["request_id"] == response.headers.get("X-Request-ID")


def test_authenticated_request_passes_through() -> None:
    app = create_app()
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    app.dependency_overrides[get_investigation_service] = _service
    client = TestClient(app)
    response = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "a", "priority": "high"},
    )
    assert response.status_code == 201


def test_authenticator_double_passes_through() -> None:
    app = create_app()
    app.dependency_overrides[get_authenticator] = _AllowAuthenticator
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    app.dependency_overrides[get_investigation_service] = _service
    client = TestClient(app)
    response = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "a", "priority": "high"},
    )
    assert response.status_code == 201


def test_health_stays_public() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200


# ------------------------------------------------------------------- identity


def test_identity_kinds() -> None:
    assert {k.value for k in IdentityKind} == {"human", "system", "external"}


def test_blank_subject_rejected() -> None:
    with pytest.raises(AuthenticationError):
        AuthenticatedIdentity(subject="  ", kind=IdentityKind.HUMAN)


def test_unconfigured_authenticator_denies() -> None:
    async def scenario() -> None:
        with pytest.raises(AuthenticationError):
            await UnconfiguredAuthenticator().authenticate(None)  # type: ignore[arg-type]

    asyncio.run(scenario())


def test_current_identity_requires_established_identity() -> None:
    scope = {"type": "http", "headers": []}
    request = Request(scope)
    with pytest.raises(AuthenticationError):
        current_identity(request)
