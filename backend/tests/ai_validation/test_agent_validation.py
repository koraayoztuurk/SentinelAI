"""Agent Validation (ES-035, ai-validation §5).

Verifies agent-level behavioral properties: stable identity, statelessness
(interleaved executions never influence each other) and the runtime's failure
containment as a behavioral guarantee over failure classes — the properties the
Agent Architecture establishes for *every* agent, independent of what a concrete
agent decides.
"""

import asyncio

import pytest

from app.ai import (
    AgentIdentity,
    AgentRequest,
    AgentResult,
    AgentRuntime,
    AgentStatus,
    MemoryAgent,
    PlannerAgent,
)
from app.shared.exceptions import SentinelAIError
from tests.ai_validation.support import ScriptedLLM, make_state

pytestmark = pytest.mark.ai


def test_agents_expose_stable_identities() -> None:
    """Identity is constant across instances (verification traceability)."""

    assert PlannerAgent(ScriptedLLM("{}")).identity == AgentIdentity(
        "planner-agent"
    )
    assert MemoryAgent(ScriptedLLM("{}")).identity == AgentIdentity("memory-agent")
    # Two fresh instances agree — identity is behavioral, not per-instance.
    assert (
        PlannerAgent(ScriptedLLM("{}")).identity
        == PlannerAgent(ScriptedLLM("{}")).identity
    )


def test_planner_agent_is_stateless_across_interleaved_calls() -> None:
    """Earlier executions never influence later ones (agent statelessness)."""

    async def scenario() -> None:
        agent = PlannerAgent(ScriptedLLM('{"action": "get_investigation"}'))
        first = await agent.decide(make_state("inv-1"), "a-1")
        await agent.decide(make_state("inv-other"), "a-2")
        third = await agent.decide(make_state("inv-1"), "a-1")
        assert first == third

    asyncio.run(scenario())


class _FailingAgent:
    """Agent double whose execution raises a configurable failure."""

    def __init__(self, failure: BaseException) -> None:
        self._failure = failure

    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("failing-agent")

    async def execute(self, request: AgentRequest) -> AgentResult:
        raise self._failure


class _DomainFailure(SentinelAIError):
    code = "test.domain_failure"


def test_runtime_contains_every_failure_class() -> None:
    """No agent failure ever escapes the runtime (behavioral containment)."""

    async def scenario() -> None:
        runtime = AgentRuntime()
        request = AgentRequest(payload="analyse", investigation_id="inv-1")

        contained = await runtime.run(_FailingAgent(_DomainFailure("boom")), request)
        assert contained.status is AgentStatus.FAILED
        assert contained.error == "test.domain_failure"

        unexpected = await runtime.run(
            _FailingAgent(RuntimeError("unplanned")), request
        )
        assert unexpected.status is AgentStatus.FAILED
        assert unexpected.error == "unexpected_runtime_failure"

    asyncio.run(scenario())
