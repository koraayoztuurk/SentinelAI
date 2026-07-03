"""AI Runtime layer.

Hosts SentinelAI's AI execution (ADR-005). The foundation provides the
provider-neutral, replaceable provider ports (ES-009) and the Agent Runtime —
the typed agent contract and its single, failure-containing execution host
(ES-010, ADR-013).

The foundation owns provider abstractions and the agent execution host; the
higher layers add the concrete agents (ES-011/012), the RAG pipeline (ES-013)
and the AI orchestration compositions (ES-037, ADR-010). Prompt engineering,
reasoning strategies, the Decision Engine and tools are introduced by later
specifications.

The AI Runtime is an independent layer: it never accesses persistence directly
and reaches business data only through backend services.
"""

from app.ai.agents import (
    Agent,
    AgentIdentity,
    AgentResult,
    AgentRuntime,
    AgentStatus,
)
from app.ai.agents.memory import (
    MemoryAgent,
    RetrievalPlan,
    RetrievalPlanId,
    RetrievalPlanRequest,
    RetrievalStrategy,
)
from app.ai.agents.planner import (
    InvestigationState,
    PlannerAgent,
    PlannerDecisionRequest,
)
from app.ai.errors import (
    AgentError,
    AIRuntimeError,
    EmbeddingProviderError,
    ExternalKnowledgeError,
    InsufficientContextError,
    InvestigationLoopError,
    LLMProviderError,
    MemoryAgentError,
    PlannerAgentError,
    RagError,
)
from app.ai.orchestration import (
    ActionExecutor,
    ActionIdSource,
    Clock,
    IdSource,
    InvestigationLoop,
    LoopEnd,
    LoopOutcome,
    RetrievalFlow,
    StateAssembler,
    TraceSink,
)
from app.ai.providers import (
    EmbeddingProvider,
    ExternalKnowledgeItem,
    ExternalKnowledgeProvider,
    ExternalKnowledgeQuery,
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
    # Provider ports (ES-009, ADR-013)
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "EmbeddingProvider",
    "ExternalKnowledgeProvider",
    "ExternalKnowledgeQuery",
    "ExternalKnowledgeItem",
    # Agent Runtime (ES-010, ADR-013)
    "Agent",
    "AgentIdentity",
    "AgentResult",
    "AgentStatus",
    "AgentRuntime",
    # Planner Agent (ES-011)
    "PlannerAgent",
    "PlannerDecisionRequest",
    "InvestigationState",
    # Memory Agent (ES-012)
    "MemoryAgent",
    "RetrievalPlan",
    "RetrievalPlanId",
    "RetrievalPlanRequest",
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
    # AI orchestration (ES-037, ADR-010/013)
    "ActionExecutor",
    "ActionIdSource",
    "Clock",
    "IdSource",
    "InvestigationLoop",
    "LoopEnd",
    "LoopOutcome",
    "StateAssembler",
    "RetrievalFlow",
    "TraceSink",
    # Errors
    "AIRuntimeError",
    "LLMProviderError",
    "EmbeddingProviderError",
    "ExternalKnowledgeError",
    "AgentError",
    "PlannerAgentError",
    "MemoryAgentError",
    "RagError",
    "InsufficientContextError",
    "InvestigationLoopError",
]
