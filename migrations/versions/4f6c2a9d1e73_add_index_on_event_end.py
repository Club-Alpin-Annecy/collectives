"""Add index on events.end

The event list filters on the end date to hide past events. Without an index,
the database scans the whole table from the very first event.

Revision ID: 4f6c2a9d1e73
Revises: bd8854e3b409
Create Date: 2026-10-11 21:20:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "4f6c2a9d1e73"
down_revision = "bd8854e3b409"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_events_end"), ["end"], unique=False)


def downgrade():
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_events_end"))
