"""Tests for the operational observability endpoints (ES-031)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

pytestmark = pytest.mark.operational


def test_readiness_reflects_unreachable_postgres_after_startup() -> None:
    # The lifespan (run inside the context manager) builds the persistence
    # registry, but no live PostgreSQL exists in this suite: since the runtime
    # persistence binding (ES-042) readiness probes the store, so the backend
    # reports not-ready while liveness stays healthy. The ready happy path is
    # verified by the live suite (`pytest -m live`).
    with TestClient(create_app()) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert body["postgres"] == "unavailable"
        assert client.get("/health").status_code == 200


def test_readiness_is_not_ready_without_startup() -> None:
    # No context manager → the lifespan does not run → the registry is absent.
    response = TestClient(create_app()).get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["postgres"] == "not_initialized"


def test_metrics_exposes_request_counter() -> None:
    with TestClient(create_app()) as client:
        client.get("/health")  # records a GET / 200 request
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert "sentinelai_requests_total" in body
        assert 'method="GET"' in body
        assert "sentinelai_uptime_seconds" in body
