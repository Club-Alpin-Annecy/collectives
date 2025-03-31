"""Add option to include number of leaders in event free slots computation

Revision ID: 9590becba403
Revises: a11e6d8d8dd2
Create Date: 2025-03-29 10:00:26.164423

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9590becba403"
down_revision = "a11e6d8d8dd2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "include_leaders_in_counts",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade():
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_column("include_leaders_in_counts")
