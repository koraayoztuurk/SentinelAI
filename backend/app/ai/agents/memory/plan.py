"""Memory Agent retrieval-plan contract.

The typed, deterministic product of the ``memory-agent``: a Retrieval Plan that
declares which documented retrieval strategies should participate in retrieval
for an investigation (memory-architecture §17, rag-architecture §14/§15). The
Memory Agent *selects* strategies; it never retrieves, coordinates sources or
assembles context — those are the RAG Pipeline's responsibility (ES-013).

These are AI-layer operational structures (not domain objects). ``RetrievalPlanId``
is an AI-layer typed identifier mirroring the domain identifier style; callers
supply its value (no generation here). ``RetrievalStrategy`` is a closed enum
because the documentation defines a fixed retrieval-strategy vocabulary.
"""

from dataclasses import dataclass
from enum import Enum

from app.ai.errors import MemoryAgentError
from app.domain.identifiers import InvestigationId


@dataclass(frozen=True, slots=True)
class RetrievalPlanId:
    """Caller-supplied identifier of a Retrieval Plan (AI-layer typed id)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise MemoryAgentError("RetrievalPlanId must not be blank.")


class RetrievalStrategy(Enum):
    """A documented retrieval strategy (memory-architecture §17, rag §15)."""

    SEMANTIC = "semantic"
    GRAPH = "graph"
    STRUCTURED = "structured"
    EXTERNAL = "external"
    HYBRID = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    """The Memory Agent's selection of retrieval strategies for an investigation.

    ``strategies`` lists the documented strategies that should participate in
    retrieval, in a deterministic canonical order. An empty ``strategies`` signals
    that no retrieval strategy could be determined (insufficient context); the RAG
    Pipeline (ES-013) consumes this plan.
    """

    plan_id: RetrievalPlanId
    investigation_id: InvestigationId
    strategies: tuple[RetrievalStrategy, ...]
