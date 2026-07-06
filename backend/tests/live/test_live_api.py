"""Live end-to-end API tests over the runtime persistence binding (ES-042).

Opt-in (`pytest -m live`): runs the real application (lifespan → persistence
registry → live PostgreSQL adapters) against a reachable PostgreSQL and
verifies the ES-042 exit criteria — investigation and memory endpoints work
end to end without 503s (authorization overridden in test, as before),
readiness reflects the reachable PostgreSQL, and the Planner Service contains a
graph-store-unavailable failure as a failed execution result (stable
``graph.store_unavailable`` code, never an exception).

The Graph store went live with ES-048: the live graph API and real
``find_neighbors`` are covered by the ``live_neo4j`` suite (which requires a
reachable Neo4j). This suite stays PostgreSQL-centric — it must pass whether or
not Neo4j is up (CI's live lane provides PostgreSQL only) — so it drives the
graph-unavailable failure-isolation path through an explicit unavailable repo.

The planner checks drive the Planner Service composition directly: its
transitional HTTP resource was removed by ES-044 (V-2) — the service remains
the Investigation Loop's executor.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.application.graph import GraphService
from app.application.investigation import InvestigationService
from app.application.memory import MemoryService
from app.application.planner import PlannerService
from app.application.planner.actions import (
    ExecutionResult,
    FindNeighborsAction,
    GetMemoryAction,
    PlannerAction,
)
from app.domain.identifiers import EntityId, MemoryItemId
from app.domain.memory_item import MemoryItem
from app.infrastructure.persistence.neo4j.unavailable import (
    UnavailableGraphRepository,
)
from app.infrastructure.persistence.postgres.engine import create_session_factory
from app.infrastructure.persistence.postgres.investigation.repositories import (
    PostgresEvidenceRepository,
    PostgresFindingRepository,
    PostgresInvestigationRepository,
    PostgresOutcomeRepository,
    PostgresReportRepository,
    PostgresTraceRepository,
)
from app.infrastructure.persistence.postgres.memory.repositories import (
    PostgresMemoryRepository,
)
from app.infrastructure.persistence.postgres.session import session_scope
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from tests.live.support import ensure_schema, live_engine, truncate_tables

pytestmark = pytest.mark.live

_ALL_TABLES = (
    "trace_entry",
    "investigation_outcome",
    "report",
    "finding",
    "evidence",
    "investigation",
    "memory_outbox",
    "memory_item",
)


async def _reset_database() -> None:
    engine = live_engine()
    try:
        await truncate_tables(engine, *_ALL_TABLES)
    finally:
        await engine.dispose()


def _client() -> TestClient:
    app = create_app()
    # Authorization stays default-deny elsewhere; tests bypass the gate the
    # same way the ES-015+ presentation tests do.
    app.dependency_overrides[require_authorization] = lambda: None
    return TestClient(app)


def test_live_stack_serves_investigation_memory_and_planner() -> None:
    ensure_schema()
    asyncio.run(_reset_database())

    with _client() as client:
        # Readiness reflects the reachable authoritative store (PostgreSQL
        # gates readiness; the neo4j field is reported but not asserted here —
        # this suite does not require a live graph store).
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        ready_body = ready.json()
        assert ready_body["status"] == "ready"
        assert ready_body["postgres"] == "ok"

        # Investigation family end to end — no 503, real persistence.
        created = client.post(
            "/api/v1/investigations",
            json={"title": "Live slice", "owner": "analyst-1", "priority": "high"},
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

        listed = client.get(
            f"/api/v1/investigations/{investigation_id}/evidence"
        )
        assert listed.status_code == 200
        assert [e["content"] for e in listed.json()["data"]] == ["beacon"]

        # Memory end to end — versioned store behind the API.
        memory_created = client.post(
            "/api/v1/memory",
            json={
                "type": "attack_pattern",
                "source_investigation_id": investigation_id,
                "confidence": 0.6,
                "status": "candidate",
            },
        )
        assert memory_created.status_code == 201
        memory_id = memory_created.json()["data"]["id"]
        memory_created_at = memory_created.json()["data"]["created_at"]

        superseded = client.put(
            f"/api/v1/memory/{memory_id}",
            json={
                "type": "attack_pattern",
                "source_investigation_id": investigation_id,
                "confidence": 0.8,
                "status": "verified",
                "version": 2,
                "created_at": memory_created_at,
            },
        )
        assert superseded.status_code == 200

        history = client.get(f"/api/v1/memory/{memory_id}/history")
        assert history.status_code == 200
        assert [v["version"] for v in history.json()["data"]] == [1, 2]

    # Planner composition against the live store (service seam, see module
    # docstring): get_memory completes with live data; find_neighbors over an
    # explicitly-unavailable graph store yields the contained
    # graph.store_unavailable failure (the failure-isolation contract).
    get_memory = asyncio.run(
        _execute_live_planner_action(
            GetMemoryAction(
                action_id="live-act-1", memory_id=MemoryItemId(memory_id)
            )
        )
    )
    assert get_memory.status.value == "completed"
    assert isinstance(get_memory.value, MemoryItem)
    assert get_memory.value.id.value == memory_id
    assert get_memory.value.version == 2

    neighbors = asyncio.run(
        _execute_live_planner_action(
            FindNeighborsAction(
                action_id="live-act-2",
                entity_id=EntityId("ent-1"),
                depth=1,
                max_nodes=5,
            )
        )
    )
    assert neighbors.status.value == "failed"
    assert neighbors.error is not None
    assert neighbors.error.code == "graph.store_unavailable"


async def _execute_live_planner_action(action: PlannerAction) -> ExecutionResult:
    """Execute one action through the live Planner Service composition."""

    engine = live_engine()
    try:
        factory = create_session_factory(engine)
        async with session_scope(factory) as session:
            investigation = InvestigationService(
                PostgresInvestigationRepository(session),
                PostgresEvidenceRepository(session),
                PostgresFindingRepository(session),
                PostgresReportRepository(session),
                PostgresOutcomeRepository(session),
                PostgresTraceRepository(session),
            )
            planner = PlannerService(
                investigation,
                GraphService(UnavailableGraphRepository()),
                MemoryService(PostgresMemoryRepository(session)),
            )
            return await planner.execute(action)
    finally:
        await engine.dispose()
