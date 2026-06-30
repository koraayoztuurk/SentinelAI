"""Tests for the Investigation API (ES-015).

Each test builds a fresh app via ``create_app`` and overrides the service and the
id/clock generators with deterministic in-memory doubles, so real endpoints
(controllers, schemas, envelope and error translation) are exercised end to end
without a database.
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

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
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)

_IDENTITY = AuthenticatedIdentity(subject="test-analyst", kind=IdentityKind.HUMAN)

_FIXED_TIME = datetime(2026, 6, 30, tzinfo=UTC)


# --------------------------------------------------------------- in-memory doubles


class _InvestigationRepo:
    def __init__(self) -> None:
        self._items: dict[str, Investigation] = {}

    async def add(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation

    async def get(self, investigation_id: InvestigationId) -> Investigation | None:
        return self._items.get(investigation_id.value)

    async def update(self, investigation: Investigation) -> None:
        self._items[investigation.id.value] = investigation


class _EvidenceRepo:
    def __init__(self) -> None:
        self._items: dict[str, Evidence] = {}

    async def add(self, evidence: Evidence) -> None:
        self._items[evidence.id.value] = evidence

    async def get(self, evidence_id: EvidenceId) -> Evidence | None:
        return self._items.get(evidence_id.value)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Evidence, ...]:
        return tuple(
            e for e in self._items.values()
            if e.investigation_id == investigation_id
        )


class _FindingRepo:
    def __init__(self) -> None:
        self._items: dict[str, Finding] = {}

    async def add(self, finding: Finding) -> None:
        self._items[finding.id.value] = finding

    async def get(self, finding_id: FindingId) -> Finding | None:
        return self._items.get(finding_id.value)

    async def update(self, finding: Finding) -> None:
        self._items[finding.id.value] = finding

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Finding, ...]:
        return tuple(
            f for f in self._items.values()
            if f.investigation_id == investigation_id
        )


class _ReportRepo:
    def __init__(self) -> None:
        self._items: dict[str, Report] = {}

    async def add(self, report: Report) -> None:
        self._items[report.id.value] = report

    async def get(self, report_id: ReportId) -> Report | None:
        return self._items.get(report_id.value)

    async def list_for_investigation(
        self, investigation_id: InvestigationId
    ) -> tuple[Report, ...]:
        return tuple(
            r for r in self._items.values()
            if r.investigation_id == investigation_id
        )


class _CountingIds:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"id-{self._n}"


class _FixedClock:
    def now(self) -> datetime:
        return _FIXED_TIME


def _client() -> TestClient:
    app = create_app()
    service = InvestigationService(
        _InvestigationRepo(), _EvidenceRepo(), _FindingRepo(), _ReportRepo()
    )
    ids = _CountingIds()
    clock = _FixedClock()
    app.dependency_overrides[get_investigation_service] = lambda: service
    app.dependency_overrides[get_id_generator] = lambda: ids
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    return TestClient(app)


def _create_investigation(client: TestClient) -> str:
    response = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    )
    assert response.status_code == 201
    investigation_id = response.json()["data"]["id"]
    assert isinstance(investigation_id, str)
    return investigation_id


# ----------------------------------------------------------------- investigation


def test_create_investigation_envelope() -> None:
    response = _client().post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["id"] == "id-1"
    assert body["data"]["title"] == "Phish"
    assert body["data"]["status"] == "created"
    assert body["data"]["created_at"].startswith("2026-06-30")
    assert body["meta"]["request_id"] == response.headers.get("X-Request-ID")


def test_get_investigation() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.get(f"/api/v1/investigations/{investigation_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == investigation_id


def test_get_missing_investigation_returns_404() -> None:
    response = _client().get("/api/v1/investigations/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "investigation.not_found"


def test_change_status_valid() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/status",
        json={"status": "active"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "active"


def test_change_status_invalid_transition_returns_409() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/status",
        json={"status": "completed"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "investigation.invalid_transition"


def test_invalid_status_value_returns_422() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/status",
        json={"status": "bogus"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "api.validation_error"


# -------------------------------------------------------------------- evidence


def test_attach_and_list_evidence() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    attach = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"source": "siem", "integrity": "sha256:abc", "content": "alert"},
    )
    assert attach.status_code == 201
    evidence_id = attach.json()["data"]["id"]

    listed = client.get(f"/api/v1/investigations/{investigation_id}/evidence")
    assert listed.status_code == 200
    assert [e["id"] for e in listed.json()["data"]] == [evidence_id]


def test_get_evidence_ownership_mismatch_returns_404() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    attach = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"source": "siem", "integrity": "sha256:abc", "content": "alert"},
    )
    evidence_id = attach.json()["data"]["id"]
    response = client.get(
        f"/api/v1/investigations/other/evidence/{evidence_id}"
    )
    assert response.status_code == 404


# --------------------------------------------------------------------- finding


def _attach_evidence(client: TestClient, investigation_id: str) -> str:
    attach = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"source": "siem", "integrity": "sha256:abc", "content": "alert"},
    )
    return attach.json()["data"]["id"]


def test_create_and_list_finding() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    evidence_id = _attach_evidence(client, investigation_id)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={
            "supporting_evidence": [evidence_id],
            "creator": "analyst-1",
            "confidence": 0.8,
            "status": "proposed",
        },
    )
    assert response.status_code == 201
    finding_id = response.json()["data"]["id"]

    listed = client.get(f"/api/v1/investigations/{investigation_id}/findings")
    assert [f["id"] for f in listed.json()["data"]] == [finding_id]


def test_create_finding_without_evidence_returns_422() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={
            "supporting_evidence": [],
            "creator": "analyst-1",
            "confidence": 0.8,
            "status": "proposed",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "domain.missing_supporting_evidence"


def test_create_finding_with_unknown_evidence_returns_404() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={
            "supporting_evidence": ["missing"],
            "creator": "analyst-1",
            "confidence": 0.8,
            "status": "proposed",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "investigation.evidence_not_found"


def test_update_finding() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    evidence_id = _attach_evidence(client, investigation_id)
    created = client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={
            "supporting_evidence": [evidence_id],
            "creator": "analyst-1",
            "confidence": 0.8,
            "status": "proposed",
        },
    )
    finding_id = created.json()["data"]["id"]
    response = client.put(
        f"/api/v1/investigations/{investigation_id}/findings/{finding_id}",
        json={
            "supporting_evidence": [evidence_id],
            "creator": "analyst-1",
            "created_at": "2026-06-30T00:00:00+00:00",
            "confidence": 0.95,
            "status": "validated",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "validated"
    assert response.json()["data"]["confidence"] == 0.95


# ---------------------------------------------------------------------- report


def test_create_list_and_get_report() -> None:
    client = _client()
    investigation_id = _create_investigation(client)
    created = client.post(
        f"/api/v1/investigations/{investigation_id}/reports",
        json={"author": "analyst-1"},
    )
    assert created.status_code == 201
    report_id = created.json()["data"]["id"]
    assert created.json()["data"]["version"] == 1

    listed = client.get(f"/api/v1/investigations/{investigation_id}/reports")
    assert [r["id"] for r in listed.json()["data"]] == [report_id]

    fetched = client.get(
        f"/api/v1/investigations/{investigation_id}/reports/{report_id}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["data"]["id"] == report_id


# ----------------------------------------------------------------- not configured


def test_service_not_configured_returns_503() -> None:
    app = create_app()
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    client = TestClient(app)
    response = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "api.persistence_not_configured"
