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


def _provider_key(choice: LLMProviderChoice) -> str:
    """The secret name a given LLM adapter actually consumes."""

    if choice is LLMProviderChoice.NVIDIA:
        return "NVIDIA_API_KEY"
    return "GOOGLE_API_KEY"


def _configured_provider_keys() -> tuple[str, ...]:
    """Every secret the composed LLM chain can serve a call from.

    With a fallback configured (ES-067) the chain survives a rejected
    credential on the primary — that is the whole point of it — so poisoning
    only the primary no longer produces an escalation. To keep proving what
    this test exists to prove (ADR-013: a rejected credential is an *outcome*,
    not a crash), every provider in the chain has to be refused.
    """

    selection = get_llm_selection()
    keys = [_provider_key(selection.provider)]
    if selection.fallback_provider is not None:
        fallback_key = _provider_key(selection.fallback_provider)
        if fallback_key not in keys:
            keys.append(fallback_key)
    return tuple(keys)


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

    # Poison the key of **every** provider in the composed chain (ES-054 made
    # the adapter selectable, ES-067 added a fallback behind it). Poisoning
    # only one leaves the assertion vacuous in a different way each time:
    # GOOGLE_API_KEY under LLM_PROVIDER=nvidia never touched the run at all,
    # and poisoning the primary while a healthy fallback stands behind it is
    # served successfully by design.
    key_names = _configured_provider_keys()
    saved = {name: os.environ.get(name) for name in key_names}
    for name in key_names:
        os.environ[name] = "invalid-key-for-escalation-test"
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
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        # The rejected credentials produced real failures against the live
        # providers; clear the process-wide breakers so a later test in the same
        # process does not inherit an unhealthy verdict (ES-067).
        reset_breakers()
