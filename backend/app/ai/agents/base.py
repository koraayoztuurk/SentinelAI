"""Agent contract.

Defines the single, typed, agent-neutral contract every AI agent satisfies and
the result envelope the Agent Runtime produces (ADR-013). Agents are stateless
(agent-architecture §10): each execution receives its typed request and returns
its typed product, or raises on failure.

The envelope belongs to the runtime, not to agents: an agent never builds a
failure envelope itself — it raises a :class:`~app.shared.exceptions.SentinelAIError`
(or fails unexpectedly), and the Agent Runtime contains the failure as a
``FAILED`` result with a stable error code. This realizes agent-architecture §15:
a concrete agent's typed product is *represented through* the neutral envelope
without coupling the envelope to any product type.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.ai.errors import AgentError


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    """A stable agent identifier (for example ``"planner-agent"``)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise AgentError("AgentIdentity must not be blank.")


class AgentStatus(Enum):
    """Outcome of a single agent execution."""

    COMPLETED = "completed"
    FAILED = "failed"


class Agent[RequestT, ProductT](Protocol):
    """The stateless, typed contract every AI agent satisfies.

    ``execute`` returns the agent's typed product or raises; it never returns a
    failure envelope. Containment is the Agent Runtime's responsibility.
    """

    @property
    def identity(self) -> AgentIdentity: ...

    async def execute(self, request: RequestT) -> ProductT: ...


@dataclass(frozen=True, slots=True)
class AgentResult[ProductT]:
    """The runtime's envelope around one agent execution.

    ``agent`` records provenance; ``product`` carries the agent's typed product
    when ``status`` is ``COMPLETED``; ``error`` carries a stable failure code
    when ``status`` is ``FAILED``.
    """

    agent: AgentIdentity
    status: AgentStatus
    product: ProductT | None = None
    error: str | None = None
