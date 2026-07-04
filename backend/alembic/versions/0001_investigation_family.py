"""Baseline: Investigation-family tables (ES-040).

Creates the schema owned by the Investigation Service: investigation,
evidence, finding, report, investigation_outcome and trace_entry. Constraint
names follow the metadata naming convention so this hand-written baseline and
future autogenerate runs stay consistent.

Revision ID: 0001
Revises:
Create Date: 2026-07-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigation",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation")),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("investigation_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("integrity", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigation.id"],
            name=op.f("fk_evidence_investigation_id_investigation"),
        ),
    )
    op.create_index(
        op.f("ix_evidence_investigation_id"),
        "evidence",
        ["investigation_id"],
    )

    op.create_table(
        "finding",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("investigation_id", sa.Text(), nullable=False),
        sa.Column(
            "supporting_evidence", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column("creator", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("related_entities", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "related_relationships", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_finding")),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigation.id"],
            name=op.f("fk_finding_investigation_id_investigation"),
        ),
    )
    op.create_index(
        op.f("ix_finding_investigation_id"),
        "finding",
        ["investigation_id"],
    )

    op.create_table(
        "report",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("investigation_id", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report")),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigation.id"],
            name=op.f("fk_report_investigation_id_investigation"),
        ),
    )
    op.create_index(
        op.f("ix_report_investigation_id"),
        "report",
        ["investigation_id"],
    )

    op.create_table(
        "investigation_outcome",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("investigation_id", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "contributing_findings", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column(
            "detected_conflicts", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column("open_questions", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("report_id", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_outcome")),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigation.id"],
            name=op.f("fk_investigation_outcome_investigation_id_investigation"),
        ),
        sa.UniqueConstraint(
            "investigation_id",
            name=op.f("uq_investigation_outcome_investigation_id"),
        ),
    )

    op.create_table(
        "trace_entry",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column(
            "seq", sa.BigInteger(), sa.Identity(always=True), nullable=False
        ),
        sa.Column("investigation_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trace_entry")),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigation.id"],
            name=op.f("fk_trace_entry_investigation_id_investigation"),
        ),
        sa.UniqueConstraint("seq", name=op.f("uq_trace_entry_seq")),
    )
    op.create_index(
        op.f("ix_trace_entry_investigation_id"),
        "trace_entry",
        ["investigation_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_trace_entry_investigation_id"), table_name="trace_entry")
    op.drop_table("trace_entry")
    op.drop_table("investigation_outcome")
    op.drop_index(op.f("ix_report_investigation_id"), table_name="report")
    op.drop_table("report")
    op.drop_index(op.f("ix_finding_investigation_id"), table_name="finding")
    op.drop_table("finding")
    op.drop_index(op.f("ix_evidence_investigation_id"), table_name="evidence")
    op.drop_table("evidence")
    op.drop_table("investigation")
