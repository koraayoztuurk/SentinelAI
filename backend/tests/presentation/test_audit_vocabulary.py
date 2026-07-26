"""Tests for the widened audit vocabulary and sink containment (ES-069).

ADR-018 §7 makes the action categories real: an erasure is recorded as an
erasure, a refused request as a policy enforcement, and every record names the
resource it affected — by identifier, never by content. §8 requires a sink
failure to be contained, counted and degraded to the log sink rather than lost.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.audit import AuditAction, AuditEvent, AuditOutcome
from app.config.rate_limit import RateLimitSettings
from app.main import create_app
from app.observability import metrics
from app.presentation.api.audit import ERASE_OPERATION
from app.presentation.api.auth import (
    AuthenticatedIdentity,
    IdentityKind,
    get_authenticator,
)
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.rate_limit import RateLimitGuard, get_rate_limit_guard

pytestmark = pytest.mark.operational

_IDENTITY = AuthenticatedIdentity(subject="analyst", kind=IdentityKind.HUMAN)


class _RecordingRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class _FailingRecorder:
    async def record(self, event: AuditEvent) -> None:
        raise RuntimeError("audit sink unavailable")


class _AllowAllAuthorizer:
    async def authorize(self, request: object) -> None:
        return None


class _FixedAuthenticator:
    async def authenticate(self, request: object) -> AuthenticatedIdentity:
        return _IDENTITY


def _client(recorder: object, *, guard: RateLimitGuard | None = None) -> TestClient:
    app = create_app()
    # The authenticator is stubbed rather than the identity seam, so the real
    # require_identity runs and stores the identity — which is what a
    # pre-authorization refusal (429) has to fall back to.
    app.dependency_overrides[get_authenticator] = _FixedAuthenticator
    app.dependency_overrides[get_authorizer] = _AllowAllAuthorizer
    if guard is not None:
        app.dependency_overrides[get_rate_limit_guard] = lambda: guard
    app.state.audit_recorder = recorder
    return TestClient(app)


# ---------------------------------------------------------------- vocabulary


def test_the_vocabulary_carries_no_value_nothing_emits() -> None:
    # ADR-018 §7: a placeholder action would assert an accountability
    # capability the platform does not have. The administrative category has
    # no surface, so it has no value.
    assert {action.value for action in AuditAction} == {
        "authentication.failed",
        "authorization.denied",
        "operation.performed",
        "investigation.erased",
        "traffic.limit_enforced",
        "service.started",
        "service.stopped",
    }


def test_a_refused_request_is_recorded_as_policy_enforcement() -> None:
    recorder = _RecordingRecorder()
    guard = RateLimitGuard(
        RateLimitSettings(enabled=True, requests=1, window_seconds=60.0)
    )
    client = _client(recorder, guard=guard)

    client.get("/api/v1/investigations/inv-1")
    refused = client.get("/api/v1/investigations/inv-1")

    assert refused.status_code == 429
    event = recorder.events[-1]
    assert event.action is AuditAction.TRAFFIC_LIMIT_ENFORCED
    # A refusal is a denial, not a failure: nothing went wrong, the platform
    # declined.
    assert event.outcome is AuditOutcome.DENIED
    assert event.subject == _IDENTITY.subject


def test_an_unauthenticated_request_is_recorded_as_an_identity_failure() -> None:
    recorder = _RecordingRecorder()
    app = create_app()
    app.state.audit_recorder = recorder
    client = TestClient(app)

    client.get("/api/v1/investigations/inv-1")

    event = recorder.events[-1]
    assert event.action is AuditAction.AUTHENTICATION_FAILED
    assert event.subject is None


def test_the_erase_operation_is_matched_exactly() -> None:
    # The erasure action is selected by the *exact* operation, not by "a DELETE
    # with an investigation id in the path" — otherwise a future DELETE of a
    # sub-resource would be recorded as an investigation erasure. Pinning the
    # constant to the published contract means a route rename fails loudly
    # instead of silently retiring the erasure category.
    paths = create_app().openapi()["paths"]

    assert ERASE_OPERATION in paths
    assert "delete" in paths[ERASE_OPERATION]


def test_the_record_names_the_affected_resource() -> None:
    recorder = _RecordingRecorder()
    client = _client(recorder)

    client.get("/api/v1/investigations/inv-42")

    assert recorder.events[-1].resource == "inv-42"


def test_the_affected_resource_is_the_most_specific_one() -> None:
    # /investigations/{id}/evidence/{evidence_id} affects the evidence item.
    recorder = _RecordingRecorder()
    client = _client(recorder)

    client.get("/api/v1/investigations/inv-1/evidence/ev-7")

    assert recorder.events[-1].resource == "ev-7"


# ---------------------------------------------------------------- containment


def test_a_sink_failure_never_fails_the_operation() -> None:
    # ES-021's stance, kept: audit observes the platform, it cannot stop it.
    client = _client(_FailingRecorder())

    response = client.get("/api/v1/investigations/inv-1")

    assert response.status_code != 500


def test_a_sink_failure_is_counted() -> None:
    # ADR-018 §8: an unrecorded action is an accountability gap, so it must
    # never be quiet.
    before = metrics.render()
    client = _client(_FailingRecorder())

    client.get("/api/v1/investigations/inv-1")

    assert "sentinelai_audit_write_failures_total" in before
    assert _failure_count(metrics.render()) > _failure_count(before)


def _failure_count(rendered: str) -> int:
    for line in rendered.splitlines():
        if line.startswith("sentinelai_audit_write_failures_total "):
            return int(line.rsplit(" ", 1)[1])
    return 0
