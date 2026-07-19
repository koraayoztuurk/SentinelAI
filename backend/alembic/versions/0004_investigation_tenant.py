"""Investigation tenant scope (ES-063, ADR-016).

Adds the ``tenant`` organization-scope column to the investigation table. The
column is NOT NULL with a server default of ``'default'``, which backfills
every existing row to the default tenant — matching the dev/claim-less
identity tenant, so no existing investigation becomes inaccessible after the
upgrade. New rows always carry a tenant supplied by the application (derived
from the authenticated identity), so the server default only governs the
backfill.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigation",
        sa.Column(
            "tenant",
            sa.Text(),
            nullable=False,
            server_default="default",
        ),
    )


def downgrade() -> None:
    op.drop_column("investigation", "tenant")
