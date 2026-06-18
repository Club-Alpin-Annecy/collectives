"""Add user preferences for new event notifications.

Revision ID: 2f4d0f7a9c3b
Revises: 50b732cde535, 96b5a190fc7c, e2b8a6027968
Create Date: 2026-02-16 21:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2f4d0f7a9c3b"
down_revision = ("50b732cde535", "96b5a190fc7c", "e2b8a6027968")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "new_event_notification_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "new_event_notification_weekdays", sa.String(length=32), nullable=True
            )
        )

    op.create_table(
        "user_notification_event_types",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["event_type_id"], ["event_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "event_type_id"),
    )
    op.create_index(
        op.f("ix_user_notification_event_types_user_id"),
        "user_notification_event_types",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_notification_event_types_event_type_id"),
        "user_notification_event_types",
        ["event_type_id"],
        unique=False,
    )

    op.create_table(
        "user_notification_activity_types",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["activity_type_id"], ["activity_types.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "activity_type_id"),
    )
    op.create_index(
        op.f("ix_user_notification_activity_types_user_id"),
        "user_notification_activity_types",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_notification_activity_types_activity_type_id"),
        "user_notification_activity_types",
        ["activity_type_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_user_notification_activity_types_activity_type_id"),
        table_name="user_notification_activity_types",
    )
    op.drop_index(
        op.f("ix_user_notification_activity_types_user_id"),
        table_name="user_notification_activity_types",
    )
    op.drop_table("user_notification_activity_types")

    op.drop_index(
        op.f("ix_user_notification_event_types_event_type_id"),
        table_name="user_notification_event_types",
    )
    op.drop_index(
        op.f("ix_user_notification_event_types_user_id"),
        table_name="user_notification_event_types",
    )
    op.drop_table("user_notification_event_types")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("new_event_notification_weekdays")
        batch_op.drop_column("new_event_notification_enabled")
