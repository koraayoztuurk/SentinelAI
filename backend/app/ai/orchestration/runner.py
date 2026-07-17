"""Investigation run entry point (ES-044, retrieval-enriched by ES-051).

The invocation surface ADR-010 anticipated: assemble the initial Investigation
State, optionally enrich it with retrieved knowledge through the Retrieval
Flow, then run the Investigation Loop over it. This is the single composition
the presentation run endpoint delegates to; it adds no reasoning of its own.

Retrieval integration (ES-051, owner decision): the Retrieval Flow runs **once
per run** before the loop — the retrieved knowledge is attached to the initial
state and preserved across cycles by the assembler, so a bounded synchronous
run pays one retrieval (one Memory Agent call + one query embedding), not one
per cycle. Retrieval is supportive, never critical: a failed or insufficient
retrieval is logged and the run proceeds without retrieved knowledge —
mirroring the platform's failure-isolation stance (a knowledge-layer outage
must not take the decision loop down with it).
"""

import logging
from dataclasses import replace

from app.ai.agents.graph_analysis.analysis import GraphObservation
from app.ai.agents.memory.plan import RetrievalPlanId
from app.ai.agents.threat_intel.report import ThreatIntelObservation
from app.ai.errors import (
    GraphAnalysisError,
    InsufficientContextError,
    MemoryAgentError,
    ThreatIntelAgentError,
)
from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.ai.orchestration.graph_analysis import GraphAnalysisFlow
from app.ai.orchestration.loop import InvestigationLoop, LoopOutcome
from app.ai.orchestration.retrieval import RetrievalFlow
from app.ai.orchestration.threat_intel import ThreatIntelFlow
from app.ai.orchestration.tracing import IdSource
from app.ai.rag.retriever import RetrievedItem
from app.domain.identifiers import InvestigationId

logger = logging.getLogger(__name__)

# Each knowledge line is bounded so retrieved content cannot flood the
# planner prompt (context budget/compression remain rag §16 deferrals).
_KNOWLEDGE_CONTENT_LIMIT = 300


def _knowledge_line(item: RetrievedItem) -> str:
    content = item.content.strip()
    if len(content) > _KNOWLEDGE_CONTENT_LIMIT:
        content = content[:_KNOWLEDGE_CONTENT_LIMIT] + "…"
    return (
        f"[{item.strategy.value}] {item.source}:{item.reference} "
        f"(confidence={item.confidence.value:.2f}) {content}"
    )


def _observation_line(observation: GraphObservation) -> str:
    detail = observation.detail.strip()
    if len(detail) > _KNOWLEDGE_CONTENT_LIMIT:
        detail = detail[:_KNOWLEDGE_CONTENT_LIMIT] + "…"
    entities = ",".join(e.value for e in observation.entities)
    return (
        f"[graph-analysis] {observation.kind.value}"
        f"{f' (entities: {entities})' if entities else ''} {detail}"
    )


def _intel_line(observation: ThreatIntelObservation) -> str:
    detail = observation.detail.strip()
    if len(detail) > _KNOWLEDGE_CONTENT_LIMIT:
        detail = detail[:_KNOWLEDGE_CONTENT_LIMIT] + "…"
    references = ",".join(observation.references)
    return (
        f"[threat-intel] {observation.kind.value}"
        f"{f' (refs: {references})' if references else ''} {detail}"
    )


class InvestigationRunner:
    """Assembles the initial state and runs the Investigation Loop."""

    def __init__(
        self,
        assembler: InvestigationStateAssembler,
        loop: InvestigationLoop,
        retrieval: RetrievalFlow | None = None,
        ids: IdSource | None = None,
        graph_analysis: GraphAnalysisFlow | None = None,
        threat_intel: ThreatIntelFlow | None = None,
    ) -> None:
        if retrieval is not None and ids is None:
            raise ValueError(
                "An IdSource is required when a Retrieval Flow is provided "
                "(retrieval-plan identifiers are caller-supplied)."
            )
        self._assembler = assembler
        self._loop = loop
        self._retrieval = retrieval
        self._ids = ids
        self._graph_analysis = graph_analysis
        self._threat_intel = threat_intel

    async def run(self, investigation_id: InvestigationId) -> LoopOutcome:
        """Run the loop for one investigation and return its outcome."""

        state = await self._assembler.assemble(investigation_id)
        if self._retrieval is not None and self._ids is not None:
            try:
                result = await self._retrieval.run(
                    state, RetrievalPlanId(self._ids.new_id())
                )
                state = replace(
                    state,
                    knowledge=tuple(
                        _knowledge_line(item)
                        for item in result.context.knowledge
                    ),
                )
            except (MemoryAgentError, InsufficientContextError) as exc:
                # Supportive capability: the run continues without retrieved
                # knowledge. (An empty knowledge base fails the pipeline's
                # validation gate by design — the normal early-investigation
                # condition, not an operational fault.)
                logger.info(
                    "run proceeds without retrieved knowledge "
                    "investigation_id=%s code=%s",
                    investigation_id.value,
                    getattr(exc, "code", "unknown"),
                )
        if self._graph_analysis is not None:
            # Graph analysis enrichment (ES-057): once per run, like
            # retrieval — its observations join the planner-visible
            # knowledge; a failed analysis is contained (supportive, never
            # critical).
            try:
                analysis = await self._graph_analysis.analyze(
                    investigation_id
                )
            except GraphAnalysisError as exc:
                analysis = None
                logger.info(
                    "run proceeds without graph analysis "
                    "investigation_id=%s code=%s",
                    investigation_id.value,
                    exc.code,
                )
            if analysis is not None and analysis.observations:
                state = replace(
                    state,
                    knowledge=state.knowledge
                    + tuple(
                        _observation_line(observation)
                        for observation in analysis.observations
                    ),
                )
        if self._threat_intel is not None:
            # Threat intelligence enrichment (ES-059): once per run, after
            # graph analysis — external correlations join the planner-visible
            # knowledge; a failed correlation is contained (supportive,
            # never critical).
            try:
                report = await self._threat_intel.enrich(investigation_id)
            except ThreatIntelAgentError as exc:
                report = None
                logger.info(
                    "run proceeds without threat intelligence "
                    "investigation_id=%s code=%s",
                    investigation_id.value,
                    exc.code,
                )
            if report is not None and report.observations:
                state = replace(
                    state,
                    knowledge=state.knowledge
                    + tuple(
                        _intel_line(observation)
                        for observation in report.observations
                    ),
                )
        return await self._loop.run(state)
