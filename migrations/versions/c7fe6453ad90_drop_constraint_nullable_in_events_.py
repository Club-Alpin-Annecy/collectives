"""Drop constraint nullable in events.registration_open_time

Revision ID: c7fe6453ad90
Revises: afe864919723
Create Date: 2020-01-07 17:54:46.105665

"""
from alembic import op
import sqlalchemy as sa

from collectives.models import db


# revision identifiers, used by Alembic.
revision = 'c7fe6453ad90'
down_revision = 'afe864919723'
branch_labels = None
depends_on = None


def upgrade():
    # Change events.registration_open_time 'nullable' False to True
    with op.batch_alter_table('events') as batch_op:
        batch_op.alter_column('registration_open_time', nullable=True, existing_type = sa.DateTime)
        batch_op.alter_column('registration_close_time', nullable=True, existing_type = sa.DateTime)


def downgrade():
    with op.batch_alter_table('events') as batch_op:
        batch_op.alter_column('registration_open_time', nullable=False, existing_type = sa.DateTime)
        batch_op.alter_column('registration_close_time', nullable=False, existing_type = sa.DateTime)
    pass
