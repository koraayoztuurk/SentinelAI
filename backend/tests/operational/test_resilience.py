"""Resilience Validation (ES-036, performance-reliability §5).

Verifies that the platform preserves its intended operational behavior under
failure conditions: an unexpected in-request failure is contained to that
request (500 envelope, no crash), the containment is consistent across repeated
failures, and the operational surfaces keep serving while business requests
fail. Architectural assurance only — no recovery mechanisms are prescribed.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.presentation.api.authorization import require_authorization
from app.presentation.api.v1.investigation.dependencies import (
    get_investigation_service,
)

pytestmark = pytest.mark.operational


def _raise_unexpected() -> None:
    raise RuntimeError("unplanned infrastructure failure")


def _failing_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None
    app.dependency_overrides[get_investigation_service] = _raise_unexpected
    # The server-side containment is exactly what is under test here.
    return TestClient(app, raise_server_exceptions=False)


def test_unexpected_failure_is_contained_per_request() -> None:
    """An unplanned failure yields the generic envelope, never a crash."""

    # The context manager runs the lifespan, so readiness reflects startup.
    with _failing_client() as client:
        response = client.get("/api/v1/investigations/inv-1")
        assert response.status_code == 500
        body = response.json()
        assert body["status"] == "error"
        assert body["error"]["code"] == "internal_server_error"
        # The failure detail never leaks to the caller.
        assert "unplanned infrastructure failure" not in response.text

        # The platform keeps serving after the failure.
        assert client.get("/health").status_code == 200
        assert client.get("/health/ready").status_code == 200


def test_containment_is_consistent_across_repeated_failures() -> None:
    """Repeated unexpected failures behave identically (no degradation)."""

    client = _failing_client()

    statuses = set()
    codes = set()
    for _ in range(5):
        response = client.get("/api/v1/investigations/inv-1")
        statuses.add(response.status_code)
        codes.add(response.json()["error"]["code"])
        assert client.get("/health").status_code == 200

    assert statuses == {500}
    assert codes == {"internal_server_error"}
