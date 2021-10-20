"""Extend trigram field length to 8 characters

Revision ID: cd130569fb5a
Revises: c4182cd3ef20
Create Date: 2020-12-15 21:00:16.891149

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd130569fb5a'
down_revision = 'c4182cd3ef20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("activity_types", schema=None) as batch_op:
        batch_op.alter_column(
            "trigram",
            type_=sa.String(8),
            existing_type_=sa.String(3),
        )


def downgrade():
    with op.batch_alter_table("activity_types", schema=None) as batch_op:
        batch_op.alter_column(
            "trigram",
            type_=sa.String(3),
            existing_type_=sa.String(8),
        )
