"""Concrete source-backed Retriever (ES-051).

Realizes the AI Runtime's :class:`~app.ai.rag.retriever.Retriever` port over
the real knowledge sources (rag-architecture §15/§18) — the infrastructure
edge implementing an AI-layer port, exactly like the concrete LLM/embedding
providers (ES-043/049); the AI layer itself keeps importing no infrastructure.

Strategy execution:

- **semantic** — the investigation objectives are embedded through the
  AI-layer embedding provider (the ES-049 "AI-side query embedding" consumer)
  and matched against the derived Memory Item embeddings in the vector store;
  every match is mapped back to the **authoritative** Memory Item (content is
  never read from the derived store — database-architecture §8a).
- **structured** — the latest Memory Items originating from the investigation,
  via the Memory Service.
- **graph** — the neighbourhood of the findings' related entities, via the
  Graph Service (entities within one hop + incident relationships).
- **external** — deferred to the Threat Intelligence milestone: the strategy
  contributes nothing (never an error).
- **hybrid** — executes semantic + graph + structured together (rag §15).

Failure isolation: one source's failure (graph store unreachable, embedding
provider outage) is contained per strategy — the remaining strategies still
contribute, mirroring the platform's contained-failure stance. Deprecated
Memory Items never enter the context (deprecation marks knowledge no longer
valid). Dangling cross-store references (a finding naming an entity absent
from the graph) are observable-and-skipped, per §8a.
"""

import logging

from app.ai.agents.memory.plan import RetrievalPlan, RetrievalStrategy
from app.ai.agents.planner.state import InvestigationState
from app.ai.providers.embedding import EmbeddingProvider
from app.ai.rag.retriever import RetrievedItem, RetrievedKnowledge
from app.application.graph import GraphService
from app.application.investigation import InvestigationService
from app.application.memory import MemoryService
from app.application.memory.errors import MemoryNotFoundError
from app.application.memory.vector_store import MemoryVectorStore
from app.domain.enums import MemoryStatus
from app.domain.identifiers import EntityId, MemoryItemId
from app.domain.memory_item import MemoryItem
from app.domain.value_objects import Confidence
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)

_MEMORY_SOURCE = "memory"
_GRAPH_SOURCE = "graph"

# Resource bounds only (they cap how much context is gathered; they never
# alter retrieval semantics) — mirroring the Graph Service's traversal bounds.
_SEMANTIC_LIMIT = 5
_GRAPH_SEED_LIMIT = 3
_NEIGHBOR_LIMIT = 10

# hybrid executes the organizational strategies together (rag §15).
_HYBRID_EXPANSION = (
    RetrievalStrategy.SEMANTIC,
    RetrievalStrategy.GRAPH,
    RetrievalStrategy.STRUCTURED,
)


def _memory_content(item: MemoryItem) -> str:
    return item.content.strip() or item.type.value


def _clamped_confidence(score: float) -> Confidence:
    # Cosine similarity may fall outside [0, 1]; Confidence is a [0, 1] value.
    return Confidence(min(1.0, max(0.0, score)))


class CompositeRetriever:
    """Executes a Retrieval Plan against the live knowledge sources."""

    def __init__(
        self,
        embedding: EmbeddingProvider,
        vector_store: MemoryVectorStore,
        memory: MemoryService,
        investigations: InvestigationService,
        graph: GraphService,
    ) -> None:
        self._embedding = embedding
        self._vector_store = vector_store
        self._memory = memory
        self._investigations = investigations
        self._graph = graph

    async def retrieve(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RetrievedKnowledge:
        """Execute the plan's strategies; contain per-strategy failures."""

        strategies: list[RetrievalStrategy] = []
        for strategy in plan.strategies:
            expansion = (
                _HYBRID_EXPANSION
                if strategy is RetrievalStrategy.HYBRID
                else (strategy,)
            )
            for expanded in expansion:
                if expanded not in strategies:
                    strategies.append(expanded)

        items: list[RetrievedItem] = []
        for strategy in strategies:
            try:
                items.extend(await self._execute(strategy, state))
            except SentinelAIError as exc:
                logger.warning(
                    "retrieval strategy contained failure strategy=%s "
                    "investigation_id=%s code=%s",
                    strategy.value,
                    state.investigation_id.value,
                    exc.code,
                )
        return RetrievedKnowledge(plan_id=plan.plan_id, items=tuple(items))

    async def _execute(
        self, strategy: RetrievalStrategy, state: InvestigationState
    ) -> tuple[RetrievedItem, ...]:
        if strategy is RetrievalStrategy.SEMANTIC:
            return await self._semantic(state)
        if strategy is RetrievalStrategy.STRUCTURED:
            return await self._structured(state)
        if strategy is RetrievalStrategy.GRAPH:
            return await self._graph_neighbourhood(state)
        # external: deferred to the Threat Intelligence milestone — the
        # strategy contributes nothing rather than failing the plan.
        logger.debug(
            "retrieval strategy not yet available strategy=%s", strategy.value
        )
        return ()

    # ------------------------------------------------------------- semantic

    async def _semantic(
        self, state: InvestigationState
    ) -> tuple[RetrievedItem, ...]:
        query = "; ".join(state.objectives)
        vector = await self._embedding.embed(query)
        matches = await self._vector_store.search(vector, _SEMANTIC_LIMIT)

        items: list[RetrievedItem] = []
        for match in matches:
            try:
                item = await self._memory.get(MemoryItemId(match.memory_id))
            except MemoryNotFoundError:
                # The point's Memory Item is gone (derived state lags the
                # system of record) — observable, never fabricated.
                continue
            if item.status is MemoryStatus.DEPRECATED:
                continue
            items.append(
                RetrievedItem(
                    strategy=RetrievalStrategy.SEMANTIC,
                    source=_MEMORY_SOURCE,
                    reference=item.id.value,
                    content=_memory_content(item),
                    confidence=_clamped_confidence(match.score),
                )
            )
        return tuple(items)

    # ------------------------------------------------------------ structured

    async def _structured(
        self, state: InvestigationState
    ) -> tuple[RetrievedItem, ...]:
        latest = await self._memory.list_for_investigation(
            state.investigation_id
        )
        return tuple(
            RetrievedItem(
                strategy=RetrievalStrategy.STRUCTURED,
                source=_MEMORY_SOURCE,
                reference=item.id.value,
                content=_memory_content(item),
                confidence=item.confidence,
            )
            for item in latest
            if item.status is not MemoryStatus.DEPRECATED
        )

    # ----------------------------------------------------------------- graph

    async def _graph_neighbourhood(
        self, state: InvestigationState
    ) -> tuple[RetrievedItem, ...]:
        findings = await self._investigations.list_findings(
            state.investigation_id
        )
        seeds: list[EntityId] = []
        for finding in findings:
            for entity_id in finding.related_entities:
                if entity_id not in seeds:
                    seeds.append(entity_id)

        items: list[RetrievedItem] = []
        for seed in seeds[:_GRAPH_SEED_LIMIT]:
            try:
                items.extend(await self._seed_neighbourhood(seed))
            except SentinelAIError as exc:
                # A dangling entity reference (§8a) or a per-seed store error
                # skips that seed only; the other seeds still contribute.
                logger.info(
                    "graph retrieval skipped seed entity_id=%s code=%s",
                    seed.value,
                    exc.code,
                )
        return tuple(items)

    async def _seed_neighbourhood(
        self, seed: EntityId
    ) -> tuple[RetrievedItem, ...]:
        items: list[RetrievedItem] = []
        neighbors = await self._graph.find_neighbors(
            seed, depth=1, max_nodes=_NEIGHBOR_LIMIT
        )
        for entity in neighbors:
            items.append(
                RetrievedItem(
                    strategy=RetrievalStrategy.GRAPH,
                    source=_GRAPH_SOURCE,
                    reference=entity.id.value,
                    content=(
                        f"{entity.type.value} '{entity.display_name}' is "
                        f"within 1 hop of entity {seed.value}"
                    ),
                    confidence=entity.confidence,
                )
            )
        for relationship in await self._graph.list_relationships_for_entity(
            seed
        ):
            items.append(
                RetrievedItem(
                    strategy=RetrievalStrategy.GRAPH,
                    source=_GRAPH_SOURCE,
                    reference=relationship.id.value,
                    content=(
                        f"{relationship.source_entity_id.value} "
                        f"-[{relationship.type.value}]-> "
                        f"{relationship.target_entity_id.value}"
                    ),
                    confidence=relationship.confidence,
                )
            )
        return tuple(items)
