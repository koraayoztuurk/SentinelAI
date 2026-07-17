"""Object store adapters (ADR-015).

Concrete realizations of the application-layer ``EvidencePayloadStore`` port.
The first adapter is the dev-grade content-addressed filesystem store; an
S3-compatible object store is the production path (Milestone G).
"""

from app.infrastructure.objectstore.filesystem import (
    FilesystemEvidencePayloadStore,
)

__all__ = ["FilesystemEvidencePayloadStore"]
