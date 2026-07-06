"""ORM model for the memory embedding outbox (PostgreSQL, ES-050).

The outbox lives in the authoritative store (PostgreSQL) so a Memory Item write
and its derivation intent commit in the same local transaction (ADR-012).
``seq`` is a server-generated identity: it is both the primary key and the
append-order the projector scans in. ``created_at``/``processed_at`` use the
database clock (an infrastructure concern — the no-clock rule constrains the
domain and services, not adapters).
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.postgres.base import Base


class MemoryOutboxRow(Base):
    """Row of the ``memory_outbox`` table."""

    __tablename__ = "memory_outbox"

    seq: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    memory_id: Mapped[str] = mapped_column(Text, nullable=False)
    memory_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
