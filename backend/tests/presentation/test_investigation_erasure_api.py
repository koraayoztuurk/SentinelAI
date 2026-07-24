"""End-to-end tests for the investigation erasure endpoint (ES-064, ADR-017).

``DELETE /api/v1/investigations/{id}`` runs through the real HTTP stack with the
owner-scoped authorization policy: the owner erases and reads the tombstone, a
foreign subject is denied, re-erasure is idempotent, business writes to an erased
investigation are 409, and a read of an erased investigation resolves to an
explicit tombstone (never a 404-as-if-never-existed).
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
from tests.support.builders import make_investigation_service

_SECRET = "test-shared-secret-9c1"


class _RecordingAuditRecorder:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)


@contextmanager
def _dev_token(value: str) -> Iterator[None]:
    saved = os.environ.get("DEV_AUTH_TOKEN")
    os.environ["DEV_AUTH_TOKEN"] = value
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop("DEV_AUTH_TOKEN", None)
        else:
            os.environ["DEV_AUTH_TOKEN"] = saved


def _stack(recorder: _RecordingAuditRecorder | None = None) -> TestClient:
    investigation = make_investigation_service()
    app = create_app()
    if recorder is not None:
        app.state.audit_recorder = recorder
    app.dependency_overrides[get_investigation_service] = lambda: investigation
    app.dependency_overrides[get_authorizer] = lambda: OwnerScopedAuthorizer(
        investigation
    )
    return TestClient(app)


def _bearer(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {subject}:{_SECRET}"}


def _create(client: TestClient, subject: str = "alice") -> str:
    created = client.post(
        "/api/v1/investigations",
        json={"title": "Phish", "priority": "high"},
        headers=_bearer(subject),
    )
    assert created.status_code == 201
    investigation_id = created.json()["data"]["id"]
    assert isinstance(investigation_id, str)
    return investigation_id


def test_erase_returns_the_tombstone_envelope() -> None:
    with _dev_token(_SECRET):
        client = _stack()
        investigation_id = _create(client)

        erased = client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )
        assert erased.status_code == 200
        data = erased.json()["data"]
        assert data["status"] == "erased"
        assert data["title"] == "[erased]"
        assert data["erased_at"] is not None
        # Owner survives so the tombstone stays owner-scoped.
        assert data["owner"] == "alice"


def test_erase_is_idempotent() -> None:
    with _dev_token(_SECRET):
        client = _stack()
        investigation_id = _create(client)

        first = client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )
        second = client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["status"] == "erased"


def test_foreign_subject_cannot_erase() -> None:
    with _dev_token(_SECRET):
        client = _stack()
        investigation_id = _create(client, subject="alice")

        denied = client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("bob"),
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "authorization.denied"


def test_get_after_erase_resolves_to_the_tombstone() -> None:
    with _dev_token(_SECRET):
        client = _stack()
        investigation_id = _create(client)
        client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )

        fetched = client.get(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )
        # Observable, not a 404-as-if-never-existed (§8a).
        assert fetched.status_code == 200
        assert fetched.json()["data"]["status"] == "erased"


def test_business_write_after_erase_returns_409() -> None:
    with _dev_token(_SECRET):
        client = _stack()
        investigation_id = _create(client)
        client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )

        attach = client.post(
            f"/api/v1/investigations/{investigation_id}/evidence",
            json={"source": "edr", "integrity": "ok", "content": "x"},
            headers=_bearer("alice"),
        )
        assert attach.status_code == 409
        assert attach.json()["error"]["code"] == "investigation.erased"


def test_erasure_is_audited() -> None:
    with _dev_token(_SECRET):
        recorder = _RecordingAuditRecorder()
        client = _stack(recorder)
        investigation_id = _create(client)

        erased = client.delete(
            f"/api/v1/investigations/{investigation_id}",
            headers=_bearer("alice"),
        )
        assert erased.status_code == 200

        # Erasure rides the operation-audit boundary (§5, ADR-017 §7): a
        # succeeded operation event names who erased what.
        erase_events = [
            event
            for event in recorder.events
            if event.action.value == "operation.performed"
            and event.operation is not None
            and event.operation.startswith("DELETE ")
            and investigation_id in event.operation
        ]
        assert erase_events, "the erasure was not audited"
        assert all(event.subject == "alice" for event in erase_events)
        assert all(
            event.outcome.value == "succeeded" for event in erase_events
        )
