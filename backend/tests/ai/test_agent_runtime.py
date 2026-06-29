"""Unit tests for the Agent Runtime (ES-010).

Plain pytest functions; tiny in-test fake agents prove the contract. No live AI
calls.
"""

import asyncio
import dataclasses

import pytest

from app.ai import (
    Agent,
    AgentIdentity,
    AgentRequest,
    AgentResult,
    AgentRuntime,
    AgentStatus,
)
from app.ai.errors import AgentError
from app.shared.exceptions import SentinelAIError


class _FakeDomainError(SentinelAIError):
    code = "fake.error"


def _request(payload: str = "do-something") -> AgentRequest:
    return AgentRequest(payload=payload, investigation_id="inv-1")


class _CompletingAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("completing-agent")

    async def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            agent=self.identity,
            status=AgentStatus.COMPLETED,
            output=f"handled:{request.payload}",
        )


class _SelfFailingAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("self-failing-agent")

    async def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            agent=self.identity, status=AgentStatus.FAILED, error="declined"
        )


class _RaisingDomainAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("raising-domain-agent")

    async def execute(self, request: AgentRequest) -> AgentResult:
        raise _FakeDomainError("nope")


class _RaisingUnexpectedAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("raising-unexpected-agent")

    async def execute(self, request: AgentRequest) -> AgentResult:
        raise RuntimeError("boom")


def test_completed_run() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(_CompletingAgent(), _request())
        assert result.status is AgentStatus.COMPLETED
        assert result.output == "handled:do-something"
        assert result.agent == AgentIdentity("completing-agent")

    asyncio.run(scenario())


def test_agent_returned_failure_is_passed_through() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(_SelfFailingAgent(), _request())
        assert result.status is AgentStatus.FAILED
        assert result.error == "declined"

    asyncio.run(scenario())


def test_sentinel_error_is_contained_with_stable_code() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(_RaisingDomainAgent(), _request())
        assert result.status is AgentStatus.FAILED
        assert result.error == "fake.error"

    asyncio.run(scenario())


def test_unexpected_exception_is_contained() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(_RaisingUnexpectedAgent(), _request())
        assert result.status is AgentStatus.FAILED
        assert result.error == "unexpected_runtime_failure"

    asyncio.run(scenario())


def test_blank_payload_is_contained_as_failed_result() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(_CompletingAgent(), _request(payload="  "))
        assert result.status is AgentStatus.FAILED
        assert result.error == "ai.agent_error"

    asyncio.run(scenario())


def test_blank_identity_raises() -> None:
    with pytest.raises(AgentError):
        AgentIdentity("")


def test_request_and_result_are_frozen() -> None:
    request = _request()
    result = AgentResult(agent=AgentIdentity("x"), status=AgentStatus.COMPLETED)
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.payload = "y"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.output = "z"  # type: ignore[misc]


def test_agent_is_protocol() -> None:
    assert getattr(Agent, "_is_protocol", False) is True
