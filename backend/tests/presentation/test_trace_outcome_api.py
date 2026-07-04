"""Tests for the Trace & Outcome read API (ES-045).

``GET /api/v1/investigations/{id}/trace`` returns the explainability trace in
append order (empty list when nothing happened yet — not an error);
``GET /api/v1/investigations/{id}/outcome`` returns the 0..1 synthesized
outcome with a stable error body when none exists. Read-only surfaces over
the Investigation Service; in-memory doubles, plain functions.
"""

import asyncio

from fastapi.testclient import TestClient

from app.application.investigation import InvestigationService
from app.domain.enums import InvestigationOutcomeStatus
from app.domain.identifiers import (
    InvestigationId,
    InvestigationOutcomeId,
    TraceEntryId,
)
from app.domain.investigation_outcome import InvestigationOutcome
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef, Confidence
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from tests.support.builders import (
    FIXED_TIME,
    build_investigation,
    make_investigation_service,
)


def _client(service: InvestigationService) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None
    app.dependency_overrides[get_investigation_service] = lambda: service
    return TestClient(app)


def _trace_entry(entry_id: str, summary: str) -> TraceEntry:
    return TraceEntry(
        id=TraceEntryId(entry_id),
        investigation_id=InvestigationId("inv-1"),
        kind=TraceEntryKind.PLANNER_DECISION,
        actor=ActorRef("planner-agent"),
        summary=summary,
        reference="act-1",
        created_at=FIXED_TIME,
    )


# ----------------------------------------------------------------------- trace


def test_trace_of_untouched_investigation_is_an_empty_list() -> None:
    service = make_investigation_service()
    asyncio.run(service.create(build_investigation("inv-1")))

    response = _client(service).get("/api/v1/investigations/inv-1/trace")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_trace_returns_entries_in_append_order_with_full_fields() -> None:
    service = make_investigation_service()

    async def populate() -> None:
        await service.create(build_investigation("inv-1"))
        await service.record_trace(_trace_entry("t-b", "first"))
        await service.record_trace(_trace_entry("t-a", "second"))

    asyncio.run(populate())

    response = _client(service).get("/api/v1/investigations/inv-1/trace")

    assert response.status_code == 200
    data = response.json()["data"]
    # Append order, not identifier order.
    assert [entry["id"] for entry in data] == ["t-b", "t-a"]
    assert [entry["summary"] for entry in data] == ["first", "second"]
    first = data[0]
    assert first["investigation_id"] == "inv-1"
    assert first["kind"] == "planner_decision"
    assert first["actor"] == "planner-agent"
    assert first["reference"] == "act-1"
    assert first["created_at"].startswith("2026-01-01")


def test_trace_of_unknown_investigation_is_404() -> None:
    response = _client(make_investigation_service()).get(
        "/api/v1/investigations/missing/trace"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "investigation.not_found"


# --------------------------------------------------------------------- outcome


def test_missing_outcome_returns_stable_error_body() -> None:
    service = make_investigation_service()
    asyncio.run(service.create(build_investigation("inv-1")))

    response = _client(service).get("/api/v1/investigations/inv-1/outcome")

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "investigation.outcome_not_found"


def test_outcome_round_trips_through_the_read_surface() -> None:
    service = make_investigation_service()

    async def populate() -> None:
        await service.create(build_investigation("inv-1"))
        await service.create_outcome(
            InvestigationOutcome(
                id=InvestigationOutcomeId("out-1"),
                investigation_id=InvestigationId("inv-1"),
                confidence=Confidence(0.8),
                recommendation="Contain the host.",
                status=InvestigationOutcomeStatus.SYNTHESIZED,
                created_at=FIXED_TIME,
                detected_conflicts=("dns telemetry conflict",),
                open_questions=("initial vector?",),
            )
        )

    asyncio.run(populate())

    response = _client(service).get("/api/v1/investigations/inv-1/outcome")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == "out-1"
    assert data["investigation_id"] == "inv-1"
    assert data["confidence"] == 0.8
    assert data["recommendation"] == "Contain the host."
    assert data["status"] == "synthesized"
    assert data["contributing_findings"] == []
    assert data["detected_conflicts"] == ["dns telemetry conflict"]
    assert data["open_questions"] == ["initial vector?"]
    assert data["report_id"] is None


def test_outcome_of_unknown_investigation_is_404_not_found() -> None:
    response = _client(make_investigation_service()).get(
        "/api/v1/investigations/missing/outcome"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "investigation.not_found"
