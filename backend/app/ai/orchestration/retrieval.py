"""Retrieval Flow.

The AI Runtime composition that connects the Memory Agent to the RAG Pipeline
(ADR-010; the "Memory Agent ↔ pipeline composition" deferred by ES-013): the
Memory Agent selects the retrieval strategies for the investigation, and the RAG
Pipeline executes them into a validated Investigation Context and its
provider-neutral prompt.

The agent runs through the **Agent Runtime** — the single execution path
(ADR-013). A failed agent execution is contained by the runtime and re-raised
here as :class:`~app.ai.errors.MemoryAgentError` carrying the stable failure
code: unlike the Investigation Loop, this flow has no degrade path — its caller
must know retrieval planning failed. Insufficient context is reported by the
pipeline's validation gate (``InsufficientContextError``).

Each run appends one RETRIEVAL entry to the Investigation Trace (best-effort),
preserving which strategies were selected and how much knowledge was assembled.
Identifiers and timestamps are caller-supplied (``IdSource``/``Clock``).
"""

import logging

from app.ai.agents.memory.agent import MemoryAgent, RetrievalPlanRequest
from app.ai.agents.memory.plan import RetrievalPlanId
from app.ai.agents.planner.state import InvestigationState
from app.ai.agents.runtime import AgentRuntime
from app.ai.errors import MemoryAgentError
from app.ai.orchestration.tracing import (
    Clock,
    IdSource,
    TraceSink,
    record_best_effort,
)
from app.ai.rag.pipeline import RagPipeline, RagResult
from app.domain.identifiers import TraceEntryId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef

logger = logging.getLogger(__name__)

_MEMORY_ACTOR = ActorRef("memory-agent")


class RetrievalFlow:
    """Runs the Memory Agent then the RAG Pipeline as one flow (stateless)."""

    def __init__(
        self,
        agent: MemoryAgent,
        pipeline: RagPipeline,
        ids: IdSource,
        clock: Clock,
        trace: TraceSink,
    ) -> None:
        self._agent = agent
        self._pipeline = pipeline
        self._ids = ids
        self._clock = clock
        self._trace = trace
        self._runtime = AgentRuntime()

    async def run(
        self, state: InvestigationState, plan_id: RetrievalPlanId
    ) -> RagResult:
        """Select retrieval strategies, then execute them into a validated context."""

        planning = await self._runtime.run(
            self._agent, RetrievalPlanRequest(state=state, plan_id=plan_id)
        )
        if planning.product is None:
            raise MemoryAgentError(
                f"Retrieval planning failed ({planning.error})."
            )
        plan = planning.product

        result = await self._pipeline.run(state, plan)

        entry = TraceEntry(
            id=TraceEntryId(self._ids.new_id()),
            investigation_id=state.investigation_id,
            kind=TraceEntryKind.RETRIEVAL,
            actor=_MEMORY_ACTOR,
            summary=(
                f"retrieved {len(result.context.knowledge)} item(s) via "
                f"{[strategy.value for strategy in plan.strategies]}"
            ),
            reference=plan_id.value,
            created_at=self._clock.now(),
        )
        await record_best_effort(self._trace, entry)

        logger.info(
            "retrieval flow completed investigation_id=%s plan_id=%s strategies=%s",
            state.investigation_id.value,
            plan_id.value,
            [strategy.value for strategy in plan.strategies],
        )
        return result
