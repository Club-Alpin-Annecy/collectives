"""add a "supersedes" partial order between custom skill levels

Revision ID: c81d4e5f2a90
Revises: 3f6a2c8e1d47
Create Date: 2026-11-21 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c81d4e5f2a90"
down_revision = "3f6a2c8e1d47"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "badge_custom_level_supersedes",
        sa.Column("superior_id", sa.Integer(), nullable=False),
        sa.Column("inferior_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["superior_id"], ["badge_custom_levels.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inferior_id"], ["badge_custom_levels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("superior_id", "inferior_id"),
    )


def downgrade():
    op.drop_table("badge_custom_level_supersedes")
