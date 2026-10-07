"""Add deprecated flag to event types

Revision ID: a4d7e2c91b05
Revises: 3f8a2c71d5e9
Create Date: 2026-10-07 19:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a4d7e2c91b05"
down_revision = "3f8a2c71d5e9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("event_types", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "deprecated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade():
    with op.batch_alter_table("event_types", schema=None) as batch_op:
        batch_op.drop_column("deprecated")
