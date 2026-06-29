"""Agent contract.

Defines the minimal, agent-neutral contract every AI agent satisfies and the
typed request/result the Agent Runtime executes. Agents are stateless
(agent-architecture §10): each execution receives its inputs and keeps no state.

The contract is intentionally minimal and provider-neutral. Rich investigation
context/state and structured findings/confidence/evidence references are defined
by concrete agents, introduced by later specifications.
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


@dataclass(frozen=True, slots=True)
class AgentRequest:
    """An agent-neutral execution request (intentionally minimal).

    ``payload`` is a generic, framework-level input; the runtime makes no
    assumption about its meaning. ``investigation_id`` is an AI-neutral reference.
    """

    payload: str
    investigation_id: str


@dataclass(frozen=True, slots=True)
class AgentResult:
    """The structured outcome of an agent execution.

    ``agent`` records provenance; ``output`` carries the agent's structured
    output; ``error`` carries a stable failure code when ``status`` is ``FAILED``.
    """

    agent: AgentIdentity
    status: AgentStatus
    output: str = ""
    error: str | None = None


class Agent(Protocol):
    """The stateless contract every AI agent satisfies."""

    @property
    def identity(self) -> AgentIdentity: ...

    async def execute(self, request: AgentRequest) -> AgentResult: ...
