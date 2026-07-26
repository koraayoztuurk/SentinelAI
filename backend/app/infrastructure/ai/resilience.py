"""Provider-edge resilience: circuit breaker + bounded retry (ES-067).

Realizes ADR-013 §4 — "a circuit-breaker (fail-fast on an unhealthy provider) is
the designated pattern for concrete provider adapters, applied at the
infrastructure/provider edge when real providers are integrated. It is not
implemented in the provider-neutral ports." Every concrete AI adapter
(Gemini/NVIDIA LLM, Gemini embedding, NVD) is an ``httpx`` client over one
endpoint, so the resilience layer is expressed once here, in HTTP terms, and the
adapters keep sole ownership of their port error wording.

What this module adds around a provider call:

- **Per-attempt time bound** (ADR-013 §1) — each attempt runs under
  ``asyncio.timeout``; the *existence* of the bound is the contract, the value
  is configuration. Retries multiply wall-clock time by the attempt count, which
  is why the default attempt count is deliberately small (one retry).
- **Bounded retry with exponential backoff + jitter**, for **transient failures
  only** — timeouts, transport failures and the provider's own
  capacity/rate-limit signals (429, 5xx). ADR-013 §3 names exactly these
  "retry-worthy transient failures"; a 4xx (bad request, bad key, blocked
  prompt) is our failure, never retried.
- **A process-wide circuit breaker per provider** — consecutive transient
  failures open it, and while open every call fails fast without touching the
  network until a probe is due. Adapters are constructed per request
  (``dependencies/services.py``), so breaker state cannot live on the adapter
  instance: it lives in a process-scoped registry keyed by provider name.

Health accounting is deliberate: the breaker counts **transient** failures only.
A 4xx means the provider answered — it is healthy, and our request was wrong.
Success and non-transient answers both close the breaker.

Failure never becomes silence: an exhausted retry budget or an open circuit is
raised as :class:`ProviderCallError`, which the calling adapter maps to its own
port error (``LLMProviderError`` / ``EmbeddingProviderError`` /
``ExternalKnowledgeError``). The loop's degrade-to-escalation behavior
(ADR-013 §3) is therefore unchanged — it simply engages later and less often.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Literal

import httpx

from app.config.ai import AIResilienceSettings
from app.observability.metrics import metrics

logger = logging.getLogger(__name__)

# Provider responses that mean "try again later", not "your request is wrong":
# 429 is the documented free-tier rate-limit signal and 5xx the capacity/outage
# class (the observed Gemini 503 windows).
_RETRYABLE_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})

FailureKind = Literal["timeout", "transport", "unavailable", "circuit_open"]


class ProviderCallError(Exception):
    """A provider call failed after exhausting its resilience budget.

    Infrastructure-internal: each adapter catches this and re-raises its own
    port error, so provider error wording stays owned by the adapter.
    """

    def __init__(self, kind: FailureKind, detail: str, attempts: int) -> None:
        self.kind: FailureKind = kind
        self.detail = detail
        self.attempts = attempts
        super().__init__(detail)


class BreakerState(Enum):
    """Circuit-breaker states (ADR-013 §4)."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Fail-fast gate over one provider's recent transient-failure history.

    Closed until ``failure_threshold`` consecutive transient failures open it.
    While open, calls are refused without touching the network. After
    ``reset_seconds`` one probe is admitted (half-open): its success closes the
    breaker, its failure re-opens the window.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int,
        reset_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._name = name
        self._threshold = max(1, failure_threshold)
        self._reset_seconds = reset_seconds
        self._clock = clock
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> BreakerState:
        """The breaker's state as of now (a due probe reads as half-open)."""

        if self._opened_at is None:
            return BreakerState.CLOSED
        if self._clock() - self._opened_at >= self._reset_seconds:
            return BreakerState.HALF_OPEN
        return BreakerState.OPEN

    def allow(self) -> bool:
        """Whether a call may proceed (a half-open probe is admitted)."""

        return self.state is not BreakerState.OPEN

    def record_success(self) -> None:
        """A provider answer (success or 4xx) — the provider is reachable."""

        if self._opened_at is not None:
            logger.info("provider circuit closed provider=%s", self._name)
        self._consecutive_failures = 0
        self._opened_at = None
        metrics.record_circuit_state(self._name, BreakerState.CLOSED.value)

    def record_failure(self) -> None:
        """A transient failure — capacity, timeout or transport."""

        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            if self._opened_at is None:
                logger.warning(
                    "provider circuit opened provider=%s failures=%s",
                    self._name,
                    self._consecutive_failures,
                )
            # Re-opening on a failed half-open probe restarts the window.
            self._opened_at = self._clock()
        metrics.record_circuit_state(self._name, self.state.value)


# Process-scoped breaker registry: adapters are per-request objects, so the
# health signal has to outlive them (see module docstring).
_BREAKERS: dict[str, CircuitBreaker] = {}


def breaker_for(name: str, settings: AIResilienceSettings) -> CircuitBreaker:
    """Return the process-wide breaker for a provider, creating it once."""

    breaker = _BREAKERS.get(name)
    if breaker is None:
        breaker = CircuitBreaker(
            name,
            settings.breaker_failure_threshold,
            settings.breaker_reset_seconds,
        )
        _BREAKERS[name] = breaker
    return breaker


def breaker_states() -> dict[str, str]:
    """Snapshot of every known provider breaker (operational visibility)."""

    return {name: breaker.state.value for name, breaker in _BREAKERS.items()}


def reset_breakers() -> None:
    """Clear the registry (test isolation only — never a runtime path)."""

    _BREAKERS.clear()


def _backoff_delay(
    attempt: int, settings: AIResilienceSettings, jitter: Callable[[], float]
) -> float:
    """Exponential backoff for ``attempt`` (1-based), with jitter applied.

    Jitter spreads retries so concurrent callers do not re-hit a recovering
    provider in lockstep.
    """

    exponential = settings.backoff_base_seconds * 2.0 ** (attempt - 1)
    return min(exponential, settings.backoff_max_seconds) * jitter()


def _default_jitter() -> float:
    # Half-to-full jitter: never longer than the computed backoff, never zero.
    return random.uniform(0.5, 1.0)  # noqa: S311 - scheduling, not cryptography


@dataclass(frozen=True, slots=True)
class ResilientHttpCaller:
    """Runs one provider's HTTP call under breaker + retry + per-attempt bound.

    ``timeout_seconds`` is the provider adapter's own configured execution bound
    (ADR-013 §1) and applies **per attempt**. ``sleep`` and ``jitter`` are
    injectable so the retry schedule is deterministic under test.
    """

    provider: str
    timeout_seconds: float
    settings: AIResilienceSettings
    breaker: CircuitBreaker
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    jitter: Callable[[], float] = _default_jitter

    async def run(
        self, operation: Callable[[], Awaitable[httpx.Response]]
    ) -> httpx.Response:
        """Execute ``operation`` resiliently and return the provider response.

        A retryable *response* (429/5xx) is retried while budget remains and
        otherwise returned as-is, so the adapter can quote the provider's own
        error detail. Timeouts and transport failures raise
        :class:`ProviderCallError` once the budget is exhausted.
        """

        if not self.breaker.allow():
            raise ProviderCallError(
                "circuit_open",
                (
                    f"{self.provider} circuit is open after repeated failures; "
                    "the call was not attempted."
                ),
                0,
            )

        attempts = max(1, self.settings.max_attempts)
        last_error: ProviderCallError | None = None
        for attempt in range(1, attempts + 1):
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    response = await operation()
            except TimeoutError:
                last_error = ProviderCallError(
                    "timeout",
                    (
                        f"{self.provider} call exceeded the "
                        f"{self.timeout_seconds}s execution bound."
                    ),
                    attempt,
                )
                self.breaker.record_failure()
            except httpx.HTTPError as exc:
                last_error = ProviderCallError(
                    "transport",
                    f"{self.provider} transport failure: {type(exc).__name__}.",
                    attempt,
                )
                self.breaker.record_failure()
            else:
                if response.status_code not in _RETRYABLE_STATUSES:
                    # The provider answered — healthy, even on a 4xx (which is
                    # our request's fault and must never be retried).
                    self.breaker.record_success()
                    return response
                self.breaker.record_failure()
                if attempt == attempts:
                    # Budget exhausted: hand the response back so the adapter
                    # reports the provider's own status and detail.
                    return response
                last_error = None
                await self._pause(attempt, f"HTTP {response.status_code}")
                continue

            if attempt == attempts:
                break
            await self._pause(attempt, last_error.kind)

        assert last_error is not None  # noqa: S101 - loop invariant
        raise last_error

    async def _pause(self, attempt: int, reason: str) -> None:
        delay = _backoff_delay(attempt, self.settings, self.jitter)
        logger.warning(
            "provider call retrying provider=%s attempt=%s reason=%s delay=%.2fs",
            self.provider,
            attempt,
            reason,
            delay,
        )
        await self.sleep(delay)
