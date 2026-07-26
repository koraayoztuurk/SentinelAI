"""Memory Service exceptions.

Service-level errors raised by the Memory Service. Each derives from the shared
:class:`~app.shared.exceptions.SentinelAIError` and carries a stable
machine-readable ``code`` so the API layer can translate them into consistent
responses. Only errors tied to an enforced rule are defined here.
"""

from app.shared.exceptions import SentinelAIError


class MemoryServiceError(SentinelAIError):
    """Base class for Memory Service errors."""

    code = "memory.error"


class MemoryNotFoundError(MemoryServiceError):
    """Raised when a referenced Memory Item does not exist."""

    code = "memory.not_found"


class DuplicateMemoryError(MemoryServiceError):
    """Raised when creating a Memory Item whose identifier already exists."""

    code = "memory.duplicate"


class InvalidMemoryVersionError(MemoryServiceError):
    """Raised when a Memory Item version is not sequential.

    Applies to creation with a version other than 1, and to updates whose version
    does not immediately follow the latest persisted version.
    """

    code = "memory.invalid_version"


class MemoryVectorStoreUnavailableError(MemoryServiceError):
    """Raised when the derived embedding store cannot be reached (ES-051).

    The operational counterpart of ``graph.store_unavailable``: the concrete
    vector-store adapter maps driver-level connectivity failures to this stable
    code so consumers (semantic retrieval) can contain the outage — the derived
    representation is supportive, never authoritative (ADR-012).

    Since ES-067 the **write** path maps to this code too: a projection failure
    used to leak the raw driver exception and was contained only by the
    background loop's broad catch, so it could not be classified or retried
    deliberately.
    """

    code = "memory.vector_store_unavailable"


class MemoryVectorDimensionMismatchError(MemoryServiceError):
    """Raised when the collection's vector size contradicts the embedder (ES-067).

    Not an outage but a **consistency** failure: an existing collection built
    for a different embedding dimension cannot hold this embedder's vectors, and
    every upsert into it would fail one at a time. The adapter refuses up front
    so the mismatch is reported once, explicitly, instead of surfacing as a
    stream of opaque per-record write errors (the ES-053 finding: live tests
    left ``memory_embeddings`` at dim 3 on the instance the app uses at dim
    768).
    """

    code = "memory.vector_dimension_mismatch"
