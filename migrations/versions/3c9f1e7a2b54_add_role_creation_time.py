"""Add role creation time

Revision ID: 3c9f1e7a2b54
Revises: bd8854e3b409
Create Date: 2026-10-09 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c9f1e7a2b54"
down_revision = "bd8854e3b409"
branch_labels = None
depends_on = None


def upgrade():
    # Existing roles are left with a null creation time: their actual
    # creation date is unknown.
    op.add_column("roles", sa.Column("creation_time", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("roles", "creation_time")
