"""Durable audit log (ES-069, ADR-018).

Creates the Platform-owned, append-only ``audit_log`` table. Two properties are
schema-level rather than conventions:

- **No foreign keys to business data.** An audit record outlives what it
  describes (data-lifecycle.md §5): a referential dependency on erasable rows
  would make the audit exception unimplementable.
- **``recorded_at`` has no server default.** The timestamp is part of the
  content sealed by the hash chain, so it is supplied by the adapter — a
  server-assigned value does not exist yet when the digest is computed.

The index on ``recorded_at`` serves retention expiry, which scans by age.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column(
            "seq",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("identity_kind", sa.Text(), nullable=True),
        sa.Column("operation", sa.Text(), nullable=True),
        sa.Column("resource", sa.Text(), nullable=True),
        # Absent for activities that are not requests (service lifecycle).
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_hash", sa.Text(), nullable=False),
        sa.Column("record_hash", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("seq", name="pk_audit_log"),
    )
    op.create_index(
        "ix_audit_log_recorded_at", "audit_log", ["recorded_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_recorded_at", table_name="audit_log")
    op.drop_table("audit_log")
