"""Leads table.

Revision ID: a4525eada2fa
Revises:
Create Date: 2026-10-19 22:55:05.096737
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4525eada2fa"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("make", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.Column("asking_price", sa.BigInteger(), nullable=True),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="new", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="direct", nullable=False),
        sa.Column("has_photos", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("preset_id", sa.String(length=64), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index(op.f("ix_leads_created_at"), "leads", ["created_at"], unique=False)
    op.create_index(op.f("ix_leads_status"), "leads", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leads_status"), table_name="leads")
    op.drop_index(op.f("ix_leads_created_at"), table_name="leads")
    op.drop_table("leads")
