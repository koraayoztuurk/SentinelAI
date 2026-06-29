"""RAG retrieval port and retrieved-knowledge structures.

The Retriever executes a Memory Agent ``RetrievalPlan`` (ES-012) against the
knowledge sources selected by its strategies and returns the retrieved knowledge
(rag-architecture §5/§6/§18). It is defined here as a provider-neutral **port**
(Protocol): the concrete source-backed retrievers (semantic via a vector store,
structured via the Memory Service, graph via the Graph Service, external
intelligence) are introduced by later specifications and tested through in-memory
doubles.

``RetrievedItem`` preserves retrieval provenance (memory-architecture §17): the
strategy that produced it, an open source label, the source reference, the
content, and a confidence estimate. These are AI-layer operational structures
(not domain objects); they reuse the domain ``Confidence`` value object.
"""

from dataclasses import dataclass
from typing import Protocol

from app.ai.agents.memory.plan import RetrievalPlan, RetrievalPlanId, RetrievalStrategy
from app.ai.agents.planner.state import InvestigationState
from app.domain.value_objects import Confidence


@dataclass(frozen=True, slots=True)
class RetrievedItem:
    """One retrieved knowledge item with retrieval provenance."""

    strategy: RetrievalStrategy
    source: str
    reference: str
    content: str
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class RetrievedKnowledge:
    """The knowledge retrieved for a single Retrieval Plan."""

    plan_id: RetrievalPlanId
    items: tuple[RetrievedItem, ...]


class Retriever(Protocol):
    """Executes a Retrieval Plan against knowledge sources (replaceable port)."""

    async def retrieve(
        self, state: InvestigationState, plan: RetrievalPlan
    ) -> RetrievedKnowledge: ...
