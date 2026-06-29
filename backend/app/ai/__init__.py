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
from app.ai.agents.planner import InvestigationState, PlannerAgent
from app.ai.errors import (
    AgentError,
    AIRuntimeError,
    EmbeddingProviderError,
    LLMProviderError,
    PlannerAgentError,
)
from app.ai.providers import (
    EmbeddingProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
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
    # Errors
    "AIRuntimeError",
    "LLMProviderError",
    "EmbeddingProviderError",
    "AgentError",
    "PlannerAgentError",
]
