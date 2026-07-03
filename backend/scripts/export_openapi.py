"""Export the published API contract artifact (api-design, Contract Synchronization).

Writes the backend's machine-readable API contract (OpenAPI document) to
``docs/api/openapi.json`` at the repository root. The committed artifact is the
single contract source consumers derive from (frontend types, mocks); the
``test_openapi_contract`` architecture check fails whenever the artifact is
stale, forcing regeneration through this script:

    cd backend && python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
ARTIFACT = REPO_ROOT / "docs" / "api" / "openapi.json"


def render_contract() -> str:
    """Return the deterministic JSON rendering of the API contract."""

    sys.path.insert(0, str(BACKEND_ROOT))
    from app.main import create_app

    schema = create_app().openapi()
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(render_contract(), encoding="utf-8", newline="\n")
    print(f"wrote {ARTIFACT}")


if __name__ == "__main__":
    main()
