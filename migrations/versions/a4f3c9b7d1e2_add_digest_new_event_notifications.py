"""Add digest-based fields for new event notifications.

Revision ID: a4f3c9b7d1e2
Revises: 2f4d0f7a9c3b
Create Date: 2026-03-22 19:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a4f3c9b7d1e2"
down_revision = "2f4d0f7a9c3b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "new_event_notification_frequency",
                sa.Enum("Daily", "Weekly", name="notificationfrequency"),
                nullable=False,
                server_default="Weekly",
            )
        )
        batch_op.add_column(
            sa.Column("last_new_event_notification_sent_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "last_new_event_notification_clicked_at", sa.DateTime(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "new_event_notification_warning_sent_at", sa.DateTime(), nullable=True
            )
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("new_event_notification_warning_sent_at")
        batch_op.drop_column("last_new_event_notification_clicked_at")
        batch_op.drop_column("last_new_event_notification_sent_at")
        batch_op.drop_column("new_event_notification_frequency")
