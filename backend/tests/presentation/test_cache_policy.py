"""Tests for the response cache policy (ES-068).

The posture is that nothing the backend serves may be stored (api-design §13):
API responses are identity/tenant-scoped and erasable, operational answers are
about *now*. These tests hold that line on the surfaces where breaking it would
matter most — an error response, an unauthenticated rejection and a health
answer are all covered, not just the happy path.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.presentation.api.caching import NO_STORE, is_non_storable

pytestmark = pytest.mark.operational


def test_api_responses_are_not_storable() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/investigations/inv-1")

    # Unauthenticated (401) — an error envelope must carry the policy too:
    # the paths that leak most easily are the ones nobody looks at.
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == NO_STORE


def test_operational_endpoints_are_not_storable() -> None:
    with TestClient(create_app()) as client:
        for path in ("/health", "/health/ready", "/metrics"):
            assert client.get(path).headers["Cache-Control"] == NO_STORE


def test_policy_covers_the_api_and_operational_surfaces_only() -> None:
    assert is_non_storable("/api/v1/investigations/inv-1")
    assert is_non_storable("/health/ready")
    # The contract artifact and the docs are not identity-scoped data.
    assert not is_non_storable("/openapi.json")
    assert not is_non_storable("/docs")
