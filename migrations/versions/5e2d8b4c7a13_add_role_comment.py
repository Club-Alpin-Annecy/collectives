"""Add role comment

Revision ID: 5e2d8b4c7a13
Revises: 3c9f1e7a2b54
Create Date: 2026-10-22 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5e2d8b4c7a13"
down_revision = "3c9f1e7a2b54"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("roles", sa.Column("comment", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("roles", "comment")
