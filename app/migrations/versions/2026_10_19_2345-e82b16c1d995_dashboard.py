"""Dashboard: owner login, sessions, notes and the activity log.

Revision ID: e82b16c1d995
Revises: 08b4e6aece7f
Create Date: 2026-10-19 23:45:03.580510
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e82b16c1d995"
down_revision: str | None = "08b4e6aece7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owner_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("env_password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_owner_account")),
    )
    op.create_table(
        "owner_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_owner_sessions")),
    )
    op.create_table(
        "lead_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lead_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_lead_events_lead_id_leads"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lead_events")),
    )
    op.create_index(op.f("ix_lead_events_lead_id"), "lead_events", ["lead_id"], unique=False)
    op.create_table(
        "notes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lead_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_notes_lead_id_leads"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
    )
    op.create_index(op.f("ix_notes_lead_id"), "notes", ["lead_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notes_lead_id"), table_name="notes")
    op.drop_table("notes")
    op.drop_index(op.f("ix_lead_events_lead_id"), table_name="lead_events")
    op.drop_table("lead_events")
    op.drop_table("owner_sessions")
    op.drop_table("owner_account")
