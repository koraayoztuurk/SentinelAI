"""Tests for the concrete source-backed Retriever (ES-051).

The CompositeRetriever executes a Retrieval Plan against the live knowledge
sources: semantic (query embedding + vector-store search, mapped back to the
authoritative Memory Items), structured (Memory Service), graph (Graph
Service neighbourhood). Deterministic fakes stand in for the embedding
provider and the vector store; the backend services run over the shared
in-memory doubles. Plain functions, ``asyncio.run``.
"""

import asyncio
from collections.abc import Mapping

from app.ai.agents.memory.plan import (
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
)
from app.ai.agents.planner.state import InvestigationState
from app.application.memory.errors import MemoryVectorStoreUnavailableError
from app.application.memory.vector_store import MemoryVectorMatch
from app.domain.enums import MemoryStatus
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence
from app.infrastructure.ai.retrieval import CompositeRetriever
from tests.support.builders import (
    build_entity,
    build_evidence,
    build_finding,
    build_investigation,
    build_memory_item,
    build_relationship,
    make_graph_service,
    make_investigation_service,
    make_memory_service,
)


class FixedEmbedding:
    """Deterministic embedding provider double (records the query)."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def embed(self, text: str) -> tuple[float, ...]:
        self.queries.append(text)
        return (1.0, 0.0, 0.0)


class ScriptedVectorStore:
    """Vector-store double returning a scripted match list."""

    def __init__(self, matches: tuple[MemoryVectorMatch, ...] = ()) -> None:
        self.matches = matches

    async def ensure_collection(self, dimensions: int) -> None:  # pragma: no cover
        return None

    async def upsert(
        self,
        memory_id: str,
        vector: tuple[float, ...],
        payload: Mapping[str, object],
    ) -> None:  # pragma: no cover - unused by retrieval
        return None

    async def search(
        self, vector: tuple[float, ...], limit: int
    ) -> tuple[MemoryVectorMatch, ...]:
        return self.matches[:limit]


class UnavailableVectorStore(ScriptedVectorStore):
    """Vector-store double whose search reports the store unreachable."""

    async def search(
        self, vector: tuple[float, ...], limit: int
    ) -> tuple[MemoryVectorMatch, ...]:
        raise MemoryVectorStoreUnavailableError(
            "The memory vector store is unreachable."
        )


def _match(memory_id: str, score: float) -> MemoryVectorMatch:
    return MemoryVectorMatch(
        memory_id=memory_id, score=score, payload={"memory_id": memory_id}
    )


def _state(investigation_id: str = "inv-1") -> InvestigationState:
    return InvestigationState(
        investigation_id=InvestigationId(investigation_id),
        status="active",
        confidence=Confidence(0.5),
        objectives=("Investigate: lateral movement",),
    )


def _plan(*strategies: RetrievalStrategy) -> RetrievalPlan:
    return RetrievalPlan(
        plan_id=RetrievalPlanId("plan-1"),
        investigation_id=InvestigationId("inv-1"),
        strategies=tuple(strategies),
    )


def test_semantic_maps_matches_to_authoritative_memory() -> None:
    async def scenario() -> None:
        memory = make_memory_service()
        await memory.create(
            build_memory_item(
                "m-1", content="C2 beacon pattern", source_investigation_id="inv-9"
            )
        )
        embedding = FixedEmbedding()
        retriever = CompositeRetriever(
            embedding,
            ScriptedVectorStore((_match("m-1", 0.87),)),
            memory,
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state(), _plan(RetrievalStrategy.SEMANTIC)
        )

        # The query derives from the objectives; the content comes from the
        # system of record, never from the derived store's payload.
        assert embedding.queries == ["Investigate: lateral movement"]
        assert len(knowledge.items) == 1
        item = knowledge.items[0]
        assert item.strategy is RetrievalStrategy.SEMANTIC
        assert item.source == "memory"
        assert item.reference == "m-1"
        assert item.content == "C2 beacon pattern"
        assert item.confidence.value == 0.87

    asyncio.run(scenario())


def test_semantic_skips_deprecated_and_missing_memory() -> None:
    async def scenario() -> None:
        memory = make_memory_service()
        await memory.create(build_memory_item("m-live", content="valid"))
        await memory.create(build_memory_item("m-old", content="stale"))
        await memory.deprecate(build_memory_item("m-old").id)

        retriever = CompositeRetriever(
            FixedEmbedding(),
            ScriptedVectorStore(
                (
                    _match("m-live", 0.9),
                    _match("m-old", 0.8),
                    _match("m-gone", 0.7),
                )
            ),
            memory,
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state(), _plan(RetrievalStrategy.SEMANTIC)
        )

        # Deprecated knowledge and dangling points never enter the context.
        assert [item.reference for item in knowledge.items] == ["m-live"]

    asyncio.run(scenario())


def test_semantic_confidence_is_clamped_to_valid_range() -> None:
    async def scenario() -> None:
        memory = make_memory_service()
        await memory.create(build_memory_item("m-1", content="x"))
        retriever = CompositeRetriever(
            FixedEmbedding(),
            ScriptedVectorStore((_match("m-1", 1.3),)),
            memory,
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state(), _plan(RetrievalStrategy.SEMANTIC)
        )

        assert knowledge.items[0].confidence.value == 1.0

    asyncio.run(scenario())


def test_structured_returns_investigation_memory_excluding_deprecated() -> None:
    async def scenario() -> None:
        memory = make_memory_service()
        await memory.create(
            build_memory_item(
                "m-1", source_investigation_id="inv-1", content="ours"
            )
        )
        await memory.create(
            build_memory_item(
                "m-2", source_investigation_id="inv-2", content="theirs"
            )
        )
        await memory.create(
            build_memory_item(
                "m-3",
                source_investigation_id="inv-1",
                content="retired",
                status=MemoryStatus.CANDIDATE,
            )
        )
        await memory.deprecate(build_memory_item("m-3").id)

        retriever = CompositeRetriever(
            FixedEmbedding(),
            ScriptedVectorStore(),
            memory,
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state("inv-1"), _plan(RetrievalStrategy.STRUCTURED)
        )

        assert [item.reference for item in knowledge.items] == ["m-1"]
        assert knowledge.items[0].strategy is RetrievalStrategy.STRUCTURED
        assert knowledge.items[0].content == "ours"

    asyncio.run(scenario())


def test_graph_retrieves_finding_seeded_neighbourhood() -> None:
    async def scenario() -> None:
        investigations = make_investigation_service()
        await investigations.create(build_investigation("inv-1"))
        await investigations.attach_evidence(build_evidence("ev-1", "inv-1"))
        await investigations.create_finding(
            build_finding(
                "f-1",
                "inv-1",
                supporting_evidence=("ev-1",),
                related_entities=("host-1",),
            )
        )

        graph = make_graph_service()
        await graph.create_entity(build_entity("host-1", display_name="HOST-1"))
        await graph.create_entity(
            build_entity("ip-1", type_value="ip", display_name="10.0.0.5")
        )
        await graph.create_relationship(
            build_relationship("rel-1", "host-1", "ip-1")
        )

        retriever = CompositeRetriever(
            FixedEmbedding(),
            ScriptedVectorStore(),
            make_memory_service(),
            investigations,
            graph,
        )

        knowledge = await retriever.retrieve(
            _state(), _plan(RetrievalStrategy.GRAPH)
        )

        references = [item.reference for item in knowledge.items]
        assert "ip-1" in references  # the neighbour entity
        assert "rel-1" in references  # the incident relationship
        assert all(
            item.strategy is RetrievalStrategy.GRAPH
            and item.source == "graph"
            for item in knowledge.items
        )

    asyncio.run(scenario())


def test_graph_skips_dangling_entity_references() -> None:
    async def scenario() -> None:
        investigations = make_investigation_service()
        await investigations.create(build_investigation("inv-1"))
        await investigations.attach_evidence(build_evidence("ev-1", "inv-1"))
        # The finding references an entity absent from the graph (§8a:
        # dangling cross-store references stay observable, never fatal).
        await investigations.create_finding(
            build_finding(
                "f-1",
                "inv-1",
                supporting_evidence=("ev-1",),
                related_entities=("ghost-1",),
            )
        )

        retriever = CompositeRetriever(
            FixedEmbedding(),
            ScriptedVectorStore(),
            make_memory_service(),
            investigations,
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state(), _plan(RetrievalStrategy.GRAPH)
        )

        assert knowledge.items == ()

    asyncio.run(scenario())


def test_hybrid_executes_the_organizational_strategies_together() -> None:
    async def scenario() -> None:
        memory = make_memory_service()
        await memory.create(
            build_memory_item(
                "m-1", source_investigation_id="inv-1", content="ours"
            )
        )
        embedding = FixedEmbedding()
        retriever = CompositeRetriever(
            embedding,
            ScriptedVectorStore((_match("m-1", 0.9),)),
            memory,
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state("inv-1"), _plan(RetrievalStrategy.HYBRID)
        )

        # semantic executed (query embedded) and structured contributed; the
        # same item may appear under both strategies — the Context Builder
        # owns (source, reference) deduplication downstream.
        assert embedding.queries == ["Investigate: lateral movement"]
        strategies = {item.strategy for item in knowledge.items}
        assert RetrievalStrategy.SEMANTIC in strategies
        assert RetrievalStrategy.STRUCTURED in strategies

    asyncio.run(scenario())


def test_external_strategy_contributes_nothing() -> None:
    async def scenario() -> None:
        retriever = CompositeRetriever(
            FixedEmbedding(),
            ScriptedVectorStore(),
            make_memory_service(),
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state(), _plan(RetrievalStrategy.EXTERNAL)
        )

        assert knowledge.items == ()

    asyncio.run(scenario())


def test_strategy_failure_is_contained_per_strategy() -> None:
    async def scenario() -> None:
        memory = make_memory_service()
        await memory.create(
            build_memory_item(
                "m-1", source_investigation_id="inv-1", content="ours"
            )
        )
        retriever = CompositeRetriever(
            FixedEmbedding(),
            UnavailableVectorStore(),
            memory,
            make_investigation_service(),
            make_graph_service(),
        )

        knowledge = await retriever.retrieve(
            _state("inv-1"),
            _plan(RetrievalStrategy.SEMANTIC, RetrievalStrategy.STRUCTURED),
        )

        # The unreachable vector store silences semantic only; structured
        # still contributes (contained per-strategy failure).
        assert [item.strategy for item in knowledge.items] == [
            RetrievalStrategy.STRUCTURED
        ]

    asyncio.run(scenario())
