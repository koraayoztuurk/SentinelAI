"""Tests for the provider-edge resilience layer (ES-067, ADR-013 §4).

Deterministic: the retry schedule is driven by an injected ``sleep`` that
records delays instead of waiting, the jitter factor is pinned to 1.0, and the
breaker reads an injected clock. No network, no real time.

The properties under test are the ones ADR-013 fixes: transient failures are
retried within a bound, non-transient ones never are, an unhealthy provider
fails fast, and health stays observable rather than hidden by the breaker.
"""

import asyncio
from collections.abc import Awaitable, Callable

import httpx
import pytest

from app.config.ai import AIResilienceSettings
from app.infrastructure.ai.resilience import (
    BreakerState,
    CircuitBreaker,
    ProviderCallError,
    ResilientHttpCaller,
    breaker_for,
    breaker_states,
    reset_breakers,
)

_POLICY = AIResilienceSettings(
    max_attempts=3,
    backoff_base_seconds=1.0,
    backoff_max_seconds=4.0,
    breaker_failure_threshold=2,
    breaker_reset_seconds=30.0,
)


class _Clock:
    """A hand-wound monotonic clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Sleeps:
    """Records the retry schedule instead of waiting for it."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def _caller(
    breaker: CircuitBreaker,
    sleeps: _Sleeps,
    policy: AIResilienceSettings = _POLICY,
) -> ResilientHttpCaller:
    return ResilientHttpCaller(
        "test-provider",
        timeout_seconds=5.0,
        settings=policy,
        breaker=breaker,
        sleep=sleeps,
        jitter=lambda: 1.0,
    )


def _breaker(clock: _Clock | None = None) -> CircuitBreaker:
    return CircuitBreaker(
        "test-provider",
        failure_threshold=_POLICY.breaker_failure_threshold,
        reset_seconds=_POLICY.breaker_reset_seconds,
        clock=clock or _Clock(),
    )


def _responder(
    *statuses: int,
) -> tuple[Callable[[], Awaitable[httpx.Response]], list[int]]:
    """An operation returning the given statuses in order; records its calls."""

    calls: list[int] = []

    async def operation() -> httpx.Response:
        status = statuses[min(len(calls), len(statuses) - 1)]
        calls.append(status)
        return httpx.Response(status)

    return operation, calls


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    reset_breakers()


# ------------------------------------------------------------------- retrying


def test_transient_status_is_retried_then_succeeds() -> None:
    sleeps = _Sleeps()
    operation, calls = _responder(503, 200)

    response = asyncio.run(_caller(_breaker(), sleeps).run(operation))

    assert response.status_code == 200
    assert calls == [503, 200]
    assert sleeps.delays == [1.0]


def test_client_error_is_never_retried() -> None:
    # A 400/401 is our request's fault: retrying it wastes quota and cannot
    # succeed. It is also not a provider-health signal (ADR-013 §4).
    sleeps = _Sleeps()
    breaker = _breaker()
    operation, calls = _responder(401, 200)

    response = asyncio.run(_caller(breaker, sleeps).run(operation))

    assert response.status_code == 401
    assert calls == [401]
    assert sleeps.delays == []
    assert breaker.state is BreakerState.CLOSED


def test_exhausted_retries_return_the_providers_own_response() -> None:
    # The adapter owns the error wording, so the last response is handed back
    # rather than swallowed — the caller can still quote status and detail.
    sleeps = _Sleeps()
    operation, calls = _responder(503)

    response = asyncio.run(_caller(_breaker(), sleeps).run(operation))

    assert response.status_code == 503
    assert calls == [503, 503, 503]
    # Backoff doubles per attempt and pauses only between attempts.
    assert sleeps.delays == [1.0, 2.0]


def test_backoff_is_capped_by_the_policy_maximum() -> None:
    policy = AIResilienceSettings(
        max_attempts=5,
        backoff_base_seconds=1.0,
        backoff_max_seconds=2.0,
        breaker_failure_threshold=99,
        breaker_reset_seconds=30.0,
    )
    sleeps = _Sleeps()
    operation, _ = _responder(503)

    asyncio.run(_caller(_breaker(), sleeps, policy).run(operation))

    assert sleeps.delays == [1.0, 2.0, 2.0, 2.0]


def test_transport_failure_is_retried_and_finally_raised() -> None:
    sleeps = _Sleeps()

    async def operation() -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    with pytest.raises(ProviderCallError) as exc_info:
        asyncio.run(_caller(_breaker(), sleeps).run(operation))

    assert exc_info.value.kind == "transport"
    assert "ConnectError" in exc_info.value.detail
    assert sleeps.delays == [1.0, 2.0]


def test_timeout_is_bounded_per_attempt_and_reported() -> None:
    sleeps = _Sleeps()
    caller = ResilientHttpCaller(
        "test-provider",
        timeout_seconds=0.01,
        settings=_POLICY,
        breaker=_breaker(),
        sleep=sleeps,
        jitter=lambda: 1.0,
    )

    async def operation() -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200)

    with pytest.raises(ProviderCallError) as exc_info:
        asyncio.run(caller.run(operation))

    assert exc_info.value.kind == "timeout"
    assert "execution bound" in exc_info.value.detail
    # Every attempt got its own bound (ADR-013 §1), so all were spent.
    assert exc_info.value.attempts == _POLICY.max_attempts


def test_error_detail_never_carries_provider_credentials() -> None:
    # The detail is built from the provider name and the exception *type*,
    # never from request material — key hygiene survives the resilience layer.
    sleeps = _Sleeps()

    async def operation() -> httpx.Response:
        raise httpx.ConnectError("Bearer super-secret-key leaked in message")

    with pytest.raises(ProviderCallError) as exc_info:
        asyncio.run(_caller(_breaker(), sleeps).run(operation))

    assert "super-secret-key" not in exc_info.value.detail


# -------------------------------------------------------------- circuit breaker


def test_circuit_opens_after_consecutive_transient_failures() -> None:
    clock = _Clock()
    breaker = _breaker(clock)
    sleeps = _Sleeps()
    operation, _ = _responder(503)

    asyncio.run(_caller(breaker, sleeps).run(operation))

    assert breaker.state is BreakerState.OPEN


def test_open_circuit_fails_fast_without_calling_the_provider() -> None:
    clock = _Clock()
    breaker = _breaker(clock)
    sleeps = _Sleeps()
    asyncio.run(_caller(breaker, sleeps).run(_responder(503)[0]))
    assert breaker.state is BreakerState.OPEN

    operation, calls = _responder(200)
    with pytest.raises(ProviderCallError) as exc_info:
        asyncio.run(_caller(breaker, sleeps).run(operation))

    assert exc_info.value.kind == "circuit_open"
    # Fail-fast means exactly that: the provider was never touched.
    assert calls == []


def test_half_open_probe_is_admitted_after_the_reset_window() -> None:
    clock = _Clock()
    breaker = _breaker(clock)
    sleeps = _Sleeps()
    asyncio.run(_caller(breaker, sleeps).run(_responder(503)[0]))

    clock.now += _POLICY.breaker_reset_seconds
    assert breaker.state is BreakerState.HALF_OPEN

    operation, calls = _responder(200)
    response = asyncio.run(_caller(breaker, sleeps).run(operation))

    assert response.status_code == 200
    assert calls == [200]
    # A successful probe closes the circuit again.
    assert breaker.state is BreakerState.CLOSED


def test_failed_probe_reopens_the_window() -> None:
    clock = _Clock()
    breaker = _breaker(clock)
    sleeps = _Sleeps()
    asyncio.run(_caller(breaker, sleeps).run(_responder(503)[0]))
    clock.now += _POLICY.breaker_reset_seconds

    asyncio.run(_caller(breaker, sleeps).run(_responder(503)[0]))

    assert breaker.state is BreakerState.OPEN


def test_success_resets_the_failure_streak() -> None:
    # Only *consecutive* failures open the circuit — an intermittent blip on an
    # otherwise healthy provider must not trip it.
    breaker = _breaker()
    sleeps = _Sleeps()

    asyncio.run(_caller(breaker, sleeps).run(_responder(503, 200)[0]))

    assert breaker.state is BreakerState.CLOSED


def test_breaker_registry_is_shared_per_provider_name() -> None:
    # Adapters are rebuilt per request, so the health signal must outlive them.
    first = breaker_for("gemini", _POLICY)
    second = breaker_for("gemini", _POLICY)

    assert first is second
    assert breaker_for("nvidia", _POLICY) is not first


def test_breaker_states_snapshot_reports_every_known_provider() -> None:
    breaker_for("gemini", _POLICY)
    breaker_for("nvd", _POLICY)

    assert breaker_states() == {"gemini": "closed", "nvd": "closed"}
