"""API contract artifact freshness (api-design, Contract Synchronization).

The committed ``docs/api/openapi.json`` is the published API contract that
frontend types and mocks derive from. This check fails whenever the running
application's contract diverges from the committed artifact, forcing an explicit
regeneration (``python scripts/export_openapi.py``) so contract changes are
always visible in review — never silent.
"""

import json
from pathlib import Path

import pytest

from app.main import create_app

_ARTIFACT = (
    Path(__file__).resolve().parents[2].parent / "docs" / "api" / "openapi.json"
)

pytestmark = pytest.mark.architecture


def test_committed_contract_matches_application() -> None:
    assert _ARTIFACT.exists(), (
        "docs/api/openapi.json is missing; generate it with "
        "`python scripts/export_openapi.py`."
    )
    committed = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    live = create_app().openapi()
    assert committed == live, (
        "docs/api/openapi.json is stale; regenerate it with "
        "`python scripts/export_openapi.py`."
    )
