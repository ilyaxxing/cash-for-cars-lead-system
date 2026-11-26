"""Owner-created QR placements."""

import sqlalchemy as sa
from alembic import op

revision = "87d1b2ea09cc"
down_revision = "e28ad67d9437"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "placements",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
    )


def downgrade() -> None:
    op.drop_table("placements")
