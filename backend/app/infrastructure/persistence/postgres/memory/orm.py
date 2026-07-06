"""ORM model for the versioned Memory Item (PostgreSQL).

One row per Memory Item *version*: the primary key is ``(id, version)``, so
the version-supersede pattern (ES-007) is a plain insert and historical
versions stay immutable rows. ``source_investigation_id`` is a plain
identifier value, not a foreign key: the investigation belongs to another
service's schema, and identifiers are the only cross-service reference
mechanism (database-architecture §8a).
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.postgres.base import Base


class MemoryItemRow(Base):
    """Row of the ``memory_item`` table (one row per version)."""

    __tablename__ = "memory_item"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    source_investigation_id: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # The embeddable knowledge text (default empty); the derived embedding
    # lives in the Vector Database, never in this authoritative row.
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    supporting_evidence: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    referenced_findings: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    referenced_entities: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    referenced_relationships: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
