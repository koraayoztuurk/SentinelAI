"""Context Builder.

Transforms retrieved knowledge into a structured, provenance-preserving
Investigation Context for downstream reasoning (rag-architecture §7/§8). Context
engineering — not retrieval — is the primary responsibility of the RAG pipeline:
the builder merges retrieved items with the investigation's objectives and
confidence, removes exact duplicates and produces a deterministic ordering.

The builder is a stateless, dependency-free component. Conflict detection and
resolution, context compression and prioritization (rag §9/§16) are introduced by
later specifications; here duplicates are collapsed only by exact
``(source, reference)`` identity.
"""

from dataclasses import dataclass

from app.ai.agents.memory.plan import RetrievalStrategy
from app.ai.agents.planner.state import InvestigationState
from app.ai.rag.retriever import RetrievedItem, RetrievedKnowledge
from app.domain.identifiers import InvestigationId
from app.domain.value_objects import Confidence

# Canonical strategy ordering for deterministic output (enum declaration order).
_STRATEGY_ORDER = {strategy: index for index, strategy in enumerate(RetrievalStrategy)}


@dataclass(frozen=True, slots=True)
class InvestigationContext:
    """A structured reasoning context assembled from retrieved knowledge."""

    investigation_id: InvestigationId
    objectives: tuple[str, ...]
    confidence: Confidence
    knowledge: tuple[RetrievedItem, ...]


class ContextBuilder:
    """Assembles an Investigation Context (stateless)."""

    def build(
        self, state: InvestigationState, retrieved: RetrievedKnowledge
    ) -> InvestigationContext:
        """Merge retrieved knowledge with the investigation into a context."""

        return InvestigationContext(
            investigation_id=state.investigation_id,
            objectives=state.objectives,
            confidence=state.confidence,
            knowledge=self._organize(retrieved.items),
        )

    @staticmethod
    def _organize(items: tuple[RetrievedItem, ...]) -> tuple[RetrievedItem, ...]:
        # Deterministic order: (strategy declaration order, source, reference).
        ordered = sorted(
            items,
            key=lambda item: (
                _STRATEGY_ORDER[item.strategy],
                item.source,
                item.reference,
            ),
        )
        # Deduplicate by (source, reference), preserving the first occurrence.
        seen: set[tuple[str, str]] = set()
        unique: list[RetrievedItem] = []
        for item in ordered:
            key = (item.source, item.reference)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return tuple(unique)
