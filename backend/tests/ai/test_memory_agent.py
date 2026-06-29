"""Unit tests for the Memory Agent (ES-012).

Plain pytest functions with a fake LLM provider returning canned JSON. No live AI
calls.
"""

import asyncio

import pytest

from app.ai import (
    AgentIdentity,
    InvestigationState,
    LLMRequest,
    LLMResponse,
    MemoryAgent,
    MemoryAgentError,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
)
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence


class _FakeLLM:
    def __init__(self, response_text: str) -> None:
        self._text = response_text

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self._text)


def _state(
    objectives: tuple[str, ...] = ("determine malicious activity",),
) -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="active",
        confidence=Confidence(0.4),
        objectives=objectives,
    )


def _plan(response_text: str, plan_id: str = "p-1") -> RetrievalPlan:
    agent = MemoryAgent(_FakeLLM(response_text))
    return asyncio.run(agent.plan(_state(), RetrievalPlanId(plan_id)))


def test_single_recognized_strategy() -> None:
    result = _plan('{"strategies": ["semantic"]}')
    assert result == RetrievalPlan(
        plan_id=RetrievalPlanId("p-1"),
        investigation_id=InvestigationId("inv-1"),
        strategies=(RetrievalStrategy.SEMANTIC,),
    )


def test_multiple_strategies_canonical_order_and_deduplicated() -> None:
    # Provided out of order and with a duplicate; emitted in enum order, once each.
    result = _plan('{"strategies": ["graph", "semantic", "graph"]}')
    assert result.strategies == (
        RetrievalStrategy.SEMANTIC,
        RetrievalStrategy.GRAPH,
    )


def test_unknown_strategies_ignored_recognized_preserved() -> None:
    result = _plan('{"strategies": ["frobnicate", "graph", "nonsense"]}')
    assert result.strategies == (RetrievalStrategy.GRAPH,)


def test_all_unknown_yields_empty_plan() -> None:
    result = _plan('{"strategies": ["frobnicate", "nonsense"]}')
    assert result.strategies == ()


def test_strategies_not_a_list_yields_empty_plan() -> None:
    result = _plan('{"strategies": "semantic"}')
    assert result.strategies == ()


def test_non_dict_payload_yields_empty_plan() -> None:
    result = _plan('["semantic"]')
    assert result.strategies == ()


def test_invalid_json_yields_empty_plan() -> None:
    result = _plan("not json at all")
    assert result.strategies == ()


def test_empty_plan_preserves_identifiers() -> None:
    result = _plan("not json at all")
    assert result.plan_id == RetrievalPlanId("p-1")
    assert result.investigation_id == InvestigationId("inv-1")


def test_missing_objectives_raises() -> None:
    async def scenario() -> None:
        agent = MemoryAgent(_FakeLLM('{"strategies": ["semantic"]}'))
        with pytest.raises(MemoryAgentError):
            await agent.plan(_state(objectives=()), RetrievalPlanId("p-1"))

    asyncio.run(scenario())


def test_blank_plan_id_raises() -> None:
    with pytest.raises(MemoryAgentError):
        RetrievalPlanId("")


def test_whitespace_plan_id_raises() -> None:
    with pytest.raises(MemoryAgentError):
        RetrievalPlanId("  ")


def test_identity() -> None:
    assert MemoryAgent(_FakeLLM("{}")).identity == AgentIdentity("memory-agent")
