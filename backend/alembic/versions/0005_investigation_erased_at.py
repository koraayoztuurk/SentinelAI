"""Investigation erasure timestamp (ES-064, ADR-017).

Adds the ``erased_at`` end-of-life timestamp column to the investigation table.
The column is nullable — NULL for a live investigation, set when the row is
tombstoned (status ``'erased'``, data-lifecycle.md / ADR-017). No backfill and
no default: every existing row is live, so ``erased_at`` stays NULL until an
investigation is erased. The terminal ``ERASED`` status needs no migration —
lifecycle states are stored as plain text values (no database enum type).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigation",
        sa.Column(
            "erased_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("investigation", "erased_at")
