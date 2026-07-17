"""Threat Intel Flow (ES-059).

The AI Runtime composition that connects the ES-058 external knowledge
providers to the Threat Intelligence Agent (agent-architecture §6): the flow
derives **focused queries** from the investigation seed (the objectives plus
the finding-named entities — closing the ES-058 note that prose objectives
rarely hit CVE keyword search), retrieves external intelligence through the
provider-neutral port (the agent's permitted sources: threat intelligence
providers, IOC lookup, CVE database), and runs the agent over the assembled
context through the **Agent Runtime** — the single execution path (ADR-013).

Failure containment mirrors the retriever (ES-058): one provider's outage on
one query never blanks the rest. Zero retrieved intelligence is a quiet skip
(``None`` — nothing external applies, not a failure). A failed agent
execution is re-raised as :class:`~app.ai.errors.ThreatIntelAgentError`
carrying the stable code — like the Graph Analysis Flow, the caller decides
how to contain it.

Each produced report appends one THREAT_INTEL entry to the Investigation
Trace (best-effort), preserving what was correlated and from how many
external items.
"""

import logging
from typing import Protocol

from app.ai.agents.runtime import AgentRuntime
from app.ai.agents.threat_intel.agent import (
    ThreatIntelAgent,
    ThreatIntelRequest,
)
from app.ai.agents.threat_intel.report import (
    ThreatIntelContext,
    ThreatIntelReport,
    ThreatIntelSeed,
)
from app.ai.errors import ThreatIntelAgentError
from app.ai.orchestration.tracing import (
    Clock,
    IdSource,
    TraceSink,
    record_best_effort,
)
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeProvider,
    ExternalKnowledgeQuery,
)
from app.domain.identifiers import InvestigationId, TraceEntryId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)

_THREAT_INTEL_ACTOR = ActorRef("threat-intel-agent")

# Resource bounds: how many entity-focused queries run per enrichment and how
# much deduplicated intelligence enters the agent's context (prompt budget —
# rag §16 compression/budget remain deferred).
_ENTITY_QUERY_LIMIT = 5
_INTELLIGENCE_LIMIT = 10


class ThreatIntelSeedAssembler(Protocol):
    """Assembles the investigation-side seed the lookups are focused on."""

    async def assemble_threat_intel_seed(
        self, investigation_id: InvestigationId
    ) -> ThreatIntelSeed: ...


class ThreatIntelFlow:
    """Retrieves external intelligence and runs the agent over it."""

    def __init__(
        self,
        agent: ThreatIntelAgent,
        assembler: ThreatIntelSeedAssembler,
        external: tuple[ExternalKnowledgeProvider, ...],
        ids: IdSource,
        clock: Clock,
        trace: TraceSink,
    ) -> None:
        self._agent = agent
        self._assembler = assembler
        self._external = external
        self._ids = ids
        self._clock = clock
        self._trace = trace
        self._runtime = AgentRuntime()

    async def enrich(
        self, investigation_id: InvestigationId
    ) -> ThreatIntelReport | None:
        """Correlate the investigation with external intelligence.

        ``None`` when no external intelligence was retrieved (no providers
        composed, feeds down, or genuinely nothing matching) — a quiet skip.
        """

        seed = await self._assembler.assemble_threat_intel_seed(
            investigation_id
        )
        intelligence = await self._retrieve(seed)
        if not intelligence:
            logger.info(
                "threat intel skipped (no external intelligence) "
                "investigation_id=%s",
                investigation_id.value,
            )
            return None

        context = ThreatIntelContext(
            investigation_id=investigation_id,
            objectives=seed.objectives,
            entities=seed.entities,
            intelligence=intelligence,
        )
        result = await self._runtime.run(
            self._agent, ThreatIntelRequest(context=context)
        )
        if result.product is None:
            raise ThreatIntelAgentError(
                f"Threat intelligence correlation failed ({result.error})."
            )
        report = result.product

        entry = TraceEntry(
            id=TraceEntryId(self._ids.new_id()),
            investigation_id=investigation_id,
            kind=TraceEntryKind.THREAT_INTEL,
            actor=_THREAT_INTEL_ACTOR,
            summary=(
                f"correlated {len(intelligence)} external item(s), "
                f"{len(report.observations)} observation(s): "
                f"{report.summary}"
            ),
            reference=investigation_id.value,
            created_at=self._clock.now(),
        )
        await record_best_effort(self._trace, entry)

        logger.info(
            "threat intel flow completed investigation_id=%s "
            "intelligence=%s observations=%s",
            investigation_id.value,
            len(intelligence),
            len(report.observations),
        )
        return report

    async def _retrieve(
        self, seed: ThreatIntelSeed
    ) -> tuple[ExternalKnowledgeItem, ...]:
        """Run the focused queries; dedupe by origin; contain per provider."""

        queries: list[str] = ["; ".join(seed.objectives)]
        for entity in seed.entities[:_ENTITY_QUERY_LIMIT]:
            if entity.display_name not in queries:
                queries.append(entity.display_name)

        items: dict[tuple[str, str], ExternalKnowledgeItem] = {}
        for query in queries:
            request = ExternalKnowledgeQuery(query=query)
            for provider in self._external:
                try:
                    results = await provider.lookup(request)
                except SentinelAIError as exc:
                    # One feed's outage on one query never blanks the rest.
                    logger.warning(
                        "threat intel lookup contained failure "
                        "investigation_id=%s code=%s",
                        seed.investigation_id.value,
                        exc.code,
                    )
                    continue
                for item in results:
                    items.setdefault((item.source, item.reference), item)
        return tuple(items.values())[:_INTELLIGENCE_LIMIT]
