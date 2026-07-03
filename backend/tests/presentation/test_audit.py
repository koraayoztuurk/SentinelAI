"""Tests for Audit (ES-021).

Verifies that a security-relevant audit event is recorded for each protected
``/api`` request — operation performed, authorization denied and authentication
failed — that ``/health`` is not audited, and that audit recording is best-effort
(a recorder failure never drops the business request).
"""

import asyncio

from fastapi.testclient import TestClient

from app.application.audit import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    LoggingAuditRecorder,
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


class _InMemoryRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class _FailingRecorder:
    async def record(self, event: AuditEvent) -> None:
        raise RuntimeError("sink unavailable")


class _AllowAllAuthorizer:
    async def authorize(self, request: object) -> None:
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


def _authorized_app(recorder: object):  # type: ignore[no-untyped-def]
    app = create_app()
    app.state.audit_recorder = recorder
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    app.dependency_overrides[get_investigation_service] = _service
    return app


# --------------------------------------------------------------------- recording


def test_operation_performed_is_audited() -> None:
    recorder = _InMemoryRecorder()
    client = TestClient(_authorized_app(recorder))
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    assert response.status_code == 201

    assert len(recorder.events) == 1
    event = recorder.events[0]
    assert event.action == AuditAction.OPERATION_PERFORMED
    assert event.outcome == AuditOutcome.SUCCEEDED
    assert event.subject == "test-analyst"
    assert event.identity_kind == "human"
    assert event.operation == "POST /api/v1/investigations"
    assert event.request_id == response.headers.get("X-Request-ID")


def test_authorization_denied_is_audited() -> None:
    recorder = _InMemoryRecorder()
    app = create_app()
    app.state.audit_recorder = recorder
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    client = TestClient(app)
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    assert response.status_code == 403

    event = recorder.events[0]
    assert event.action == AuditAction.AUTHORIZATION_DENIED
    assert event.outcome == AuditOutcome.DENIED
    assert event.subject == "test-analyst"
    assert event.operation == "POST /api/v1/investigations"


def test_authentication_failed_is_audited() -> None:
    recorder = _InMemoryRecorder()
    app = create_app()
    app.state.audit_recorder = recorder
    client = TestClient(app)
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    assert response.status_code == 401

    event = recorder.events[0]
    assert event.action == AuditAction.AUTHENTICATION_FAILED
    assert event.outcome == AuditOutcome.FAILED
    assert event.subject is None


def test_health_is_not_audited() -> None:
    recorder = _InMemoryRecorder()
    app = create_app()
    app.state.audit_recorder = recorder
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert recorder.events == []


def test_recording_is_best_effort() -> None:
    client = TestClient(_authorized_app(_FailingRecorder()))
    response = client.post("/api/v1/investigations", json=_PAYLOAD)
    # The recorder raised, but the business request still succeeds.
    assert response.status_code == 201


# --------------------------------------------------------------------- unit


def test_logging_recorder_does_not_raise() -> None:
    event = AuditEvent(
        action=AuditAction.OPERATION_PERFORMED,
        outcome=AuditOutcome.SUCCEEDED,
        subject="s",
        identity_kind="human",
        operation="POST /api/v1/investigations",
        request_id="req-1",
    )
    asyncio.run(LoggingAuditRecorder().record(event))


def test_audit_enum_values() -> None:
    assert AuditAction.AUTHORIZATION_DENIED.value == "authorization.denied"
    assert {o.value for o in AuditOutcome} == {"succeeded", "denied", "failed"}
