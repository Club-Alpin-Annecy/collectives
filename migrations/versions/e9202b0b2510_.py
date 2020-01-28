"""Add status column to events

Revision ID: e9202b0b2510
Revises: 20e75469b22b
Create Date: 2020-01-01 20:18:16.524387

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9202b0b2510'
down_revision = '20e75469b22b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('events', sa.Column('status', sa.Integer(), nullable=False, server_default='0'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('events', 'status')
    # ### end Alembic commands ###
