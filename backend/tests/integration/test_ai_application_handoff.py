"""Integration tests: AI Runtime ↔ Application collaboration (ES-034).

Verifies the two documented AI → application hand-offs without introducing any
new orchestrator (integration-testing §5 — cross-domain validation):

- Planner Agent → Planner Service: the typed ``PlannerAction`` the agent produces
  (ES-011) is executed by the single-action Planner Service (ES-008) against the
  backend services.
- Memory Agent → RAG Pipeline: the typed ``RetrievalPlan`` the agent produces
  (ES-012) drives the pipeline's retrieval and context engineering (ES-013).

The LLM provider is a deterministic scripted fake; the AI layer touches no
persistence and reaches business data only through the composed services.
"""

import asyncio

import pytest

from app.ai import (
    InsufficientContextError,
    InvestigationState,
    LLMRequest,
    LLMResponse,
    MemoryAgent,
    PlannerAgent,
    RagPipeline,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
    RetrievedItem,
    RetrievedKnowledge,
)
from app.application.planner import (
    ControlAction,
    ControlKind,
    ExecutionStatus,
    PlannerService,
)
from app.domain.identifiers import InvestigationId
from app.domain.investigation import Investigation
from app.domain.value_objects import Confidence
from tests.support.builders import (
    build_investigation,
    make_graph_service,
    make_investigation_service,
    make_memory_service,
)

pytestmark = pytest.mark.integration


class _ScriptedLLM:
    """Deterministic LLM provider double returning a fixed response."""

    def __init__(self, text: str) -> None:
        self._text = text

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self._text)


class _PlanHonoringRetriever:
    """Retriever double that yields one item per strategy in the received plan."""

    def __init__(self) -> None:
        self.received: RetrievalPlan | None = None

    async def retrieve(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RetrievedKnowledge:
        self.received = plan
        items = tuple(
            RetrievedItem(
                strategy=strategy,
                source=strategy.value,
                reference=f"{strategy.value}-1",
                content=f"{strategy.value} fact",
                confidence=Confidence(0.6),
            )
            for strategy in plan.strategies
        )
        return RetrievedKnowledge(plan_id=plan.plan_id, items=items)


def _state(investigation_id: str = "inv-1") -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId(investigation_id),
        status="active",
        confidence=Confidence(0.5),
        objectives=("determine malicious activity",),
    )


def _planner_service() -> PlannerService:
    return PlannerService(
        make_investigation_service(), make_graph_service(), make_memory_service()
    )


# ------------------------------------------- Planner Agent → Planner Service


def test_planner_agent_decision_executes_against_services() -> None:
    """The agent's typed action completes through the Planner Service."""

    async def scenario() -> None:
        investigation = make_investigation_service()
        planner = PlannerService(
            investigation, make_graph_service(), make_memory_service()
        )
        await investigation.create(build_investigation("inv-1"))

        agent = PlannerAgent(_ScriptedLLM('{"action": "get_investigation"}'))
        action = await agent.decide(_state("inv-1"), "act-1")
        result = await planner.execute(action)

        assert result.status is ExecutionStatus.COMPLETED
        assert isinstance(result.value, Investigation)
        assert result.value.id == InvestigationId("inv-1")
        assert result.action_id == "act-1"

    asyncio.run(scenario())


def test_planner_agent_escalation_is_executable() -> None:
    """A malformed provider response degrades to an executable escalate action."""

    async def scenario() -> None:
        agent = PlannerAgent(_ScriptedLLM("not json"))
        action = await agent.decide(_state(), "act-1")

        assert isinstance(action, ControlAction)
        assert action.kind is ControlKind.ESCALATE

        result = await _planner_service().execute(action)
        assert result.status is ExecutionStatus.COMPLETED
        assert result.value is ControlKind.ESCALATE

    asyncio.run(scenario())


# ------------------------------------------------ Memory Agent → RAG Pipeline


def test_memory_agent_plan_drives_rag_pipeline() -> None:
    """The agent-selected strategies flow into retrieval and the built prompt."""

    async def scenario() -> None:
        agent = MemoryAgent(
            _ScriptedLLM('{"strategies": ["structured", "graph", "bogus"]}')
        )
        plan = await agent.plan(_state(), RetrievalPlanId("p-1"))
        # Canonical enum order, unknown strategy ignored.
        assert plan.strategies == (
            RetrievalStrategy.GRAPH,
            RetrievalStrategy.STRUCTURED,
        )

        retriever = _PlanHonoringRetriever()
        result = await RagPipeline(retriever).run(_state(), plan)

        assert retriever.received is plan
        assert len(result.context.knowledge) == 2
        assert "graph fact" in result.prompt.text
        assert "structured fact" in result.prompt.text

    asyncio.run(scenario())


def test_memory_agent_empty_plan_yields_insufficient_context() -> None:
    """An empty Retrieval Plan is reported explicitly by the pipeline."""

    async def scenario() -> None:
        agent = MemoryAgent(_ScriptedLLM('{"strategies": []}'))
        plan = await agent.plan(_state(), RetrievalPlanId("p-1"))
        assert plan.strategies == ()

        with pytest.raises(InsufficientContextError):
            await RagPipeline(_PlanHonoringRetriever()).run(_state(), plan)

    asyncio.run(scenario())
