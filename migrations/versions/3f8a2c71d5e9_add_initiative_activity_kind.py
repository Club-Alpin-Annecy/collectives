"""Add Initiative activity kind

Revision ID: 3f8a2c71d5e9
Revises: bd8854e3b409
Create Date: 2026-09-28 13:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3f8a2c71d5e9"
down_revision = "bd8854e3b409"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("activity_types", schema=None) as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum("Regular", "Service", name="activitykind"),
            type_=sa.Enum("Regular", "Service", "Initiative", name="activitykind"),
            existing_nullable=False,
            existing_server_default="Regular",
        )


def downgrade():
    op.execute(
        "UPDATE activity_types SET kind = 'Service' WHERE kind = 'Initiative'"
    )

    with op.batch_alter_table("activity_types", schema=None) as batch_op:
        batch_op.alter_column(
            "kind",
            existing_type=sa.Enum(
                "Regular", "Service", "Initiative", name="activitykind"
            ),
            type_=sa.Enum("Regular", "Service", name="activitykind"),
            existing_nullable=False,
            existing_server_default="Regular",
        )
