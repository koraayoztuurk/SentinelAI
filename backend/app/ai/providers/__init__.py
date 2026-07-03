"""AI Runtime provider ports.

Provider-neutral, replaceable interfaces for language-model, embedding and
external-knowledge providers. Implementations must honor the resilience
contract (ADR-013): bounded execution time, failures surfaced as the port's
error type. Concrete implementations are deferred integration work.
"""

from app.ai.providers.embedding import EmbeddingProvider
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeProvider,
    ExternalKnowledgeQuery,
)
from app.ai.providers.llm import LLMProvider, LLMRequest, LLMResponse

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "EmbeddingProvider",
    "ExternalKnowledgeProvider",
    "ExternalKnowledgeQuery",
    "ExternalKnowledgeItem",
]
