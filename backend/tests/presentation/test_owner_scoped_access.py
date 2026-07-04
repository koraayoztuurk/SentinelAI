"""End-to-end tests for the ES-046 security chain.

The development-grade shared-token authenticator (V-3) and the owner-scoped
authorization policy run together through the real HTTP stack: no token →
401; the owner's flow works end to end; a foreign subject gets 403 on
investigation-scoped surfaces; the audit trail carries the denied decision
with its subject. The shared secret comes from the environment through the
SecretProvider (saved/restored manually — no fixtures).
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.application.audit import AuditEvent
from app.application.authorization import OwnerScopedAuthorizer
from app.main import create_app
from app.presentation.api.authorization import get_authorizer
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)
from app.presentation.api.v1.memory.dependencies import get_memory_service
from tests.support.builders import make_investigation_service, make_memory_service

_SECRET = "test-shared-secret-9c1"


class _RecordingAuditRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)


@contextmanager
def _dev_token(value: str | None) -> Iterator[None]:
    saved = os.environ.get("DEV_AUTH_TOKEN")
    if value is None:
        os.environ.pop("DEV_AUTH_TOKEN", None)
    else:
        os.environ["DEV_AUTH_TOKEN"] = value
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("DEV_AUTH_TOKEN", None)
        else:
            os.environ["DEV_AUTH_TOKEN"] = saved


def _stack() -> tuple[TestClient, _RecordingAuditRecorder]:
    """Real authn/authz chain over in-memory services.

    ``create_app`` binds the live shared-token authenticator; the authorizer
    is the owner policy over the same in-memory Investigation Service the
    resource endpoints use (the live binding needs a persistence registry,
    which this suite does not run).
    """

    investigation = make_investigation_service()
    app = create_app()
    recorder = _RecordingAuditRecorder()
    app.state.audit_recorder = recorder
    app.dependency_overrides[get_investigation_service] = lambda: investigation
    app.dependency_overrides[get_memory_service] = make_memory_service
    app.dependency_overrides[get_authorizer] = lambda: OwnerScopedAuthorizer(
        investigation
    )
    return TestClient(app), recorder


def _bearer(subject: str, token: str = _SECRET) -> dict[str, str]:
    return {"Authorization": f"Bearer {subject}:{token}"}


def test_request_without_token_is_401() -> None:
    with _dev_token(_SECRET):
        client, _ = _stack()
        response = client.get("/api/v1/investigations/inv-1")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "api.unauthenticated"


def test_wrong_token_and_malformed_credentials_are_401() -> None:
    with _dev_token(_SECRET):
        client, _ = _stack()
        for headers in (
            _bearer("alice", "wrong-secret"),
            {"Authorization": "Bearer no-colon-credential"},
            {"Authorization": f"Bearer :{_SECRET}"},
            {"Authorization": "Basic something"},
        ):
            response = client.get(
                "/api/v1/investigations/inv-1", headers=headers
            )
            assert response.status_code == 401
            # Credential material never appears in the error body.
            assert _SECRET not in response.text


def test_unset_shared_secret_keeps_everything_401() -> None:
    with _dev_token(None):
        client, _ = _stack()
        response = client.get(
            "/api/v1/investigations/inv-1", headers=_bearer("alice")
        )
        assert response.status_code == 401


def test_owner_flow_works_end_to_end_and_foreign_subject_is_denied() -> None:
    with _dev_token(_SECRET):
        client, recorder = _stack()

        created = client.post(
            "/api/v1/investigations",
            json={"title": "Phish", "owner": "alice", "priority": "high"},
            headers=_bearer("alice"),
        )
        assert created.status_code == 201
        investigation_id = created.json()["data"]["id"]

        # The owner reads and works with the investigation.
        assert (
            client.get(
                f"/api/v1/investigations/{investigation_id}",
                headers=_bearer("alice"),
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/investigations/{investigation_id}/evidence",
                json={"source": "edr", "integrity": "ok", "content": "x"},
                headers=_bearer("alice"),
            ).status_code
            == 201
        )
        assert (
            client.get(
                f"/api/v1/investigations/{investigation_id}/trace",
                headers=_bearer("alice"),
            ).status_code
            == 200
        )

        # A foreign subject is denied on every investigation-scoped surface.
        for path in (
            f"/api/v1/investigations/{investigation_id}",
            f"/api/v1/investigations/{investigation_id}/evidence",
            f"/api/v1/investigations/{investigation_id}/trace",
        ):
            denied = client.get(path, headers=_bearer("bob"))
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "authorization.denied"

        # The audit trail carries the denied decision with its subject.
        denials = [
            event
            for event in recorder.events
            if event.action.value == "authorization.denied"
        ]
        assert denials, "no denied decision reached the audit trail"
        assert all(event.subject == "bob" for event in denials)
        assert all(event.outcome.value == "denied" for event in denials)

        # Shared knowledge layers stay open to any authenticated identity.
        memory = client.post(
            "/api/v1/memory",
            json={
                "type": "attack_pattern",
                "source_investigation_id": investigation_id,
                "confidence": 0.5,
                "status": "candidate",
            },
            headers=_bearer("bob"),
        )
        assert memory.status_code == 201


def test_unknown_investigation_still_reports_404_for_any_subject() -> None:
    with _dev_token(_SECRET):
        client, _ = _stack()
        response = client.get(
            "/api/v1/investigations/missing", headers=_bearer("alice")
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "investigation.not_found"
