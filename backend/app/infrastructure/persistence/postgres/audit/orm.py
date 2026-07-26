"""ORM model for the durable audit log (PostgreSQL, ES-069 / ADR-018).

The audit log is a **Platform-owned authoritative** category (ADR-018 §1): its
records are derived from nothing, so they are primary evidence, and they carry
**no foreign keys to business data** — an audit record outlives what it
describes (data-lifecycle.md §5), so a referential dependency on erasable rows
would contradict its purpose.

``seq`` is a server-generated identity and the chain order. ``record_hash`` /
``previous_hash`` carry the tamper-evidence chain (ADR-018 §3); ``recorded_at``
is part of the sealed content, so it is supplied by the adapter rather than
assigned by the database — a server-assigned value does not exist yet when the
digest is computed.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.postgres.base import Base


class AuditRecordRow(Base):
    """Row of the append-only ``audit_log`` table."""

    __tablename__ = "audit_log"

    seq: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_kind: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    previous_hash: Mapped[str] = mapped_column(Text, nullable=False)
    record_hash: Mapped[str] = mapped_column(Text, nullable=False)
