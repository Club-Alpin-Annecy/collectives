"""add loxya user id

Records the Loxya login account of a member, when the LOXYA_CREATE_ACCOUNTS
option gives them one. See :py:mod:`collectives.utils.loxya_sync`.

Revision ID: d5f9b2a6e3c8
Revises: c4e8a1f5d2b7
Create Date: 2026-10-11 12:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d5f9b2a6e3c8"
down_revision = "c4e8a1f5d2b7"
branch_labels = None
depends_on = None


def upgrade():
    """Adds the column holding the Loxya login account of a user."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("loxya_user_id", sa.Integer(), nullable=True))


def downgrade():
    """Removes it; the accounts stay on Loxya, untouched."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("loxya_user_id")
