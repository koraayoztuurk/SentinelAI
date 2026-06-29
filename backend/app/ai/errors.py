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
