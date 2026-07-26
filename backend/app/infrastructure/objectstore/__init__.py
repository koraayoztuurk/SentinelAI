"""Object store adapters (ADR-015).

Concrete realizations of the application-layer ``EvidencePayloadStore`` port:
the dev-grade content-addressed filesystem store (ES-060), and the
crypto-shredding store (ES-070) that composes two of them — one for payload
bytes, one for keys — to realize the erasure strategy ADR-015 §6 / ADR-017 §6
designate for production, where deleting an object cannot be trusted to
destroy its bytes.
"""

from app.infrastructure.objectstore.cryptoshred import CryptoShredPayloadStore
from app.infrastructure.objectstore.filesystem import (
    FilesystemEvidencePayloadStore,
)

__all__ = ["CryptoShredPayloadStore", "FilesystemEvidencePayloadStore"]
