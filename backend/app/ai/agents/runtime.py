"""Agent Runtime.

The stateless execution host and the **single agent execution path** (ADR-013):
every agent runs through :meth:`AgentRuntime.run`, which fully contains failures
— it **never propagates exceptions** to its caller. Domain failures surface as a
``FAILED`` result carrying the error's stable code; unexpected failures surface
as ``unexpected_runtime_failure``. Logging is operational observability, not an
audit record.
"""

import logging
from typing import TypeVar

from app.ai.agents.base import Agent, AgentResult, AgentStatus
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)

_UNEXPECTED_FAILURE = "unexpected_runtime_failure"

RequestT = TypeVar("RequestT")
ProductT = TypeVar("ProductT")


class AgentRuntime:
    """Executes an agent, containing every failure as a result (stateless)."""

    async def run(
        self, agent: Agent[RequestT, ProductT], request: RequestT
    ) -> AgentResult[ProductT]:
        """Run an agent and return a typed result; no exception ever escapes."""

        try:
            product = await agent.execute(request)
        except SentinelAIError as exc:
            logger.info(
                "agent run failed agent=%s code=%s",
                agent.identity.value,
                exc.code,
            )
            return AgentResult(
                agent=agent.identity,
                status=AgentStatus.FAILED,
                error=exc.code,
            )
        except Exception:
            logger.exception("agent run errored agent=%s", agent.identity.value)
            return AgentResult(
                agent=agent.identity,
                status=AgentStatus.FAILED,
                error=_UNEXPECTED_FAILURE,
            )

        logger.info(
            "agent run completed agent=%s status=%s",
            agent.identity.value,
            AgentStatus.COMPLETED.value,
        )
        return AgentResult(
            agent=agent.identity,
            status=AgentStatus.COMPLETED,
            product=product,
        )
