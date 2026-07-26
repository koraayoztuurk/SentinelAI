"""Request-edge rate limiting (ES-068).

Realizes Traffic Validation (api-design §10) and the §13 Rate Limiting policy:
a configurable per-identity, per-operation request budget that protects the
backend services — the investigation run surface above all, whose cost is
bounded but large (ADR-013 §1).

Placement in the request lifecycle is the design decision. The limiter chains
:func:`require_identity`, so it runs **after** authentication and **before**
authorization: an anonymous caller is rejected as unauthenticated rather than
counted (a limiter that answered 429 before 401 would leak that a credential is
valid), and a limited identity is rejected before any authorization decision or
backend service invocation. The rejection ladder is therefore 401 → 429 → 403.

The counters live in this process. That is protection state, not request state:
no request's *result* depends on them, so Stateless Requests (§13) is preserved
and a deployment may run several instances — each simply enforces its own share
of the budget. Anonymous flood protection is deliberately *not* here; it belongs
to the deployment edge, which sees traffic this layer never reaches.
"""

import logging
import threading
from collections import deque
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from functools import lru_cache
from math import ceil
from time import monotonic

from fastapi import Depends, Request

from app.config.rate_limit import RateLimitSettings, get_rate_limit_settings
from app.observability import metrics
from app.presentation.api.auth import AuthenticatedIdentity, require_identity
from app.presentation.api.context import route_template
from app.presentation.api.errors import RateLimitedError

logger = logging.getLogger(__name__)

# The one operation with its own budget. Asserted against the live routing table
# by the test suite: renaming the route must fail loudly rather than silently
# demote the run surface to the default budget.
RUN_OPERATION_PATH = "/api/v1/investigations/{investigation_id}/run"


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """A request budget: ``requests`` permitted per ``window_seconds``."""

    requests: int
    window_seconds: float


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """The limiter's answer for one request."""

    allowed: bool
    retry_after_seconds: int = 0


@dataclass(slots=True)
class _Budget:
    """One key's retained requests, with the window they were counted under.

    The window travels with the entry because keys are governed by different
    policies: sweeping a run-surface key against the default policy's window
    would forget a budget that is still being spent.
    """

    hits: deque[float]
    window_seconds: float


class SlidingWindowRateLimiter:
    """Counts each key's requests over a moving window.

    A sliding window rather than a fixed one: a fixed window admits twice the
    budget across a window boundary, and its ``Retry-After`` can only be
    "when the window rolls over". Here the retained timestamps are exactly the
    requests still inside the window, so both the decision and the retry hint
    are exact — the oldest retained request is the moment budget frees up.

    Memory is bounded twice over: a key holds at most ``policy.requests``
    timestamps, and the key space is swept of inactive keys once it exceeds
    ``max_tracked_keys`` (a caller cycling identities cannot grow it without
    bound). The clock is injected so the tests are deterministic and never
    wait; a monotonic source is required — a wall clock stepping backwards
    would hand out free budget.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = monotonic,
        max_tracked_keys: int = 4096,
    ) -> None:
        self._clock = clock
        self._max_tracked_keys = max_tracked_keys
        self._budgets: dict[Hashable, _Budget] = {}
        self._lock = threading.Lock()

    def check(
        self, key: Hashable, policy: RateLimitPolicy
    ) -> RateLimitDecision:
        """Consume one request from ``key``'s budget and report the outcome.

        A denied request is *not* recorded, so a caller that keeps hammering a
        closed budget does not push its own recovery further away.
        """

        now = self._clock()
        cutoff = now - policy.window_seconds
        with self._lock:
            budget = self._budgets.get(key)
            if budget is None:
                # Sweep before inserting, never after: the key being created is
                # empty, so a sweep that saw it would drop the very budget it
                # was asked to start tracking.
                if len(self._budgets) >= self._max_tracked_keys:
                    self._sweep(now)
                budget = _Budget(deque(), policy.window_seconds)
                self._budgets[key] = budget
            budget.window_seconds = policy.window_seconds
            hits = budget.hits
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= policy.requests:
                # The oldest retained request leaves the window first.
                retry_after = max(
                    1, ceil(hits[0] + policy.window_seconds - now)
                )
                return RateLimitDecision(
                    allowed=False, retry_after_seconds=retry_after
                )
            hits.append(now)
            return RateLimitDecision(allowed=True)

    @property
    def tracked_keys(self) -> int:
        """How many keys currently hold budget state (the bounded footprint)."""

        with self._lock:
            return len(self._budgets)

    def _sweep(self, now: float) -> None:
        """Drop keys whose whole window has passed since their last request."""

        stale = [
            key
            for key, budget in self._budgets.items()
            if not budget.hits
            or budget.hits[-1] + budget.window_seconds <= now
        ]
        for key in stale:
            del self._budgets[key]


class RateLimitGuard:
    """Applies the configured policy to a request's identity and operation.

    Holds the settings and the limiter together so the whole decision — which
    policy applies, under which key, and whether limiting is on at all — is one
    testable object, independent of FastAPI.
    """

    def __init__(
        self,
        settings: RateLimitSettings,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._settings = settings
        self._limiter = SlidingWindowRateLimiter(
            clock=clock, max_tracked_keys=settings.max_tracked_keys
        )

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    def policy_for(self, operation: str) -> RateLimitPolicy:
        """Return the budget governing ``operation`` (a route path template)."""

        if operation == RUN_OPERATION_PATH:
            return RateLimitPolicy(
                requests=self._settings.run_requests,
                window_seconds=self._settings.run_window_seconds,
            )
        return RateLimitPolicy(
            requests=self._settings.requests,
            window_seconds=self._settings.window_seconds,
        )

    def check(
        self, identity: AuthenticatedIdentity, operation: str
    ) -> RateLimitDecision:
        """Decide whether ``identity`` may perform ``operation`` right now."""

        if not self.enabled:
            return RateLimitDecision(allowed=True)
        # The tenant is part of the key: identities are only unique within
        # their organization scope (ADR-016), so two tenants must never share
        # a budget — nor be able to exhaust each other's. A tuple rather than a
        # joined string, so no subject containing the separator can be made to
        # collide with another key.
        key = (identity.tenant, identity.subject, operation)
        return self._limiter.check(key, self.policy_for(operation))


@lru_cache
def get_rate_limit_guard() -> RateLimitGuard:
    """Return the process-wide guard (FastAPI dependency).

    Process-scoped for the same reason the ES-067 breaker registry is: the
    dependency graph is rebuilt per request, so a per-request guard would
    forget every count it ever made.
    """

    return RateLimitGuard(get_rate_limit_settings())


async def enforce_rate_limit(
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    guard: RateLimitGuard = Depends(get_rate_limit_guard),
) -> None:
    """Enforce the request budget (enforcement seam, mounted on ``/api/v1``).

    Keyed by the route template rather than the concrete URL, so the limiter's
    key space and the metric's label cardinality stay bounded by the number of
    API operations rather than by the number of investigations.
    """

    operation = route_template(request)
    decision = guard.check(identity, operation)
    if decision.allowed:
        return
    metrics.record_rate_limited(operation)
    logger.warning(
        "rate limited subject=%s operation=%s retry_after=%s",
        identity.subject,
        operation,
        decision.retry_after_seconds,
    )
    raise RateLimitedError(
        "Request limit exceeded; retry later.",
        retry_after_seconds=decision.retry_after_seconds,
    )
