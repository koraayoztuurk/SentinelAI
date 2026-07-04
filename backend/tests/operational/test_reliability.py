"""Reliability Validation (ES-036, performance-reliability §5).

Verifies that the platform preserves consistent operational behavior under
sustained use: repeated requests behave identically, per-request identifiers
stay unique, the correlation contract holds across many requests, error and
success traffic interleave without degradation and the operational metrics grow
monotonically with traffic. Architectural assurance only — no wall-clock
thresholds or benchmark metrics (performance-reliability §3).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.presentation.api.authorization import require_authorization

pytestmark = pytest.mark.operational


def test_sustained_requests_remain_consistent() -> None:
    """Repeated identical requests produce identical, healthy responses."""

    client = TestClient(create_app())

    bodies = []
    request_ids = []
    for _ in range(25):
        response = client.get("/health")
        assert response.status_code == 200
        bodies.append(response.json())
        request_ids.append(response.headers["X-Request-ID"])

    assert all(body == bodies[0] for body in bodies)
    # Traceability under sustained use: every request keeps its own identity.
    assert len(set(request_ids)) == len(request_ids)


def test_correlation_contract_holds_under_sustained_use() -> None:
    """Every request echoes its caller-supplied correlation id, one by one."""

    client = TestClient(create_app())

    for index in range(10):
        correlation_id = f"corr-{index}"
        response = client.get(
            "/health", headers={"X-Correlation-ID": correlation_id}
        )
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == correlation_id


def test_error_and_success_traffic_interleave_without_degradation() -> None:
    """Failing business traffic never degrades healthy operational traffic."""

    app = create_app()
    app.dependency_overrides[require_authorization] = lambda: None

    # The context manager runs the lifespan, so the live persistence binding
    # (ES-042) is active — but no PostgreSQL is reachable in this suite.
    with TestClient(app) as client:
        for _ in range(10):
            # Business endpoint: the unreachable store degrades to a stable 503.
            failed = client.post(
                "/api/v1/investigations",
                json={"title": "Phish", "owner": "analyst-1", "priority": "high"},
            )
            assert failed.status_code == 503
            assert (
                failed.json()["error"]["code"] == "api.persistence_unavailable"
            )

            # Operational surfaces stay healthy between the failures.
            assert client.get("/health").status_code == 200

        # Readiness keeps serving and truthfully reports the store as down.
        ready = client.get("/health/ready")
        assert ready.status_code == 503
        assert ready.json() == {"status": "not_ready", "postgres": "unavailable"}


def _duration_count(metrics_text: str) -> int:
    for line in metrics_text.splitlines():
        if line.startswith("sentinelai_request_duration_ms_count "):
            return int(line.rsplit(" ", 1)[1])
    raise AssertionError("duration count metric not found")


def test_metrics_grow_monotonically_with_traffic() -> None:
    """The request counters only ever grow while traffic is served."""

    client = TestClient(create_app())

    before = _duration_count(client.get("/metrics").text)
    for _ in range(5):
        assert client.get("/health").status_code == 200
    after = _duration_count(client.get("/metrics").text)

    # The process-wide registry must have observed at least the five requests.
    assert after >= before + 5
