"""AI Runtime exceptions.

Service-level errors for the AI Runtime. Each derives from the shared
:class:`~app.shared.exceptions.SentinelAIError` and carries a stable
machine-readable ``code``. The surface is split per provider so failures remain
attributable; concrete providers (introduced by later specifications) raise these.
"""

from app.shared.exceptions import SentinelAIError


class AIRuntimeError(SentinelAIError):
    """Base class for AI Runtime errors."""

    code = "ai.error"


class LLMProviderError(AIRuntimeError):
    """Raised when a language-model provider operation fails."""

    code = "ai.llm_provider_error"


class EmbeddingProviderError(AIRuntimeError):
    """Raised when an embedding provider operation fails."""

    code = "ai.embedding_provider_error"


class ExternalKnowledgeError(AIRuntimeError):
    """Raised when an external knowledge provider operation fails or times out."""

    code = "ai.external_knowledge_error"


class AgentError(AIRuntimeError):
    """Raised for a runtime-level agent failure (e.g. an invalid request or a
    blank agent identity).

    The Agent Runtime contains this error and represents it as a failed result;
    it never escapes ``AgentRuntime.run``.
    """

    code = "ai.agent_error"


class PlannerAgentError(AIRuntimeError):
    """Raised when the Planner Agent cannot begin planning.

    Used for precondition violations (an Investigation State without objectives, a
    blank action identifier). Transformation failures are not raised — they
    resolve to an escalate action.
    """

    code = "ai.planner_agent_error"


class MemoryAgentError(AIRuntimeError):
    """Raised when the Memory Agent cannot begin retrieval planning.

    Used for precondition violations (a blank ``RetrievalPlanId``, an Investigation
    State without objectives). Transformation failures are not raised — unknown
    strategies are ignored and an empty Retrieval Plan is returned.
    """

    code = "ai.memory_agent_error"


class InvestigationLoopError(AIRuntimeError):
    """Raised when the Investigation Loop cannot begin running.

    Used for precondition violations (a non-positive cycle budget). Downstream
    execution failures are never raised by the loop — they are represented as
    failed execution results observed by the Planner Agent (ADR-010).
    """

    code = "ai.investigation_loop_error"


class ValidationAgentError(AIRuntimeError):
    """Raised when the Validation Agent cannot produce an assessment.

    Used for precondition violations (a context without findings) and for
    malformed assessment responses — an empty assessment is not a neutral
    fallback (it would read as a clean bill of health), so unlike the
    planner/memory agents there is no safe degrade product. The consuming
    composition contains this error.
    """

    code = "ai.validation_agent_error"


class GraphAnalysisError(AIRuntimeError):
    """Raised when the Graph Analysis Agent cannot produce an analysis.

    Used for precondition violations (a context without entities) and for
    malformed analysis responses — an empty analysis is not a neutral
    fallback (it would read as "nothing notable in the graph"). The
    consuming composition contains this error.
    """

    code = "ai.graph_analysis_error"


class DecisionEngineError(AIRuntimeError):
    """Raised when the Decision Engine cannot synthesize an outcome.

    Used for malformed synthesis responses (no safe fallback product exists —
    an invented recommendation would be worse than none) and precondition
    violations. The Investigation Loop contains this error: a failed synthesis
    never breaks a completed run.
    """

    code = "ai.decision_engine_error"


class RagError(AIRuntimeError):
    """Base class for RAG pipeline errors."""

    code = "ai.rag_error"


class InsufficientContextError(RagError):
    """Raised when the assembled investigation context fails validation.

    The RAG pipeline reports insufficient context explicitly rather than building a
    prompt over it (rag-architecture §9/§20).
    """

    code = "ai.rag_insufficient_context"
