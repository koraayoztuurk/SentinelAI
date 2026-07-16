"""Graph Analysis Flow (ES-057).

The AI Runtime composition that runs the Graph Analysis Agent over an
investigation's assembled entity neighbourhood (agent-architecture §6). The
agent runs through the **Agent Runtime** — the single execution path
(ADR-013); a contained agent failure is re-raised as
:class:`~app.ai.errors.GraphAnalysisError` carrying the stable code — like
the Retrieval Flow, its caller decides how to contain the failure.

Each produced analysis appends one GRAPH_ANALYSIS entry to the
Investigation Trace (best-effort), preserving what the agent observed.
``None`` signals there was nothing to analyze (no graph store composed, or
no finding-seeded entity resolves) — a quiet skip, not a failure.
"""

import logging
from typing import Protocol

from app.ai.agents.graph_analysis.agent import (
    GraphAnalysisAgent,
    GraphAnalysisRequest,
)
from app.ai.agents.graph_analysis.analysis import GraphAnalysis, GraphContext
from app.ai.agents.runtime import AgentRuntime
from app.ai.errors import GraphAnalysisError
from app.ai.orchestration.tracing import (
    Clock,
    IdSource,
    TraceSink,
    record_best_effort,
)
from app.domain.identifiers import InvestigationId, TraceEntryId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef

logger = logging.getLogger(__name__)

_GRAPH_ANALYSIS_ACTOR = ActorRef("graph-analysis-agent")


class GraphContextAssembler(Protocol):
    """Assembles the neighbourhood under analysis (Workspace / Context Builder)."""

    async def assemble_graph_context(
        self, investigation_id: InvestigationId
    ) -> GraphContext | None: ...


class GraphAnalysisFlow:
    """Runs the Graph Analysis Agent over the assembled neighbourhood."""

    def __init__(
        self,
        agent: GraphAnalysisAgent,
        assembler: GraphContextAssembler,
        ids: IdSource,
        clock: Clock,
        trace: TraceSink,
    ) -> None:
        self._agent = agent
        self._assembler = assembler
        self._ids = ids
        self._clock = clock
        self._trace = trace
        self._runtime = AgentRuntime()

    async def analyze(
        self, investigation_id: InvestigationId
    ) -> GraphAnalysis | None:
        """Analyze the investigation's neighbourhood; ``None`` when empty."""

        context = await self._assembler.assemble_graph_context(
            investigation_id
        )
        if context is None:
            logger.info(
                "graph analysis skipped (no neighbourhood) "
                "investigation_id=%s",
                investigation_id.value,
            )
            return None

        result = await self._runtime.run(
            self._agent, GraphAnalysisRequest(context=context)
        )
        if result.product is None:
            raise GraphAnalysisError(
                f"Graph analysis failed ({result.error})."
            )
        analysis = result.product

        entry = TraceEntry(
            id=TraceEntryId(self._ids.new_id()),
            investigation_id=investigation_id,
            kind=TraceEntryKind.GRAPH_ANALYSIS,
            actor=_GRAPH_ANALYSIS_ACTOR,
            summary=(
                f"analyzed {len(context.entities)} entities, "
                f"{len(analysis.observations)} observation(s): "
                f"{analysis.summary}"
            ),
            reference=investigation_id.value,
            created_at=self._clock.now(),
        )
        await record_best_effort(self._trace, entry)

        logger.info(
            "graph analysis flow completed investigation_id=%s "
            "observations=%s",
            investigation_id.value,
            len(analysis.observations),
        )
        return analysis
