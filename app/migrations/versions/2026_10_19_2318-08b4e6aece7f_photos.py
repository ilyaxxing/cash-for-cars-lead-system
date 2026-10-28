"""Photos table: object keys of car photos stored in the bucket.

Revision ID: 08b4e6aece7f
Revises: a4525eada2fa
Create Date: 2026-10-19 23:18:38.635754
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "08b4e6aece7f"
down_revision: str | None = "a4525eada2fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "photos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lead_id", sa.BigInteger(), nullable=False),
        sa.Column("slot", sa.String(length=64), nullable=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("thumb_key", sa.String(length=255), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], name=op.f("fk_photos_lead_id_leads"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_photos")),
        sa.UniqueConstraint("lead_id", "slot", name=op.f("uq_photos_lead_id")),
    )
    op.create_index(op.f("ix_photos_lead_id"), "photos", ["lead_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_photos_lead_id"), table_name="photos")
    op.drop_table("photos")
