"""Live Gemini embedding smoke test (ES-049).

Opt-in (`pytest -m live_ai`): one real ``embed`` call against the configured
Gemini embedding model, proving the adapter works end to end with the actual
provider. Reuses the LLM smoke's ``load_google_api_key`` (env, falling back to
the repository-root ``.env``); skips without a key.
"""

import asyncio

import pytest

from app.config.ai import get_gemini_embedding_settings
from app.infrastructure.ai.gemini_embedding import GeminiEmbeddingProvider
from app.infrastructure.secrets import EnvironmentSecretProvider
from tests.live.test_gemini_smoke import load_google_api_key

pytestmark = pytest.mark.live_ai


def test_live_embed_smoke() -> None:
    if not load_google_api_key():
        pytest.skip("GOOGLE_API_KEY is not configured")

    provider = GeminiEmbeddingProvider(
        get_gemini_embedding_settings(), EnvironmentSecretProvider()
    )
    vector = asyncio.run(provider.embed("suspicious beaconing to a rare domain"))

    # A real embedding is a non-empty fixed-dimension float vector.
    assert len(vector) > 0
    assert all(isinstance(v, float) for v in vector)
