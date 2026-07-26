"""Live Investigation Loop run over the real stack (ES-044/045).

Opt-in (`pytest -m live_ai`): requires a reachable PostgreSQL (compose
``data`` profile, ``POSTGRES_HOST=127.0.0.1``) **and** a ``GOOGLE_API_KEY``
(skipped otherwise). Verifies the ES-044 exit criteria against the real
provider: a run over the live stack persists chronological
decision/execution/outcome trace entries readable through the ES-045 read
surface, and an invalid provider key degrades the run to an ``escalated``
outcome with the stable failure code — never an HTTP error — leaving the
investigation intact.
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.config.ai import LLMProviderChoice, get_llm_selection
from app.domain.trace import TraceEntryKind
from app.infrastructure.ai.resilience import reset_breakers
from app.main import create_app
from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    require_identity,
)
from app.presentation.api.authorization import require_authorization
from tests.live.support import ensure_schema, live_engine, truncate_tables
from tests.live.test_gemini_smoke import load_google_api_key

pytestmark = pytest.mark.live_ai

_TABLES = (
    "trace_entry",
    "investigation_outcome",
    "report",
    "finding",
    "evidence",
    "investigation",
    "memory_outbox",
    "memory_item",
)


def _reset_database() -> None:
    async def scenario() -> None:
        engine = live_engine()
        try:
            await truncate_tables(engine, *_TABLES)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def _configured_provider_key() -> str:
    """The secret name the active LLM adapter actually consumes."""

    if get_llm_selection().provider is LLMProviderChoice.NVIDIA:
        return "NVIDIA_API_KEY"
    return "GOOGLE_API_KEY"


def _client() -> TestClient:
    app = create_app()
    # Both gates are bypassed the same way test_live_api.py does (ES-062):
    # create_investigation resolves require_identity directly to derive the
    # owner from the verified subject, not only through require_authorization,
    # so overriding authorization alone leaves every request at 401. This
    # suite exercises the AI run path, not the auth boundary.
    app.dependency_overrides[require_authorization] = lambda: None
    app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
        subject="analyst-1", kind=IdentityKind.HUMAN
    )
    return TestClient(app)


def _create_investigation(client: TestClient) -> str:
    created = client.post(
        "/api/v1/investigations",
        json={
            "title": "Suspicious beaconing from workstation",
            "owner": "analyst-1",
            "priority": "high",
        },
    )
    assert created.status_code == 201
    investigation_id = created.json()["data"]["id"]
    assert isinstance(investigation_id, str)
    evidence = client.post(
        f"/api/v1/investigations/{investigation_id}/evidence",
        json={
            "source": "edr",
            "integrity": "verified",
            "content": "Periodic DNS requests to rare domain every 60s.",
        },
    )
    assert evidence.status_code == 201
    return investigation_id


def test_live_run_persists_a_chronological_trace() -> None:
    if not load_google_api_key():
        pytest.skip("GOOGLE_API_KEY is not configured")
    ensure_schema()
    _reset_database()

    with _client() as client:
        investigation_id = _create_investigation(client)

        run = client.post(f"/api/v1/investigations/{investigation_id}/run")
        assert run.status_code == 200
        data = run.json()["data"]
        assert data["end"] in {"completed", "escalated", "exhausted"}
        assert data["cycles"] >= 1

        # The persisted trace is readable in append order (ES-045) and ends
        # with the loop outcome; every cycle contributed its entries.
        trace = client.get(f"/api/v1/investigations/{investigation_id}/trace")
        assert trace.status_code == 200
        kinds = [entry["kind"] for entry in trace.json()["data"]]
        assert kinds, "the run left no trace"
        assert kinds[-1] == TraceEntryKind.LOOP_OUTCOME.value
        if data["actions"]:
            assert TraceEntryKind.PLANNER_DECISION.value in kinds
            assert TraceEntryKind.ACTION_EXECUTION.value in kinds

        # The investigation survived its run.
        fetched = client.get(f"/api/v1/investigations/{investigation_id}")
        assert fetched.status_code == 200


def test_invalid_provider_key_escalates_without_breaking_anything() -> None:
    ensure_schema()
    _reset_database()

    # Poison the key of the **configured** provider (ES-054 made the adapter
    # selectable; poisoning GOOGLE_API_KEY under LLM_PROVIDER=nvidia left the
    # run perfectly healthy and this assertion vacuous).
    key_name = _configured_provider_key()
    saved = os.environ.get(key_name)
    os.environ[key_name] = "invalid-key-for-escalation-test"
    try:
        with _client() as client:
            investigation_id = _create_investigation(client)

            run = client.post(f"/api/v1/investigations/{investigation_id}/run")

            # ADR-013 live proof: a rejected credential is an outcome.
            assert run.status_code == 200
            data = run.json()["data"]
            assert data["end"] == "escalated"
            assert data["failure_code"] == "ai.llm_provider_error"

            fetched = client.get(f"/api/v1/investigations/{investigation_id}")
            assert fetched.status_code == 200
            assert fetched.json()["data"]["status"] == "created"
    finally:
        if saved is None:
            os.environ.pop(key_name, None)
        else:
            os.environ[key_name] = saved
        # The rejected credential produced real failures against the live
        # provider; clear the process-wide breaker so a later test in the same
        # process does not inherit an unhealthy verdict (ES-067).
        reset_breakers()
