"""Planner Agent.

The concrete ``planner-agent`` that reasons over an already-assembled Investigation
State and produces exactly one Planner Action (ES-008) via the AI Foundation LLM
provider (ES-009).

Reasoning boundary (planner-agent §6): the agent builds a provider request from the
state, obtains a provider response, and transforms a minimal structured (JSON)
response into one typed Planner Action. The prompt content and the JSON shape are
implementation details of the documented transformation boundary. An invalid,
unknown or malformed response resolves to an escalate action; precondition
violations raise ``PlannerAgentError``.
"""

import json
import logging
from dataclasses import dataclass

from app.ai.agents.base import AgentIdentity
from app.ai.agents.planner.state import InvestigationState
from app.ai.errors import PlannerAgentError
from app.ai.providers.llm import LLMProvider, LLMRequest
from app.application.planner.actions import (
    ControlAction,
    ControlKind,
    FindNeighborsAction,
    GetInvestigationAction,
    GetMemoryAction,
    PlannerAction,
)
from app.domain.identifiers import EntityId, MemoryItemId

logger = logging.getLogger(__name__)

PLANNER_AGENT_IDENTITY = AgentIdentity("planner-agent")


@dataclass(frozen=True, slots=True)
class PlannerDecisionRequest:
    """The typed execution request of the Planner Agent (ADR-013)."""

    state: InvestigationState
    action_id: str


class PlannerAgent:
    """Selects the next Planner Action for an investigation (stateless)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def identity(self) -> AgentIdentity:
        return PLANNER_AGENT_IDENTITY

    async def execute(self, request: PlannerDecisionRequest) -> PlannerAction:
        """Run one decision through the typed agent contract (ADR-013)."""

        return await self.decide(request.state, request.action_id)

    async def decide(
        self, state: InvestigationState, action_id: str
    ) -> PlannerAction:
        """Reason over the provided state and return one Planner Action."""

        self._validate(action_id, state)
        response = await self._llm.generate(self._build_request(state))
        result = self._to_action(response.text, state, action_id)
        logger.info(
            "planner agent decided action_id=%s action=%s",
            action_id,
            type(result).__name__,
        )
        return result

    @staticmethod
    def _validate(action_id: str, state: InvestigationState) -> None:
        if not action_id.strip():
            raise PlannerAgentError("Planner action_id must not be blank.")
        if not state.objectives:
            raise PlannerAgentError(
                "Investigation State must define at least one objective."
            )

    @staticmethod
    def _build_request(state: InvestigationState) -> LLMRequest:
        # Prompt content is an implementation detail; kept minimal.
        prompt = (
            "Select the next planner action and respond as JSON.\n"
            f"investigation_id={state.investigation_id.value}\n"
            f"status={state.status}\n"
            f"objectives={list(state.objectives)}\n"
            f"confidence={state.confidence.value}\n"
            f"pending_tasks={[task.value for task in state.pending_tasks]}"
        )
        return LLMRequest(prompt=prompt)

    @staticmethod
    def _to_action(
        text: str, state: InvestigationState, action_id: str
    ) -> PlannerAction:
        escalate = ControlAction(action_id=action_id, kind=ControlKind.ESCALATE)

        try:
            payload = json.loads(text)
        except ValueError:
            return escalate
        if not isinstance(payload, dict):
            return escalate

        action = payload.get("action")

        if action == "control":
            if payload.get("control") == "complete":
                return ControlAction(action_id=action_id, kind=ControlKind.COMPLETE)
            return escalate

        if action == "get_investigation":
            return GetInvestigationAction(
                action_id=action_id, investigation_id=state.investigation_id
            )

        if action == "get_memory":
            memory_id = payload.get("memory_id")
            if isinstance(memory_id, str) and memory_id.strip():
                return GetMemoryAction(
                    action_id=action_id, memory_id=MemoryItemId(memory_id)
                )
            return escalate

        if action == "find_neighbors":
            entity_id = payload.get("entity_id")
            depth = payload.get("depth")
            max_nodes = payload.get("max_nodes")
            if (
                isinstance(entity_id, str)
                and entity_id.strip()
                and isinstance(depth, int)
                and not isinstance(depth, bool)
                and isinstance(max_nodes, int)
                and not isinstance(max_nodes, bool)
            ):
                return FindNeighborsAction(
                    action_id=action_id,
                    entity_id=EntityId(entity_id),
                    depth=depth,
                    max_nodes=max_nodes,
                )
            return escalate

        return escalate
