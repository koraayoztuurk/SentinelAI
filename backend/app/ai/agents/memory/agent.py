"""Memory Agent.

The concrete ``memory-agent`` that reasons over an already-assembled Investigation
State and selects which documented retrieval strategies should participate in
retrieval, producing exactly one typed Retrieval Plan (memory-architecture §10/§17,
rag-architecture §14/§15). It is the Knowledge Steward gateway: it *selects*
strategies but never retrieves, coordinates sources, assembles context or persists
anything — those belong to the RAG Pipeline (ES-013).

Reasoning boundary: the agent builds a provider request from the state, obtains a
provider response, and transforms a minimal structured (JSON) response into one
typed Retrieval Plan. The prompt content and JSON shape are implementation details
of the documented transformation boundary. Unknown strategies are ignored while
recognized strategies are preserved; an empty Retrieval Plan results only when no
recognized strategy remains. Precondition violations raise ``MemoryAgentError``.
"""

import json
import logging
from dataclasses import dataclass

from app.ai.agents.base import AgentIdentity
from app.ai.agents.memory.plan import RetrievalPlan, RetrievalPlanId, RetrievalStrategy
from app.ai.agents.planner.state import InvestigationState
from app.ai.errors import MemoryAgentError
from app.ai.providers.llm import LLMProvider, LLMRequest

logger = logging.getLogger(__name__)

MEMORY_AGENT_IDENTITY = AgentIdentity("memory-agent")


@dataclass(frozen=True, slots=True)
class RetrievalPlanRequest:
    """The typed execution request of the Memory Agent (ADR-013)."""

    state: InvestigationState
    plan_id: RetrievalPlanId


class MemoryAgent:
    """Selects the retrieval strategies for an investigation (stateless)."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @property
    def identity(self) -> AgentIdentity:
        return MEMORY_AGENT_IDENTITY

    async def execute(self, request: RetrievalPlanRequest) -> RetrievalPlan:
        """Run one planning cycle through the typed agent contract (ADR-013)."""

        return await self.plan(request.state, request.plan_id)

    async def plan(
        self, state: InvestigationState, plan_id: RetrievalPlanId
    ) -> RetrievalPlan:
        """Reason over the provided state and return one Retrieval Plan."""

        self._validate(state)
        response = await self._llm.generate(self._build_request(state))
        result = self._to_plan(response.text, state, plan_id)
        logger.info(
            "memory agent planned plan_id=%s strategies=%s",
            plan_id.value,
            [strategy.value for strategy in result.strategies],
        )
        return result

    @staticmethod
    def _validate(state: InvestigationState) -> None:
        if not state.objectives:
            raise MemoryAgentError(
                "Investigation State must define at least one objective."
            )

    @staticmethod
    def _build_request(state: InvestigationState) -> LLMRequest:
        # Prompt content is an implementation detail of the documented
        # transformation boundary (memory-architecture §17). It describes the
        # exact JSON shape and strategy vocabulary `_to_plan` accepts so a
        # real provider can actually play (the ES-044 planner-prompt
        # precedent); anything else still resolves to an empty selection.
        prompt = (
            "You are the knowledge steward of a security investigation "
            "platform.\n"
            "Select which retrieval strategies should gather context for "
            "the investigation below and respond with ONLY a JSON object "
            "(no prose, no code fences), of exactly this shape:\n"
            '{"strategies": ["semantic", "graph", "structured"]}\n'
            "Available strategies:\n"
            '- "semantic": similarity search over organizational memory '
            "(past investigations, analyst notes)\n"
            '- "graph": the knowledge-graph neighbourhood of the '
            "investigation's entities\n"
            '- "structured": the investigation\'s own recorded memory '
            "items\n"
            '- "external": external threat intelligence (MITRE ATT&CK '
            "techniques, CVE lookups)\n"
            '- "hybrid": semantic + graph + structured together\n'
            "Select every strategy that would add investigative value.\n"
            "Investigation state:\n"
            f"investigation_id={state.investigation_id.value}\n"
            f"status={state.status}\n"
            f"objectives={list(state.objectives)}\n"
            f"confidence={state.confidence.value}"
        )
        return LLMRequest(prompt=prompt)

    @staticmethod
    def _to_plan(
        text: str, state: InvestigationState, plan_id: RetrievalPlanId
    ) -> RetrievalPlan:
        recognized = MemoryAgent._parse_strategies(text)
        # Emit in enum declaration order (canonical, deterministic, deduplicated).
        strategies = tuple(
            strategy for strategy in RetrievalStrategy if strategy in recognized
        )
        return RetrievalPlan(
            plan_id=plan_id,
            investigation_id=state.investigation_id,
            strategies=strategies,
        )

    @staticmethod
    def _parse_strategies(text: str) -> set[RetrievalStrategy]:
        try:
            payload = json.loads(text)
        except ValueError:
            return set()
        if not isinstance(payload, dict):
            return set()

        tokens = payload.get("strategies")
        if not isinstance(tokens, list):
            return set()

        recognized: set[RetrievalStrategy] = set()
        for token in tokens:
            if isinstance(token, str):
                try:
                    recognized.add(RetrievalStrategy(token))
                except ValueError:
                    # Unknown strategy: ignore while preserving recognized ones.
                    continue
        return recognized
