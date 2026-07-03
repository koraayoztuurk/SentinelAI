"""Unit tests for the Agent Runtime (ES-010, ADR-013).

Plain pytest functions; tiny in-test fake agents with typed request/product
structures prove the single-execution-path contract. No live AI calls.
"""

import asyncio
import dataclasses

import pytest

from app.ai import (
    Agent,
    AgentIdentity,
    AgentResult,
    AgentRuntime,
    AgentStatus,
)
from app.ai.errors import AgentError
from app.shared.exceptions import SentinelAIError


class _FakeDomainError(SentinelAIError):
    code = "fake.error"


@dataclasses.dataclass(frozen=True, slots=True)
class _EchoRequest:
    payload: str


@dataclasses.dataclass(frozen=True, slots=True)
class _EchoProduct:
    handled: str


class _CompletingAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("completing-agent")

    async def execute(self, request: _EchoRequest) -> _EchoProduct:
        return _EchoProduct(handled=f"handled:{request.payload}")


class _RaisingDomainAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("raising-domain-agent")

    async def execute(self, request: _EchoRequest) -> _EchoProduct:
        raise _FakeDomainError("nope")


class _RaisingUnexpectedAgent:
    @property
    def identity(self) -> AgentIdentity:
        return AgentIdentity("raising-unexpected-agent")

    async def execute(self, request: _EchoRequest) -> _EchoProduct:
        raise RuntimeError("boom")


def test_completed_run_carries_typed_product() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(
            _CompletingAgent(), _EchoRequest(payload="do-something")
        )
        assert result.status is AgentStatus.COMPLETED
        assert result.product == _EchoProduct(handled="handled:do-something")
        assert result.agent == AgentIdentity("completing-agent")
        assert result.error is None

    asyncio.run(scenario())


def test_sentinel_error_is_contained_with_stable_code() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(
            _RaisingDomainAgent(), _EchoRequest(payload="x")
        )
        assert result.status is AgentStatus.FAILED
        assert result.error == "fake.error"
        assert result.product is None

    asyncio.run(scenario())


def test_unexpected_exception_is_contained() -> None:
    async def scenario() -> None:
        result = await AgentRuntime().run(
            _RaisingUnexpectedAgent(), _EchoRequest(payload="x")
        )
        assert result.status is AgentStatus.FAILED
        assert result.error == "unexpected_runtime_failure"

    asyncio.run(scenario())


def test_blank_identity_raises() -> None:
    with pytest.raises(AgentError):
        AgentIdentity("")


def test_result_is_frozen() -> None:
    result: AgentResult[_EchoProduct] = AgentResult(
        agent=AgentIdentity("x"), status=AgentStatus.COMPLETED
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.error = "z"  # type: ignore[misc]


def test_agent_is_protocol() -> None:
    assert getattr(Agent, "_is_protocol", False) is True
