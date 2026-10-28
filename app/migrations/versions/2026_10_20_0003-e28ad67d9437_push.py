"""Push notifications: device subscriptions and the notification outbox.

Revision ID: e28ad67d9437
Revises: e82b16c1d995
Create Date: 2026-10-20 00:03:50.304934
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e28ad67d9437"
down_revision: str | None = "e82b16c1d995"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=128), nullable=False),
        sa.Column("auth", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_push_subscriptions")),
        sa.UniqueConstraint("endpoint", name=op.f("uq_push_subscriptions_endpoint")),
    )
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lead_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name=op.f("fk_notification_outbox_lead_id_leads"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_outbox")),
    )
    op.create_index(
        "ix_notification_outbox_due",
        "notification_outbox",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_outbox_lead_id"), "notification_outbox", ["lead_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_outbox_lead_id"), table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_due", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_table("push_subscriptions")
