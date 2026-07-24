"""ORM models for the Investigation family (PostgreSQL).

Row classes mirroring the Investigation-family domain objects one to one.
Lifecycle states are stored as their stable string values (no database enum
types, so vocabulary evolution never requires a type migration). Identifier
lists are PostgreSQL text arrays. Cross-object references within the
Investigation Service's own schema are real foreign keys; references to
objects owned by other services (entities, relationships) remain plain
identifier values (database-architecture §8a: identifiers are the only
cross-store mechanism).

``TraceEntryRow.seq`` is a server-generated, monotonically increasing value
recording append order: the trace is append-only and must be read back in
exactly the order it was written, independent of caller-supplied timestamps.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Identity, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.postgres.base import Base


class InvestigationRow(Base):
    """Row of the ``investigation`` table."""

    __tablename__ = "investigation"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    # Organization access scope (ADR-016); server default backfills pre-tenant
    # rows to the default tenant (migration 0004).
    tenant: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="default"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    # End-of-life timestamp (ADR-017, migration 0005): NULL for a live
    # investigation, set when the row is tombstoned (status 'erased').
    erased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EvidenceRow(Base):
    """Row of the ``evidence`` table."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigation.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    integrity: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class FindingRow(Base):
    """Row of the ``finding`` table."""

    __tablename__ = "finding"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigation.id"), nullable=False, index=True
    )
    supporting_evidence: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    creator: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    related_entities: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    related_relationships: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )


class ReportRow(Base):
    """Row of the ``report`` table."""

    __tablename__ = "report"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigation.id"), nullable=False, index=True
    )
    author: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class InvestigationOutcomeRow(Base):
    """Row of the ``investigation_outcome`` table.

    ``investigation_id`` is unique: the 0..1 outcome-per-investigation rule
    (domain-model §16) is enforced by the database as well as the service.
    ``report_id`` is a plain identifier (the service does not validate it, so
    the schema stays no stricter than the owning service).
    """

    __tablename__ = "investigation_outcome"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigation.id"), nullable=False, unique=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    contributing_findings: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    detected_conflicts: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    open_questions: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    report_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class TraceEntryRow(Base):
    """Row of the ``trace_entry`` table (append-only)."""

    __tablename__ = "trace_entry"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    seq: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), nullable=False, unique=True
    )
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigation.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
