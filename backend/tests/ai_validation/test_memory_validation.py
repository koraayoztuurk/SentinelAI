"""Memory Validation (ES-035, ai-validation §5).

Verifies the Memory Agent's behavioral properties: every provider response
resolves to exactly one typed Retrieval Plan (safe degradation), strategy
selection is consistent and canonical (behavioral consistency), the plan is
bound to the caller-provided investigation and plan id (responsibility
alignment) and the reasoning input derives from the assembled Investigation
State (reasoning verification).
"""

import asyncio

import pytest

from app.ai import MemoryAgent, RetrievalPlan, RetrievalPlanId, RetrievalStrategy
from app.domain.identifiers import InvestigationId
from tests.ai_validation.support import (
    ADVERSARIAL_RESPONSES,
    RecordingLLM,
    ScriptedLLM,
    make_state,
)

pytestmark = pytest.mark.ai

_PLAN_ID = RetrievalPlanId("p-1")


def test_every_provider_response_yields_exactly_one_plan() -> None:
    """Arbitrary provider output never breaks the typed plan contract."""

    async def scenario() -> None:
        for response in ADVERSARIAL_RESPONSES:
            agent = MemoryAgent(ScriptedLLM(response))
            plan = await agent.plan(make_state(), _PLAN_ID)
            assert isinstance(plan, RetrievalPlan)
            # Unrecognized output degrades to "no strategy determined",
            # never to an invented strategy.
            assert plan.strategies == ()

    asyncio.run(scenario())


def test_partially_recognized_selection_preserves_the_recognized() -> None:
    """Unknown vocabulary is ignored while recognized strategies survive."""

    async def scenario() -> None:
        agent = MemoryAgent(
            ScriptedLLM('{"strategies": ["bogus", "semantic", 42, "graph"]}')
        )
        plan = await agent.plan(make_state(), _PLAN_ID)
        assert plan.strategies == (
            RetrievalStrategy.SEMANTIC,
            RetrievalStrategy.GRAPH,
        )

    asyncio.run(scenario())


def test_selection_is_canonical_and_deduplicated() -> None:
    """Order and duplication in the provider output never leak into the plan."""

    async def scenario() -> None:
        reversed_dupes = MemoryAgent(
            ScriptedLLM(
                '{"strategies": ["structured", "graph", "structured", "graph"]}'
            )
        )
        plan = await reversed_dupes.plan(make_state(), _PLAN_ID)
        assert plan.strategies == (
            RetrievalStrategy.GRAPH,
            RetrievalStrategy.STRUCTURED,
        )

    asyncio.run(scenario())


def test_repeated_plans_are_consistent() -> None:
    """The same state and provider behavior produce the same plan."""

    async def scenario() -> None:
        agent = MemoryAgent(ScriptedLLM('{"strategies": ["semantic"]}'))
        plans = [await agent.plan(make_state(), _PLAN_ID) for _ in range(3)]
        assert plans[0] == plans[1] == plans[2]

    asyncio.run(scenario())


def test_plan_is_bound_to_the_provided_investigation() -> None:
    """The plan carries the caller's investigation and plan identifiers."""

    async def scenario() -> None:
        agent = MemoryAgent(ScriptedLLM('{"strategies": ["semantic"]}'))
        plan = await agent.plan(make_state("inv-7"), RetrievalPlanId("p-9"))
        assert plan.investigation_id == InvestigationId("inv-7")
        assert plan.plan_id == RetrievalPlanId("p-9")

    asyncio.run(scenario())


def test_reasoning_consumes_the_assembled_state() -> None:
    """The provider request demonstrably derives from the Investigation State."""

    async def scenario() -> None:
        llm = RecordingLLM('{"strategies": ["semantic"]}')
        state = make_state("inv-42", objectives=("attribute the campaign",))
        await MemoryAgent(llm).plan(state, _PLAN_ID)

        assert len(llm.requests) == 1
        prompt = llm.requests[0].prompt
        assert "inv-42" in prompt
        assert "attribute the campaign" in prompt

    asyncio.run(scenario())
