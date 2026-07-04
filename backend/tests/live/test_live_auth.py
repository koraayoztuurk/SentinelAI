"""Live security-chain test over the real stack (ES-046).

Opt-in (`pytest -m live`): the full production wiring with **no dependency
overrides** — shared-token authentication (secret via the SecretProvider),
the owner-scoped authorization policy over the live Investigation Service,
the live PostgreSQL adapters and the audit middleware all run together:
no token → 401, the owner's flow is 200 end to end, a foreign subject is
403 on investigation-scoped surfaces.
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.live.support import ensure_schema, live_engine, truncate_tables

pytestmark = pytest.mark.live

_SECRET = "live-shared-secret-51d"


def _reset_database() -> None:
    async def scenario() -> None:
        engine = live_engine()
        try:
            await truncate_tables(
                engine,
                "trace_entry",
                "investigation_outcome",
                "report",
                "finding",
                "evidence",
                "investigation",
            )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def _bearer(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {subject}:{_SECRET}"}


def test_live_security_chain_enforces_ownership() -> None:
    ensure_schema()
    _reset_database()

    saved = os.environ.get("DEV_AUTH_TOKEN")
    os.environ["DEV_AUTH_TOKEN"] = _SECRET
    try:
        with TestClient(create_app()) as client:
            # Anonymous requests are rejected before any business code runs.
            assert client.get("/api/v1/investigations/x").status_code == 401

            # The owner's flow works end to end against the live store.
            created = client.post(
                "/api/v1/investigations",
                json={"title": "Live auth", "owner": "alice", "priority": "high"},
                headers=_bearer("alice"),
            )
            assert created.status_code == 201
            investigation_id = created.json()["data"]["id"]

            fetched = client.get(
                f"/api/v1/investigations/{investigation_id}",
                headers=_bearer("alice"),
            )
            assert fetched.status_code == 200

            trace = client.get(
                f"/api/v1/investigations/{investigation_id}/trace",
                headers=_bearer("alice"),
            )
            assert trace.status_code == 200
            assert trace.json()["data"] == []

            # A foreign subject cannot cross the investigation scope.
            denied = client.get(
                f"/api/v1/investigations/{investigation_id}",
                headers=_bearer("bob"),
            )
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "authorization.denied"

            # Operational surfaces stay public.
            assert client.get("/health").status_code == 200
    finally:
        if saved is None:
            os.environ.pop("DEV_AUTH_TOKEN", None)
        else:
            os.environ["DEV_AUTH_TOKEN"] = saved
