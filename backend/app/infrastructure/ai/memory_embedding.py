"""Memory-Service embedding adapter (ADR-012 §3, ES-049).

Infrastructure realization of the Memory Service's application-owned embedding
port (:class:`~app.application.memory.MemoryEmbedder`). It **delegates to the AI
Runtime's provider-neutral embedding provider** — ADR-012 §3 explicitly permits
the concrete adapter to use the AI Runtime port internally — and translates the
AI-layer :class:`~app.ai.errors.EmbeddingProviderError` into the memory port's
stable :class:`~app.application.memory.MemoryEmbeddingError`.

This bridge is where the two layers meet: infrastructure may implement a port
from one layer (Memory Service) while consuming a port from another (AI
Runtime). The Memory Service itself never imports the AI Runtime, so AC-04 is
preserved. The outbox projector (ES-050) depends only on ``MemoryEmbedder``.
"""

from app.ai.errors import EmbeddingProviderError
from app.ai.providers.embedding import EmbeddingProvider
from app.application.memory import MemoryEmbeddingError


class EmbeddingMemoryAdapter:
    """``MemoryEmbedder`` over an AI Runtime ``EmbeddingProvider``."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    async def embed(self, text: str) -> tuple[float, ...]:
        """Produce the embedding, mapping provider failures to the memory port."""

        try:
            return await self._provider.embed(text)
        except EmbeddingProviderError as exc:
            raise MemoryEmbeddingError(
                f"Memory Item embedding failed ({exc.code})."
            ) from exc
