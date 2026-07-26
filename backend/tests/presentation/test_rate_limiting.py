"""Tests for request-edge rate limiting (ES-068).

Two levels. The guard is exercised directly against a controlled clock — the
budget arithmetic, the sliding window, the per-identity/per-tenant/per-operation
key separation and the memory bound — so nothing here waits on wall-clock time.
The API level then proves the boundary contract: the 401 → 429 → 403 ladder, the
429 envelope with ``Retry-After``, and that the limiter is off by default.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.audit import AuditEvent
from app.config.rate_limit import RateLimitSettings
from app.main import create_app
from app.observability import metrics
from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    get_authenticator,
    require_identity,
)
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.rate_limit import (
    RUN_OPERATION_PATH,
    RateLimitDecision,
    RateLimitGuard,
    RateLimitPolicy,
    SlidingWindowRateLimiter,
    get_rate_limit_guard,
)

pytestmark = pytest.mark.operational

_IDENTITY = AuthenticatedIdentity(subject="analyst", kind=IdentityKind.HUMAN)
_OTHER_IDENTITY = AuthenticatedIdentity(
    subject="other-analyst", kind=IdentityKind.HUMAN
)
_READ_OPERATION = "/api/v1/investigations/{investigation_id}"


class _Clock:
    """A hand-advanced monotonic clock."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _guard(
    clock: _Clock,
    *,
    enabled: bool = True,
    requests: int = 3,
    run_requests: int = 1,
) -> RateLimitGuard:
    return RateLimitGuard(
        RateLimitSettings(
            enabled=enabled,
            requests=requests,
            window_seconds=60.0,
            run_requests=run_requests,
            run_window_seconds=60.0,
        ),
        clock=clock,
    )


# ------------------------------------------------------------------- limiter


def test_requests_within_budget_are_allowed() -> None:
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock)
    policy = RateLimitPolicy(requests=3, window_seconds=60.0)

    decisions = [limiter.check("k", policy) for _ in range(3)]

    assert all(decision.allowed for decision in decisions)


def test_request_beyond_budget_is_refused_with_a_retry_hint() -> None:
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock)
    policy = RateLimitPolicy(requests=2, window_seconds=60.0)
    limiter.check("k", policy)
    clock.advance(10.0)
    limiter.check("k", policy)

    clock.advance(5.0)
    decision = limiter.check("k", policy)

    assert not decision.allowed
    # The oldest of the two retained requests leaves the window 45s from now.
    assert decision.retry_after_seconds == 45


def test_budget_frees_up_as_the_window_slides() -> None:
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock)
    policy = RateLimitPolicy(requests=1, window_seconds=60.0)
    limiter.check("k", policy)

    assert not limiter.check("k", policy).allowed
    clock.advance(60.1)
    assert limiter.check("k", policy).allowed


def test_a_refused_request_does_not_extend_its_own_penalty() -> None:
    # A caller hammering a closed budget must not push its own recovery away:
    # a denied request is never recorded, so the retry hint keeps shrinking.
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock)
    policy = RateLimitPolicy(requests=1, window_seconds=60.0)
    limiter.check("k", policy)

    clock.advance(10.0)
    first = limiter.check("k", policy)
    clock.advance(10.0)
    second = limiter.check("k", policy)

    assert first.retry_after_seconds == 50
    assert second.retry_after_seconds == 40


def test_retry_after_is_never_zero() -> None:
    # A sub-second remainder must still tell the client to wait, not to retry
    # immediately (which would produce a second 429).
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock)
    policy = RateLimitPolicy(requests=1, window_seconds=60.0)
    limiter.check("k", policy)
    clock.advance(59.9)

    assert limiter.check("k", policy).retry_after_seconds == 1


def test_inactive_keys_are_swept_once_the_key_space_is_full() -> None:
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock, max_tracked_keys=2)
    policy = RateLimitPolicy(requests=5, window_seconds=60.0)
    limiter.check("a", policy)
    limiter.check("b", policy)

    clock.advance(120.0)  # both keys leave the window
    limiter.check("c", policy)

    assert limiter.tracked_keys == 1


def test_active_keys_survive_a_sweep() -> None:
    # The bound is a guard against unbounded growth, never a reason to forget
    # a budget that is still being spent.
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock, max_tracked_keys=1)
    policy = RateLimitPolicy(requests=1, window_seconds=60.0)
    limiter.check("a", policy)

    limiter.check("b", policy)  # over capacity, but "a" is still active

    assert limiter.tracked_keys == 2
    assert not limiter.check("a", policy).allowed


def test_a_key_is_swept_by_its_own_window_not_the_sweeper_s() -> None:
    # Keys are governed by different policies (the run surface has its own).
    # A sweep triggered by a short-window caller must not forget a long-window
    # budget that is still being spent — that would hand out free requests
    # exactly when the limiter is under memory pressure.
    clock = _Clock()
    limiter = SlidingWindowRateLimiter(clock=clock, max_tracked_keys=1)
    long_policy = RateLimitPolicy(requests=1, window_seconds=3600.0)
    short_policy = RateLimitPolicy(requests=1, window_seconds=60.0)
    limiter.check("long", long_policy)

    clock.advance(100.0)  # past the short window, deep inside the long one
    limiter.check("short", short_policy)  # triggers the sweep

    assert not limiter.check("long", long_policy).allowed


# --------------------------------------------------------------------- guard


def test_disabled_guard_allows_everything() -> None:
    guard = _guard(_Clock(), enabled=False, requests=1)

    decisions = [guard.check(_IDENTITY, _READ_OPERATION) for _ in range(5)]

    assert all(decision.allowed for decision in decisions)


def test_identities_do_not_share_a_budget() -> None:
    guard = _guard(_Clock(), requests=1)
    guard.check(_IDENTITY, _READ_OPERATION)

    assert not guard.check(_IDENTITY, _READ_OPERATION).allowed
    assert guard.check(_OTHER_IDENTITY, _READ_OPERATION).allowed


def test_tenants_do_not_share_a_budget() -> None:
    # Subjects are only unique within their tenant (ADR-016): the same subject
    # string in two tenants must be two budgets.
    guard = _guard(_Clock(), requests=1)
    other_tenant = AuthenticatedIdentity(
        subject=_IDENTITY.subject, kind=IdentityKind.HUMAN, tenant="acme"
    )
    guard.check(_IDENTITY, _READ_OPERATION)

    assert not guard.check(_IDENTITY, _READ_OPERATION).allowed
    assert guard.check(other_tenant, _READ_OPERATION).allowed


def test_operations_do_not_share_a_budget() -> None:
    guard = _guard(_Clock(), requests=1)
    guard.check(_IDENTITY, _READ_OPERATION)

    assert not guard.check(_IDENTITY, _READ_OPERATION).allowed
    assert guard.check(_IDENTITY, "/api/v1/memory").allowed


def test_the_run_surface_carries_its_own_stricter_budget() -> None:
    guard = _guard(_Clock(), requests=10, run_requests=1)

    assert guard.check(_IDENTITY, RUN_OPERATION_PATH).allowed
    assert not guard.check(_IDENTITY, RUN_OPERATION_PATH).allowed
    # The default budget is untouched by the run surface's exhaustion.
    assert guard.check(_IDENTITY, _READ_OPERATION).allowed


def test_the_run_operation_path_matches_a_real_route() -> None:
    # The stricter budget is selected by path template. If the route is ever
    # renamed, the run surface would silently fall back to the default budget
    # — so the constant is asserted against the published contract.
    assert RUN_OPERATION_PATH in create_app().openapi()["paths"]


def test_operation_is_the_full_route_template() -> None:
    # The limiter keys on the template, so two investigations share one budget
    # while two operations do not.
    seen: list[str] = []
    app = create_app()
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    app.dependency_overrides[get_rate_limit_guard] = lambda: _RecordingGuard(
        seen
    )
    client = TestClient(app)

    client.get("/api/v1/investigations/inv-1")
    client.post("/api/v1/investigations/inv-2/run")

    assert seen == [_READ_OPERATION, RUN_OPERATION_PATH]


# ----------------------------------------------------------------- API edge


def _build_client(guard: RateLimitGuard | None) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_identity] = lambda: _IDENTITY
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    if guard is not None:
        app.dependency_overrides[get_rate_limit_guard] = lambda: guard
    return TestClient(app)


class _AllowAllAuthorizer:
    async def authorize(self, request: object) -> None:
        return None


class _FixedAuthenticator:
    """Accepts every request as the fixed identity, recording each call."""

    def __init__(self, calls: list[str] | None = None) -> None:
        self._calls = calls if calls is not None else []

    async def authenticate(self, request: object) -> AuthenticatedIdentity:
        self._calls.append("authenticate")
        return _IDENTITY


class _RecordingRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class _RecordingGuard:
    """Allows everything and records the operation the seam derived."""

    def __init__(self, seen: list[str]) -> None:
        self._seen = seen

    def check(
        self, identity: AuthenticatedIdentity, operation: str
    ) -> RateLimitDecision:
        self._seen.append(operation)
        return RateLimitDecision(allowed=True)


def test_over_limit_request_returns_429_with_retry_after_and_envelope() -> None:
    guard = _guard(_Clock(), requests=1)
    client = _build_client(guard)
    # The service is unbound in this suite, so the first request fails with
    # 503 — it still consumes the budget, which is the point: the limiter
    # protects the backend regardless of how the operation ends.
    first = client.get("/api/v1/investigations/inv-1")
    second = client.get("/api/v1/investigations/inv-1")

    assert first.status_code != 429
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
    body = second.json()
    assert body["status"] == "error"
    assert body["error"]["code"] == "api.rate_limited"
    assert body["meta"]["request_id"]


def test_rate_limiting_is_disabled_by_default() -> None:
    # No override: the application's own guard, built from the defaults.
    client = _build_client(None)

    statuses = {
        client.get("/api/v1/investigations/inv-1").status_code
        for _ in range(6)
    }

    assert 429 not in statuses


def test_an_anonymous_request_is_unauthenticated_not_rate_limited() -> None:
    # 401 precedes 429: answering 429 to an anonymous caller would confirm
    # that some credential was accepted.
    guard = _guard(_Clock(), requests=1)
    app = create_app()
    app.dependency_overrides[get_rate_limit_guard] = lambda: guard
    client = TestClient(app)

    statuses = [
        client.get("/api/v1/investigations/inv-1").status_code
        for _ in range(3)
    ]

    assert statuses == [401, 401, 401]


def test_authentication_runs_once_per_request() -> None:
    # Two router-level dependencies now chain require_identity. FastAPI caches
    # a dependency per request, and it must stay that way: authenticating twice
    # would double the JWT verification on every single request.
    calls: list[str] = []

    app = create_app()
    app.dependency_overrides[get_authenticator] = lambda: _FixedAuthenticator(
        calls
    )
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    TestClient(app).get("/api/v1/investigations/inv-1")

    assert calls == ["authenticate"]


def test_a_rate_limited_request_is_audited_with_its_subject() -> None:
    # The refusal happens before the authorization context exists, so the
    # audit event has to fall back to the authenticated identity — a
    # security-relevant refusal recorded as anonymous would be useless.
    recorder = _RecordingRecorder()
    app = create_app()
    # The real require_identity must run (it is what stores the identity on the
    # request), so the authenticator is stubbed rather than the seam itself.
    app.dependency_overrides[get_authenticator] = _FixedAuthenticator
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    app.dependency_overrides[get_rate_limit_guard] = lambda: _guard(
        _Clock(), requests=1
    )
    app.state.audit_recorder = recorder
    client = TestClient(app)
    client.get("/api/v1/investigations/inv-1")
    client.get("/api/v1/investigations/inv-1")

    assert recorder.events[-1].subject == _IDENTITY.subject
    assert recorder.events[-1].identity_kind == _IDENTITY.kind.value


def test_rate_limited_request_is_counted_in_the_metrics() -> None:
    guard = _guard(_Clock(), requests=1)
    client = _build_client(guard)
    client.get("/api/v1/investigations/inv-1")
    client.get("/api/v1/investigations/inv-1")

    body = metrics.render()

    assert "sentinelai_rate_limited_total" in body
    assert f'operation="{_READ_OPERATION}"' in body
