"""External knowledge provider port.

Defines the provider-neutral interface for external cybersecurity knowledge
sources (threat intelligence feeds, CVE databases, MITRE ATT&CK and similar),
mirroring the provider discipline of the LLM and embedding ports (ADR-005).
This is the executable counterpart of the documented EXTERNAL retrieval
strategy (rag-architecture §15) and the External Knowledge memory layer
(memory-architecture §4): the RAG Retriever's external strategy runs through
this port.

Results carry their origin (`source`, `reference`) so external knowledge stays
distinguishable from organizational knowledge (rag-architecture §17). Per
ADR-013, implementations must enforce a bounded execution time and surface
exhaustion or provider failure as :class:`~app.ai.errors.ExternalKnowledgeError`.

This contract must remain entirely provider-neutral: no vendor-specific
concepts, parameters or types. Concrete providers are deferred integration work.
"""

from dataclasses import dataclass
from typing import Protocol

from app.domain.value_objects import Confidence


@dataclass(frozen=True, slots=True)
class ExternalKnowledgeQuery:
    """A provider-neutral external-knowledge query (intentionally minimal)."""

    query: str


@dataclass(frozen=True, slots=True)
class ExternalKnowledgeItem:
    """One external knowledge item with its origin preserved."""

    source: str
    reference: str
    content: str
    confidence: Confidence


class ExternalKnowledgeProvider(Protocol):
    """Replaceable external knowledge source interface."""

    async def lookup(
        self, query: ExternalKnowledgeQuery
    ) -> tuple[ExternalKnowledgeItem, ...]: ...
