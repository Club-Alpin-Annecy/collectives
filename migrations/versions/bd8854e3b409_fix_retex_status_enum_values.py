"""fix retex status enum values

Revision ID: bd8854e3b409
Revises: b7c3e1d94f20
Create Date: 2026-09-29 10:15:07.461286

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bd8854e3b409'
down_revision = 'b7c3e1d94f20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("retex", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "Normale", "Annulee", "Ecourtee", "PresqueAccident", "Accident", name="retexstatus"
            ),
            type_=sa.Enum(
                "Normal", "Cancelled", "Shortened", "NearMissAccident", "Accident", name="retexstatus"
            ),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("retex", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "Normal", "Cancelled", "Shortened", "NearMissAccident", "Accident", name="retexstatus"
            ),
            type_=sa.Enum(
                "Normale", "Annulee", "Ecourtee", "PresqueAccident", "Accident", name="retexstatus"
            ),
            existing_nullable=False,
        )
