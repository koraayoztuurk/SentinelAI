"""Concrete Investigation State assembler (ES-044).

First realization of the Investigation Workspace / Context Builder
responsibility (planner-agent §4): assembles the
:class:`~app.ai.agents.planner.state.InvestigationState` the Planner Agent
reasons over from the Investigation Service's data — the AI Runtime composes
backend service interfaces one way (ADR-010) and never touches persistence.

Assembly decisions (ES-044, recorded in the tracker):

- **Objectives** — a single objective derived from the investigation title
  (the platform has no separate objective source yet).
- **Confidence** — the highest finding confidence, ``0.0`` with no findings
  (the state's confidence reflects the strongest supported conclusion).
- **History** — the most recent trace entries as ``kind: summary`` lines
  (bounded), so the agent observes what already happened, including its own
  earlier decisions.
- **Tasks** — empty: no Task service exists (tracker: Task ownership is an
  open documentation gap).
- **Knowledge** (ES-051) — retrieved-knowledge lines are attached by the
  runner (once per run, before the loop); ``next_state`` preserves them across
  cycles, so the planner keeps observing the same retrieved context without
  re-retrieval.
"""

from dataclasses import replace

from app.ai.agents.graph_analysis.analysis import (
    EntitySnapshot,
    GraphContext,
    RelationshipSnapshot,
)
from app.ai.agents.planner.state import InvestigationState
from app.ai.agents.threat_intel.report import (
    ThreatIntelEntity,
    ThreatIntelSeed,
)
from app.ai.agents.validation.assessment import (
    EvidenceSnapshot,
    FindingSnapshot,
    ValidationContext,
)
from app.application.graph import GraphService
from app.application.investigation import InvestigationService
from app.application.planner.actions import ExecutionResult
from app.domain.identifiers import EntityId, InvestigationId
from app.domain.value_objects import Confidence
from app.shared.exceptions import SentinelAIError

_HISTORY_LIMIT = 10

# Resource bounds only (mirroring the retriever's neighbourhood bounds).
_GRAPH_SEED_LIMIT = 3
_NEIGHBOR_LIMIT = 10


class InvestigationStateAssembler:
    """Assembles Investigation States from the Investigation Service."""

    def __init__(
        self,
        investigations: InvestigationService,
        graph: GraphService | None = None,
    ) -> None:
        self._investigations = investigations
        # Optional (additive, ES-057): the graph-context assembly consults
        # the Graph Service; compositions without a graph store skip it.
        self._graph = graph

    async def assemble(
        self, investigation_id: InvestigationId
    ) -> InvestigationState:
        """Assemble the current state snapshot of an investigation."""

        investigation = await self._investigations.get(investigation_id)
        evidence = await self._investigations.list_evidence(investigation_id)
        findings = await self._investigations.list_findings(investigation_id)
        trace = await self._investigations.list_trace(investigation_id)

        confidence = max(
            (finding.confidence.value for finding in findings), default=0.0
        )
        history = tuple(
            f"{entry.kind.value}: {entry.summary}"
            for entry in trace[-_HISTORY_LIMIT:]
        )
        return InvestigationState(
            investigation_id=investigation_id,
            status=investigation.status.value,
            confidence=Confidence(confidence),
            objectives=(f"Investigate: {investigation.title}",),
            evidence_ids=tuple(item.id for item in evidence),
            finding_ids=tuple(finding.id for finding in findings),
            history=history,
        )

    async def assemble_validation_context(
        self, investigation_id: InvestigationId
    ) -> ValidationContext | None:
        """Assemble the material the Validation Agent reasons over (ES-056).

        ``None`` when the investigation has no findings — there is nothing to
        validate, and the caller skips the step quietly.
        """

        findings = await self._investigations.list_findings(investigation_id)
        if not findings:
            return None
        investigation = await self._investigations.get(investigation_id)
        evidence = await self._investigations.list_evidence(investigation_id)
        return ValidationContext(
            investigation_id=investigation_id,
            objectives=(f"Investigate: {investigation.title}",),
            findings=tuple(
                FindingSnapshot(
                    id=finding.id,
                    status=finding.status.value,
                    confidence=finding.confidence,
                    supporting_evidence=finding.supporting_evidence,
                )
                for finding in findings
            ),
            evidence=tuple(
                EvidenceSnapshot(
                    id=item.id,
                    source=item.source.value,
                    integrity=item.integrity.value,
                    content=item.content,
                )
                for item in evidence
            ),
        )

    async def assemble_graph_context(
        self, investigation_id: InvestigationId
    ) -> GraphContext | None:
        """Assemble the neighbourhood the Graph Analysis Agent reasons over.

        Seeds derive from the findings' related entities (the investigation's
        only entity source, mirroring the retriever/visualization pattern);
        dangling cross-store references are observable-and-skipped (§8a).
        ``None`` when no graph store is composed or no seed entity resolves —
        there is nothing to analyze, and the caller skips the step quietly.
        """

        if self._graph is None:
            return None
        findings = await self._investigations.list_findings(investigation_id)
        seeds: list[EntityId] = []
        for finding in findings:
            for entity_id in finding.related_entities:
                if entity_id not in seeds:
                    seeds.append(entity_id)
        if not seeds:
            return None

        investigation = await self._investigations.get(investigation_id)
        entities: dict[str, EntitySnapshot] = {}
        relationships: dict[str, RelationshipSnapshot] = {}
        for seed in seeds[:_GRAPH_SEED_LIMIT]:
            try:
                seed_entity = await self._graph.get_entity(seed)
                neighbors = await self._graph.find_neighbors(
                    seed, depth=1, max_nodes=_NEIGHBOR_LIMIT
                )
                incident = await self._graph.list_relationships_for_entity(
                    seed
                )
            except SentinelAIError:
                # A dangling entity reference or a contained graph failure
                # skips this seed only; the other seeds still contribute.
                continue
            for entity in (seed_entity, *neighbors):
                entities[entity.id.value] = EntitySnapshot(
                    id=entity.id,
                    type=entity.type.value,
                    display_name=entity.display_name,
                    confidence=entity.confidence,
                )
            for relationship in incident:
                relationships[relationship.id.value] = RelationshipSnapshot(
                    id=relationship.id,
                    source_entity_id=relationship.source_entity_id,
                    target_entity_id=relationship.target_entity_id,
                    type=relationship.type.value,
                    confidence=relationship.confidence,
                )
        if not entities:
            return None
        return GraphContext(
            investigation_id=investigation_id,
            objectives=(f"Investigate: {investigation.title}",),
            entities=tuple(entities.values()),
            relationships=tuple(relationships.values()),
        )

    async def assemble_threat_intel_seed(
        self, investigation_id: InvestigationId
    ) -> ThreatIntelSeed:
        """Assemble the seed the Threat Intel Flow focuses its lookups on.

        Objectives are always present (title-derived, as everywhere); the
        entity list comes from the findings' related entities resolved
        through the Graph Service when one is composed — dangling references
        are observable-and-skipped (§8a). An entity-less seed is valid: the
        objectives alone can still hit external knowledge.
        """

        investigation = await self._investigations.get(investigation_id)
        entities: list[ThreatIntelEntity] = []
        if self._graph is not None:
            findings = await self._investigations.list_findings(
                investigation_id
            )
            seeds: list[EntityId] = []
            for finding in findings:
                for entity_id in finding.related_entities:
                    if entity_id not in seeds:
                        seeds.append(entity_id)
            for seed in seeds[:_GRAPH_SEED_LIMIT]:
                try:
                    entity = await self._graph.get_entity(seed)
                except SentinelAIError:
                    continue
                entities.append(
                    ThreatIntelEntity(
                        id=entity.id,
                        type=entity.type.value,
                        display_name=entity.display_name,
                    )
                )
        return ThreatIntelSeed(
            investigation_id=investigation_id,
            objectives=(f"Investigate: {investigation.title}",),
            entities=tuple(entities),
        )

    async def next_state(
        self, state: InvestigationState, result: ExecutionResult
    ) -> InvestigationState:
        """Re-assemble after an executed action (the loop's ``StateAssembler``).

        The retrieved knowledge attached to the run's initial state is carried
        forward: re-assembly reflects the investigation's new persisted state,
        while the run's retrieval context stays observable to the agent.
        """

        assembled = await self.assemble(state.investigation_id)
        return replace(assembled, knowledge=state.knowledge)
