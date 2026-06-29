"""Unit tests for the Planner Agent (ES-011).

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
    PlannerAgent,
    PlannerAgentError,
)
from app.application.planner.actions import (
    ControlAction,
    ControlKind,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
)
from app.domain.identifiers import EntityId, InvestigationId, MemoryItemId
from app.domain.value_objects import Confidence


class _FakeLLM:
    def __init__(self, response_text: str) -> None:
        self._text = response_text

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=self._text)


def _state() -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId("inv-1"),
        status="active",
        confidence=Confidence(0.4),
        objectives=("determine whether malicious activity exists",),
    )


def _decide(response_text: str, action_id: str = "a-1"):  # type: ignore[no-untyped-def]
    agent = PlannerAgent(_FakeLLM(response_text))
    return asyncio.run(agent.decide(_state(), action_id))


def test_control_complete() -> None:
    result = _decide('{"action": "control", "control": "complete"}')
    assert result == ControlAction(action_id="a-1", kind=ControlKind.COMPLETE)


def test_control_escalate() -> None:
    result = _decide('{"action": "control", "control": "escalate"}')
    assert result == ControlAction(action_id="a-1", kind=ControlKind.ESCALATE)


def test_get_investigation_uses_state_id() -> None:
    result = _decide('{"action": "get_investigation"}')
    assert result == GetInvestigationAction(
        action_id="a-1", investigation_id=InvestigationId("inv-1")
    )


def test_get_memory_builds_typed_id() -> None:
    result = _decide('{"action": "get_memory", "memory_id": "m-1"}')
    assert result == GetMemoryAction(
        action_id="a-1", memory_id=MemoryItemId("m-1")
    )


def test_find_neighbors_builds_typed_action() -> None:
    result = _decide(
        '{"action": "find_neighbors", "entity_id": "e-1", "depth": 2, "max_nodes": 10}'
    )
    assert result == FindNeighborsAction(
        action_id="a-1", entity_id=EntityId("e-1"), depth=2, max_nodes=10
    )


def test_invalid_json_falls_back_to_escalate() -> None:
    result = _decide("not json at all")
    assert result == ControlAction(action_id="a-1", kind=ControlKind.ESCALATE)


def test_unknown_action_falls_back_to_escalate() -> None:
    result = _decide('{"action": "frobnicate"}')
    assert result == ControlAction(action_id="a-1", kind=ControlKind.ESCALATE)


def test_missing_field_falls_back_to_escalate() -> None:
    result = _decide('{"action": "get_memory"}')
    assert result == ControlAction(action_id="a-1", kind=ControlKind.ESCALATE)


def test_wrong_type_falls_back_to_escalate() -> None:
    result = _decide(
        '{"action":"find_neighbors","entity_id":"e-1","depth":"x","max_nodes":10}'
    )
    assert result == ControlAction(action_id="a-1", kind=ControlKind.ESCALATE)


def test_blank_action_id_raises() -> None:
    with pytest.raises(PlannerAgentError):
        _decide('{"action": "control", "control": "complete"}', action_id="  ")


def test_missing_objectives_raises() -> None:
    async def scenario() -> None:
        agent = PlannerAgent(_FakeLLM('{"action": "control", "control": "complete"}'))
        state = InvestigationState(
            investigation_id=InvestigationId("inv-1"),
            status="active",
            confidence=Confidence(0.4),
            objectives=(),
        )
        with pytest.raises(PlannerAgentError):
            await agent.decide(state, "a-1")

    asyncio.run(scenario())


def test_identity() -> None:
    assert PlannerAgent(_FakeLLM("{}")).identity == AgentIdentity("planner-agent")
