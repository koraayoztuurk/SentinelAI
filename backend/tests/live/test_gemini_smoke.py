"""Live Gemini smoke test (ES-043).

Opt-in (`pytest -m live_ai`): one real ``generate`` call against the
configured Gemini model, proving the adapter works end to end with the actual
provider (key from ``GOOGLE_API_KEY``; if the variable is not already set,
it is read from the repository-root ``.env`` — only that variable, nothing
else, so the database configuration of the shell stays authoritative).
"""

import asyncio
import os
from pathlib import Path

import pytest

from app.ai.providers.llm import LLMRequest
from app.config.ai import get_gemini_settings
from app.infrastructure.ai.gemini import GeminiLLMProvider
from app.infrastructure.secrets import EnvironmentSecretProvider

pytestmark = pytest.mark.live_ai

_REPO_ROOT = Path(__file__).resolve().parents[3]


def load_google_api_key() -> bool:
    """Ensure GOOGLE_API_KEY is in the environment; True when available."""

    if os.environ.get("GOOGLE_API_KEY"):
        return True
    env_file = _REPO_ROOT / ".env"
    if not env_file.exists():
        return False
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, _, value = line.strip().partition("=")
        if name.strip() == "GOOGLE_API_KEY" and value.strip():
            os.environ["GOOGLE_API_KEY"] = value.strip()
            return True
    return False


def test_live_generate_smoke() -> None:
    if not load_google_api_key():
        pytest.skip("GOOGLE_API_KEY is not configured")

    provider = GeminiLLMProvider(
        get_gemini_settings(), EnvironmentSecretProvider()
    )
    response = asyncio.run(
        provider.generate(
            LLMRequest(prompt="Reply with exactly one word: pong")
        )
    )
    assert response.text.strip()
