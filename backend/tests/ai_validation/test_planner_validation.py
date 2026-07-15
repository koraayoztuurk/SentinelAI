"""Planner Validation (ES-035, ai-validation §5).

Verifies the Planner Agent's behavioral properties as properties, not cases:
every conceivable provider response resolves to exactly one typed action (safe
degradation), repeated decisions over the same state are identical (decision
consistency), the decision can only target the caller-provided state
(architectural responsibility alignment) and the reasoning input demonstrably
derives from the assembled Investigation State (reasoning verification).
"""

import asyncio

import pytest

from app.ai import PlannerAgent
from app.application.planner.actions import (
    ChangeInvestigationStatusAction,
    ControlAction,
    ControlKind,
    CreateEntityAction,
    CreateInvestigationAction,
    CreateMemoryAction,
    CreateRelationshipAction,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
)
from app.domain.identifiers import InvestigationId
from tests.ai_validation.support import (
    ADVERSARIAL_RESPONSES,
    RecordingLLM,
    ScriptedLLM,
    make_state,
)

pytestmark = pytest.mark.ai

_TYPED_ACTIONS = (
    ControlAction,
    GetInvestigationAction,
    ChangeInvestigationStatusAction,
    FindNeighborsAction,
    GetMemoryAction,
    CreateInvestigationAction,
    CreateEntityAction,
    CreateRelationshipAction,
    CreateMemoryAction,
)


def test_every_provider_response_yields_exactly_one_typed_action() -> None:
    """Arbitrary provider output never breaks the typed decision contract."""

    async def scenario() -> None:
        for response in ADVERSARIAL_RESPONSES:
            agent = PlannerAgent(ScriptedLLM(response))
            action = await agent.decide(make_state(), "a-1")
            assert isinstance(action, _TYPED_ACTIONS)
            assert action.action_id == "a-1"

    asyncio.run(scenario())


def test_unrecognized_responses_escalate_never_complete() -> None:
    """Safe degradation escalates to the human analyst, never auto-completes."""

    async def scenario() -> None:
        for response in ADVERSARIAL_RESPONSES:
            agent = PlannerAgent(ScriptedLLM(response))
            action = await agent.decide(make_state(), "a-1")
            if isinstance(action, ControlAction):
                assert action.kind is ControlKind.ESCALATE

    asyncio.run(scenario())


def test_repeated_decisions_are_consistent() -> None:
    """The same state and provider behavior produce the same decision."""

    async def scenario() -> None:
        agent = PlannerAgent(ScriptedLLM('{"action": "get_investigation"}'))
        decisions = [await agent.decide(make_state(), "a-1") for _ in range(3)]
        assert decisions[0] == decisions[1] == decisions[2]

    asyncio.run(scenario())


def test_decision_targets_only_the_provided_state() -> None:
    """A provider cannot redirect the decision to a foreign investigation."""

    async def scenario() -> None:
        agent = PlannerAgent(
            ScriptedLLM(
                '{"action": "get_investigation", "investigation_id": "evil"}'
            )
        )
        action = await agent.decide(make_state("inv-1"), "a-1")
        assert isinstance(action, GetInvestigationAction)
        assert action.investigation_id == InvestigationId("inv-1")

    asyncio.run(scenario())


def test_reasoning_consumes_the_assembled_state() -> None:
    """The provider request demonstrably derives from the Investigation State."""

    async def scenario() -> None:
        llm = RecordingLLM('{"action": "get_investigation"}')
        state = make_state("inv-42", objectives=("identify lateral movement",))
        await PlannerAgent(llm).decide(state, "a-1")

        assert len(llm.requests) == 1
        prompt = llm.requests[0].prompt
        assert "inv-42" in prompt
        assert "identify lateral movement" in prompt

    asyncio.run(scenario())


def test_reasoning_observes_retrieved_knowledge() -> None:
    """Retrieved-knowledge lines attached to the state reach the provider
    request (ES-051: planner decisions can observe retrieval)."""

    async def scenario() -> None:
        from dataclasses import replace

        llm = RecordingLLM('{"action": "get_investigation"}')
        state = replace(
            make_state("inv-42"),
            knowledge=("[semantic] memory:m-7 (confidence=0.87) C2 beacon",),
        )
        await PlannerAgent(llm).decide(state, "a-1")

        prompt = llm.requests[0].prompt
        assert "retrieved_knowledge" in prompt
        assert "C2 beacon" in prompt

    asyncio.run(scenario())
