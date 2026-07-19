"""Integration tests: presentation ↔ application ↔ domain collaboration (ES-034).

Cross-domain flows through the full HTTP stack: real controllers, envelope,
error translation and middleware over the real Investigation Service wired to the
shared in-memory doubles (integration-testing §4/§5 — collaboration and interface
validation across architectural domains, not per-endpoint unit checks).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from tests.support.auth import override_identity
from tests.support.builders import FIXED_TIME, make_investigation_service
from tests.support.doubles import FixedClock, SequentialIdGenerator

pytestmark = pytest.mark.integration


def _client() -> TestClient:
    service = make_investigation_service()
    ids = SequentialIdGenerator()
    clock = FixedClock(FIXED_TIME)
    app = create_app()
    app.dependency_overrides[get_investigation_service] = lambda: service
    app.dependency_overrides[get_id_generator] = lambda: ids
    app.dependency_overrides[get_clock] = lambda: clock
    app.dependency_overrides[require_authorization] = lambda: None
    override_identity(app)
    return TestClient(app)


def test_full_investigation_lifecycle_flow() -> None:
    """Create → activate → evidence → finding → report, one coherent flow."""

    client = _client()

    created = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    )
    assert created.status_code == 201
    investigation_id = created.json()["data"]["id"]

    activated = client.post(
        f"/api/v1/investigations/{investigation_id}/status",
        json={"status": "active"},
    )
    assert activated.status_code == 200
    assert activated.json()["data"]["status"] == "active"

    evidence = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={"source": "edr", "integrity": "verified", "content": "beacon"},
    )
    assert evidence.status_code == 201
    evidence_id = evidence.json()["data"]["id"]
    assert evidence.json()["data"]["investigation_id"] == investigation_id

    finding = client.post(
        f"/api/v1/investigations/{investigation_id}/findings",
        json={
            "supporting_evidence": [evidence_id],
            "creator": "analyst-1",
            "confidence": 0.8,
            "status": "proposed",
        },
    )
    assert finding.status_code == 201
    assert finding.json()["data"]["supporting_evidence"] == [evidence_id]

    report = client.post(
        f"/api/v1/investigations/{investigation_id}/reports",
        json={"author": "analyst-1"},
    )
    assert report.status_code == 201

    # Cross-resource consistency: every listing reflects the same flow.
    fetched = client.get(f"/api/v1/investigations/{investigation_id}")
    assert fetched.json()["data"]["status"] == "active"

    evidence_list = client.get(
        f"/api/v1/investigations/{investigation_id}/evidence"
    )
    assert [e["id"] for e in evidence_list.json()["data"]] == [evidence_id]

    findings_list = client.get(
        f"/api/v1/investigations/{investigation_id}/findings"
    )
    assert len(findings_list.json()["data"]) == 1
    assert findings_list.json()["data"][0]["supporting_evidence"] == [evidence_id]

    reports_list = client.get(
        f"/api/v1/investigations/{investigation_id}/reports"
    )
    assert len(reports_list.json()["data"]) == 1

    # Interface consistency: the envelope carries the request id end to end.
    assert fetched.json()["meta"]["request_id"] == fetched.headers["X-Request-ID"]


def test_finding_cannot_reference_foreign_evidence() -> None:
    """Evidence ownership is enforced across resources (422 at the boundary)."""

    client = _client()

    inv_a = client.post(
        "/api/v1/investigations",
        json={"title": "A", "owner": "analyst-1", "priority": "high"},
    ).json()["data"]["id"]
    inv_b = client.post(
        "/api/v1/investigations",
        json={"title": "B", "owner": "analyst-1", "priority": "high"},
    ).json()["data"]["id"]

    evidence_a = client.post(
        f"/api/v1/investigations/{inv_a}/evidence",
        json={"source": "edr", "integrity": "verified", "content": "beacon"},
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/investigations/{inv_b}/findings",
        json={
            "supporting_evidence": [evidence_a],
            "creator": "analyst-1",
            "confidence": 0.8,
            "status": "proposed",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "investigation.evidence_ownership"


def test_finding_with_unknown_evidence_translates_to_not_found() -> None:
    """A missing cross-resource reference surfaces as the documented 404."""

    client = _client()

    investigation_id = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
    ).json()["data"]["id"]

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
