"""Smoke test for the health endpoint.

Verifies the ES-002 acceptance criteria that the application starts and the
health endpoint responds correctly.
"""

import pytest
from fastapi.testclient import TestClient

from app import __version__
from app.main import app

pytestmark = pytest.mark.operational

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["name"] == "SentinelAI"
    assert body["version"] == __version__
    assert body["environment"] == "development"
