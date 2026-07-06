"""Memory content column + embedding outbox (ES-050).

Adds the embeddable ``memory_item.content`` text (default empty; Option B) and
creates the ``memory_outbox`` table — the transactional outbox that records the
intent to derive a Memory Item embedding, written in the same local transaction
as the Memory Item row (ADR-012). The asynchronous, idempotent projector
consumes it.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_item",
        sa.Column(
            "content", sa.Text(), nullable=False, server_default=""
        ),
    )

    op.create_table(
        "memory_outbox",
        sa.Column(
            "seq", sa.BigInteger(), sa.Identity(always=True), nullable=False
        ),
        sa.Column("memory_id", sa.Text(), nullable=False),
        sa.Column("memory_version", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "processed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.PrimaryKeyConstraint("seq", name=op.f("pk_memory_outbox")),
    )
    # The projector scans for pending work in append order.
    op.create_index(
        op.f("ix_memory_outbox_status"),
        "memory_outbox",
        ["status", "seq"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_outbox_status"), table_name="memory_outbox")
    op.drop_table("memory_outbox")
    op.drop_column("memory_item", "content")
