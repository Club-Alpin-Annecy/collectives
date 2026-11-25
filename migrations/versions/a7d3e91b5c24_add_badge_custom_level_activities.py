"""add the selection of activities of a custom badge level

Revision ID: a7d3e91b5c24
Revises: 4f6c2a9d1e73
Create Date: 2026-11-25 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7d3e91b5c24"
down_revision = "4f6c2a9d1e73"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "badge_custom_level_activities",
        sa.Column("custom_level_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["custom_level_id"], ["badge_custom_levels.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"], ["activity_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("custom_level_id", "activity_id"),
    )


def downgrade():
    op.drop_table("badge_custom_level_activities")
