"""Durable audit sink (PostgreSQL, ES-069 / ADR-018).

The Platform-owned authoritative audit log: an append-only table sealed by a
hash chain, with retention expiry as its only removal path.
"""

from app.infrastructure.persistence.postgres.audit.chain import (
    GENESIS_HASH,
    ChainVerification,
    SealedAuditRecord,
    compute_hash,
    seal,
    verify_chain,
)
from app.infrastructure.persistence.postgres.audit.orm import AuditRecordRow
from app.infrastructure.persistence.postgres.audit.recorder import (
    PostgresAuditRecorder,
)

__all__ = [
    "AuditRecordRow",
    "ChainVerification",
    "GENESIS_HASH",
    "PostgresAuditRecorder",
    "SealedAuditRecord",
    "compute_hash",
    "seal",
    "verify_chain",
]
