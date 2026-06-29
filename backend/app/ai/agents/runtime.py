"""Agent Runtime.

The stateless execution host that runs an agent and fully contains failures: it
**never propagates exceptions** to its caller. Every outcome is an
:class:`~app.ai.agents.base.AgentResult`. Logging is operational observability,
not an audit record.
"""

import logging

from app.ai.agents.base import Agent, AgentRequest, AgentResult, AgentStatus
from app.ai.errors import AgentError
from app.shared.exceptions import SentinelAIError

logger = logging.getLogger(__name__)

_UNEXPECTED_FAILURE = "unexpected_runtime_failure"


class AgentRuntime:
    """Executes an agent, containing every failure as a result (stateless)."""

    async def run(self, agent: Agent, request: AgentRequest) -> AgentResult:
        """Run an agent and return a result; no exception ever escapes."""

        try:
            self._validate(request)
            result = await agent.execute(request)
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
            result.status.value,
        )
        return result

    @staticmethod
    def _validate(request: AgentRequest) -> None:
        if not request.payload.strip():
            raise AgentError("AgentRequest payload must not be blank.")
