"""Tests for the investigation run surface (ES-044).

``POST /api/v1/investigations/{id}/run`` drives the Investigation Loop
synchronously within the configured cycle budget. Verified over in-memory
services and a scripted LLM provider: the run summary projection, the
degrade-to-escalation contract (a provider failure is an outcome, never an
HTTP error; the investigation stays intact), budget exhaustion, contained
downstream failures and the trace record of every step.
"""

import asyncio

from fastapi.testclient import TestClient

from app.ai.agents.planner.agent import PlannerAgent
from app.ai.errors import LLMProviderError
from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.loop import InvestigationLoop
from app.ai.orchestration.runner import InvestigationRunner
from app.ai.providers.llm import LLMRequest, LLMResponse
from app.application.investigation import InvestigationService
from app.application.planner import PlannerService
from app.domain.identifiers import InvestigationId
from app.domain.trace import TraceEntryKind
from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.generation import get_clock, get_id_generator
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_runner,
    get_investigation_service,
)
from tests.support.builders import (
    FIXED_TIME,
    make_graph_service,
    make_investigation_service,
    make_memory_service,
)
from tests.support.doubles import FixedClock, SequentialIdGenerator


class _ScriptedLLM:
    """Returns the scripted responses in order."""

    def __init__(self, *responses: str) -> None:
        self._responses = list(responses)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self._responses.pop(0))


class _BrokenLLM:
    """Fails like an unreachable/misconfigured provider (ES-043 mapping)."""

    async def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMProviderError("provider rejected the credentials")


class _Stack:
    """The run composition over in-memory services with a scripted provider."""

    def __init__(self, llm: _ScriptedLLM | _BrokenLLM, budget: int = 3) -> None:
        self.investigation: InvestigationService = make_investigation_service()
        planner = PlannerService(
            self.investigation, make_graph_service(), make_memory_service()
        )
        assembler = InvestigationStateAssembler(self.investigation)
        loop = InvestigationLoop(
            PlannerAgent(llm),
            planner,
            assembler,
            SequentialIdGenerator("run"),
            FixedClock(FIXED_TIME),
            self.investigation,
            budget,
        )
        runner = InvestigationRunner(assembler, loop)

        app = create_app()
        app.dependency_overrides[require_authorization] = lambda: None
        app.dependency_overrides[get_investigation_service] = (
            lambda: self.investigation
        )
        app.dependency_overrides[get_investigation_runner] = lambda: runner
        app.dependency_overrides[get_id_generator] = (
            lambda: SequentialIdGenerator()
        )
        app.dependency_overrides[get_clock] = lambda: FixedClock(FIXED_TIME)
        self.client = TestClient(app)

    def create_investigation(self) -> str:
        response = self.client.post(
            "/api/v1/investigations",
            json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
        )
        assert response.status_code == 201
        investigation_id = response.json()["data"]["id"]
        assert isinstance(investigation_id, str)
        return investigation_id

    def trace_kinds(self, investigation_id: str) -> list[str]:
        entries = asyncio.run(
            self.investigation.list_trace(InvestigationId(investigation_id))
        )
        return [entry.kind.value for entry in entries]


def test_run_completes_and_records_the_trace() -> None:
    stack = _Stack(
        _ScriptedLLM(
            '{"action":"get_investigation"}',
            '{"action":"control","control":"complete"}',
        )
    )
    investigation_id = stack.create_investigation()

    response = stack.client.post(f"/api/v1/investigations/{investigation_id}/run")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["end"] == "completed"
    assert data["cycles"] == 2
    assert data["failure_code"] is None
    assert [a["execution_status"] for a in data["actions"]] == [
        "completed",
        "completed",
    ]
    assert data["actions"][0]["target"] == "investigation"
    assert data["actions"][1]["target"] is None  # the control action

    # Every decision/execution and the outcome are in the trace, in order.
    expected_kinds = [
        TraceEntryKind.PLANNER_DECISION.value,
        TraceEntryKind.ACTION_EXECUTION.value,
        TraceEntryKind.PLANNER_DECISION.value,
        TraceEntryKind.ACTION_EXECUTION.value,
        TraceEntryKind.LOOP_OUTCOME.value,
    ]
    assert stack.trace_kinds(investigation_id) == expected_kinds

    # The ES-045 read surface exposes the same trace over HTTP, same order.
    trace = stack.client.get(f"/api/v1/investigations/{investigation_id}/trace")
    assert trace.status_code == 200
    assert [e["kind"] for e in trace.json()["data"]] == expected_kinds


def test_provider_failure_degrades_to_escalated_not_http_error() -> None:
    stack = _Stack(_BrokenLLM())
    investigation_id = stack.create_investigation()

    response = stack.client.post(f"/api/v1/investigations/{investigation_id}/run")

    # ADR-013: never an HTTP failure — an observable escalated outcome.
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["end"] == "escalated"
    assert data["failure_code"] == "ai.llm_provider_error"
    assert data["actions"] == []

    # The investigation itself is intact.
    fetched = stack.client.get(f"/api/v1/investigations/{investigation_id}")
    assert fetched.json()["data"]["status"] == "created"
    assert stack.trace_kinds(investigation_id) == [
        TraceEntryKind.LOOP_OUTCOME.value
    ]


def test_budget_exhaustion_returns_exhausted() -> None:
    stack = _Stack(
        _ScriptedLLM(*['{"action":"get_investigation"}'] * 3), budget=3
    )
    investigation_id = stack.create_investigation()

    response = stack.client.post(f"/api/v1/investigations/{investigation_id}/run")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["end"] == "exhausted"
    assert data["cycles"] == 3
    assert len(data["actions"]) == 3


def test_contained_downstream_failure_does_not_stop_the_run() -> None:
    stack = _Stack(
        _ScriptedLLM(
            '{"action":"find_neighbors","entity_id":"e-x","depth":1,'
            '"max_nodes":5}',
            '{"action":"control","control":"complete"}',
        )
    )
    investigation_id = stack.create_investigation()

    response = stack.client.post(f"/api/v1/investigations/{investigation_id}/run")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["end"] == "completed"
    failed, control = data["actions"]
    assert failed["execution_status"] == "failed"
    assert failed["error_code"] == "graph.entity_not_found"
    assert control["execution_status"] == "completed"


def test_unknown_investigation_returns_404() -> None:
    stack = _Stack(_ScriptedLLM('{"action":"control","control":"complete"}'))

    response = stack.client.post("/api/v1/investigations/missing/run")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "investigation.not_found"


def test_runner_not_bound_returns_503() -> None:
    # No lifespan → no persistence registry → the live runner provider
    # reports the explicit unbound contract, like every other service seam.
    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None
    client = TestClient(app)

    response = client.post("/api/v1/investigations/inv-1/run")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "api.persistence_not_configured"
