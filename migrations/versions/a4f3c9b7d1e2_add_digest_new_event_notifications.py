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

    op.create_table(
        "new_event_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_new_event_notifications_created_at"),
        "new_event_notifications",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_new_event_notifications_event_id"),
        "new_event_notifications",
        ["event_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_new_event_notifications_event_id"),
        table_name="new_event_notifications",
    )
    op.drop_index(
        op.f("ix_new_event_notifications_created_at"),
        table_name="new_event_notifications",
    )
    op.drop_table("new_event_notifications")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("new_event_notification_warning_sent_at")
        batch_op.drop_column("last_new_event_notification_clicked_at")
        batch_op.drop_column("last_new_event_notification_sent_at")
        batch_op.drop_column("new_event_notification_frequency")

    sa.Enum("Daily", "Weekly", name="notificationfrequency").drop(
        op.get_bind(), checkfirst=False
    )
