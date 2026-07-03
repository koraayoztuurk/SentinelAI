"""Agent Runtime: the typed agent contract and its stateless execution host.

The Agent Runtime is the single agent execution path (ADR-013): agents expose
``execute(request) -> product`` and the runtime contains every failure as a
typed :class:`AgentResult`. Concrete agents implement the :class:`Agent`
contract with their own typed request/product structures.
"""

from app.ai.agents.base import (
    Agent,
    AgentIdentity,
    AgentResult,
    AgentStatus,
)
from app.ai.agents.runtime import AgentRuntime

__all__ = [
    "Agent",
    "AgentIdentity",
    "AgentResult",
    "AgentStatus",
    "AgentRuntime",
]
