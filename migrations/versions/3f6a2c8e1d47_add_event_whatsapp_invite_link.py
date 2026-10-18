"""add event whatsapp invite link

Revision ID: 3f6a2c8e1d47
Revises: 420c243a17f8
Create Date: 2026-10-12 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f6a2c8e1d47"
down_revision = "420c243a17f8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("whatsapp_invite_link", sa.String(length=255), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_column("whatsapp_invite_link")
