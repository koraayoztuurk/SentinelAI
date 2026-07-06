"""Memory Service package.

Exposes the Memory Service and its error types. The repository contract lives in
:mod:`app.application.memory.repositories` and is imported directly by the
infrastructure adapter that implements it.
"""

from app.application.memory.embedding import MemoryEmbedder, MemoryEmbeddingError
from app.application.memory.errors import (
    DuplicateMemoryError,
    InvalidMemoryVersionError,
    MemoryNotFoundError,
    MemoryServiceError,
)
from app.application.memory.service import MemoryService

__all__ = [
    "MemoryService",
    "MemoryServiceError",
    "MemoryNotFoundError",
    "DuplicateMemoryError",
    "InvalidMemoryVersionError",
    "MemoryEmbedder",
    "MemoryEmbeddingError",
]
