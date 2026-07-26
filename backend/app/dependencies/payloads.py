"""Evidence payload store composition (ES-060/ES-070, ADR-015).

One builder for the two places that need the store — the request path and the
erasure projector — so the configured erasure strategy cannot differ between
writing a payload and shredding it. Two composition sites drifting apart is
exactly how a payload would end up encrypted by one and "deleted" by the other.
"""

import logging
from pathlib import Path

from app.application.investigation.payload_store import EvidencePayloadStore
from app.config.database import get_evidence_payload_settings
from app.infrastructure.objectstore import (
    CryptoShredPayloadStore,
    FilesystemEvidencePayloadStore,
)

logger = logging.getLogger(__name__)


def build_payload_store() -> EvidencePayloadStore:
    """Return the configured payload store (``EVIDENCE_PAYLOAD_CRYPTO_SHRED``).

    Crypto-shredding keeps payload bytes and keys in **separate** stores, so a
    deployment can hold the payload tier immutable and backed up while the key
    tier stays mutable and excluded from backups — the separation is what makes
    shredding real rather than decorative.
    """

    settings = get_evidence_payload_settings()
    root = Path(settings.root)
    payloads = FilesystemEvidencePayloadStore(root)
    if not settings.crypto_shred:
        return payloads
    logger.info(
        "evidence payloads are crypto-shredded; key material lives under "
        "the store's keys/ directory and must be excluded from backups"
    )
    return CryptoShredPayloadStore(
        payloads, FilesystemEvidencePayloadStore(root / "keys")
    )
