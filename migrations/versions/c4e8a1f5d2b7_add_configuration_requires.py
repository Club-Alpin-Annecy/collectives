"""add requires to configuration items

Lets a configuration item depend on an application setting: the item is only
shown and editable while that setting is on. Used to keep the settings of an
optional feature, such as the Loxya integration, out of sight of the clubs that
do not enable it.

Revision ID: c4e8a1f5d2b7
Revises: 7babe0b3cfa2
Create Date: 2026-09-28 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4e8a1f5d2b7"
down_revision = "7babe0b3cfa2"
branch_labels = None
depends_on = None


def upgrade():
    """Adds the requires column to the configuration table."""
    with op.batch_alter_table("config", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requires", sa.Text(), nullable=True))


def downgrade():
    """Removes the requires column; every item becomes visible again."""
    with op.batch_alter_table("config", schema=None) as batch_op:
        batch_op.drop_column("requires")
