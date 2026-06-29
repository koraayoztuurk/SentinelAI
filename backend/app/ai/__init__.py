"""AI Runtime layer.

Hosts SentinelAI's AI execution (ADR-005). The foundation provides the
provider-neutral, replaceable provider ports (ES-009) and the Agent Runtime —
the agent contract and its stateless execution host (ES-010).

The foundation owns **only** provider abstractions and the agent execution host.
Prompt engineering, reasoning strategies, concrete agents, the Decision Engine,
tools and RAG belong to higher AI layers introduced by later specifications.

The AI Runtime is an independent layer: it never accesses persistence directly
and reaches business data only through backend services.
"""

from app.ai.agents import (
    Agent,
    AgentIdentity,
    AgentRequest,
    AgentResult,
    AgentRuntime,
    AgentStatus,
)
from app.ai.agents.memory import (
    MemoryAgent,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalStrategy,
)
from app.ai.agents.planner import InvestigationState, PlannerAgent
from app.ai.errors import (
    AgentError,
    AIRuntimeError,
    EmbeddingProviderError,
    InsufficientContextError,
    LLMProviderError,
    MemoryAgentError,
    PlannerAgentError,
    RagError,
)
from app.ai.providers import (
    EmbeddingProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)
from app.ai.rag import (
    ContextBuilder,
    ContextValidationResult,
    ContextValidator,
    InvestigationContext,
    Prompt,
    PromptBuilder,
    RagPipeline,
    RagResult,
    RetrievedItem,
    RetrievedKnowledge,
    Retriever,
    ValidationIssue,
    ValidationIssueCode,
)

__all__ = [
    # Provider ports (ES-009)
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "EmbeddingProvider",
    # Agent Runtime (ES-010)
    "Agent",
    "AgentIdentity",
    "AgentRequest",
    "AgentResult",
    "AgentStatus",
    "AgentRuntime",
    # Planner Agent (ES-011)
    "PlannerAgent",
    "InvestigationState",
    # Memory Agent (ES-012)
    "MemoryAgent",
    "RetrievalPlan",
    "RetrievalPlanId",
    "RetrievalStrategy",
    # RAG Pipeline (ES-013)
    "Retriever",
    "RetrievedItem",
    "RetrievedKnowledge",
    "ContextBuilder",
    "InvestigationContext",
    "ContextValidator",
    "ContextValidationResult",
    "ValidationIssue",
    "ValidationIssueCode",
    "PromptBuilder",
    "Prompt",
    "RagPipeline",
    "RagResult",
    # Errors
    "AIRuntimeError",
    "LLMProviderError",
    "EmbeddingProviderError",
    "AgentError",
    "PlannerAgentError",
    "MemoryAgentError",
    "RagError",
    "InsufficientContextError",
]
