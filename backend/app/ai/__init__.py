"""AI Runtime layer.

Hosts SentinelAI's AI execution (ADR-005). This task (ES-009) establishes the
**foundation** only: the provider-neutral, replaceable provider ports
(language-model and embedding) and the AI error hierarchy.

The foundation owns **only** provider abstractions. Prompt engineering, reasoning
strategies, orchestration and agent behaviour belong to higher AI layers
(Agent Runtime, Planner Agent, Memory Manager, RAG) introduced by later
specifications.

The AI Runtime is an independent layer: it never accesses persistence directly
and reaches business data only through backend services.
"""

from app.ai.errors import AIRuntimeError, EmbeddingProviderError, LLMProviderError
from app.ai.providers import (
    EmbeddingProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)

__all__ = [
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "EmbeddingProvider",
    "AIRuntimeError",
    "LLMProviderError",
    "EmbeddingProviderError",
]
