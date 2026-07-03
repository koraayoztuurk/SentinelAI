"""Tests for Authorization (ES-020).

Verifies that authorization is enforced after authentication and decided by the
application-layer authorizer: an authenticated identity is denied by default
(403), an allow-all policy lets the request reach the endpoint, and unauthenticated
requests still fail authentication first (401).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.application.authorization import (
    AuthorizationError,
    AuthorizationRequest,
    DenyAllAuthorizer,
)
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
    require_identity,
)
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from tests.support.doubles import (
    InMemoryOutcomeRepository,
    InMemoryTraceRepository,
)

_IDENTITY = AuthenticatedIdentity(subject="test-analyst", kind=IdentityKind.HUMAN)
_PAYLOAD = {"title": "Phish", "owner": "a", "priority": "high"}


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


def test_authenticated_request_denied_by_default() -> None:
    app = create_app()
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    client = TestClient(app)
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "authorization.denied"
    assert body["meta"]["request_id"] == response.headers.get("X-Request-ID")


def test_authorized_request_reaches_endpoint() -> None:
    app = create_app()
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    app.dependency_overrides[get_investigation_service] = _service
    client = TestClient(app)
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    assert response.status_code == 201


def test_unauthenticated_fails_authentication_first() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "api.unauthenticated"


# --------------------------------------------------------------------- unit


def test_deny_all_authorizer_denies() -> None:
    async def scenario() -> None:
        request = AuthorizationRequest(
            subject="s", identity_kind="human", operation="POST /api/v1/investigations"
        )
        with pytest.raises(AuthorizationError):
            await DenyAllAuthorizer().authorize(request)

    asyncio.run(scenario())


def test_authorization_request_fields() -> None:
    request = AuthorizationRequest(
        subject="analyst-1",
        identity_kind="human",
        operation="GET /api/v1/investigations/inv-1",
    )
    assert request.subject == "analyst-1"
    assert request.identity_kind == "human"
    assert request.operation == "GET /api/v1/investigations/inv-1"
