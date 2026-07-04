"""Memory Item table (ES-041).

Creates the schema owned by the Memory Service: the versioned ``memory_item``
table, one row per version, primary key ``(id, version)``. No foreign key to
``investigation``: cross-service references are identifiers only
(database-architecture §8a).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_item",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("source_investigation_id", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "supporting_evidence", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column(
            "referenced_findings", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column(
            "referenced_entities", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column(
            "referenced_relationships", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", "version", name=op.f("pk_memory_item")),
    )


def downgrade() -> None:
    op.drop_table("memory_item")
