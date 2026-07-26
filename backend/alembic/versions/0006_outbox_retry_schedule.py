"""Outbox retry schedule (ES-067, ADR-012).

Adds ``next_attempt_at`` to ``memory_outbox`` so a failed projection can back
off instead of being retried every poll interval. The column is nullable: NULL
means "due now", which is exactly the state of every freshly enqueued record,
so no default and no backfill are needed for pending rows.

Existing ``'failed'`` rows **are** rewritten to ``'pending'``. Before ES-067 a
failed record was terminal by accident — the projector's scan skipped it and
nothing ever retried it (the ES-050 deferral). Those records represent
derivations the platform still owes, so the migration returns them to the
working set; their ``attempts`` counter is preserved, so a record that has
already burned its budget dead-letters on its next failure rather than looping.
The terminal ``'dead_letter'`` status itself needs no migration — outbox states
are stored as plain text (no database enum type).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memory_outbox",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Return never-retried failures to the working set (see module docstring).
    op.execute(
        "UPDATE memory_outbox SET status = 'pending' WHERE status = 'failed'"
    )


def downgrade() -> None:
    # Dead-lettered records become plain failures again — the pre-ES-067
    # vocabulary, where a failure was terminal for the scan.
    op.execute(
        "UPDATE memory_outbox SET status = 'failed' WHERE status = 'dead_letter'"
    )
    op.drop_column("memory_outbox", "next_attempt_at")
