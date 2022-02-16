"""Add Refunded to PaymentStatus. Rename creditor->buyer

Revision ID: 88f73f88cb1b
Revises: 5a9ba75de4d1
Create Date: 2020-10-25 20:29:27.943230

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "88f73f88cb1b"
down_revision = "9e57d5a69575"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        # SQLite won't uodate the index automatically when renaming the column
        # MySQL will but won't allow us to drop the index
        op.drop_index(op.f("ix_payments_creditor_id"), "payments")

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            type_=sa.Enum(
                "Initiated",
                "Approved",
                "Cancelled",
                "Refused",
                "Expired",
                "Refunded",
                name="paymentstatus",
            ),
            existing_type=sa.Enum(
                "Initiated",
                "Approved",
                "Cancelled",
                "Refused",
                "Expired",
                name="paymentstatus",
            ),
        )
        batch_op.alter_column(
            "creditor_id", new_column_name="buyer_id", existing_type=sa.Integer
        )

    if bind.engine.name == "sqlite":
        op.create_index(
            op.f("ix_payments_creditor_id"), "payments", ["buyer_id"], unique=False
        )


def downgrade():

    bind = op.get_bind()
    if bind.engine.name == "sqlite":
        op.drop_index(op.f("ix_payments_creditor_id"), "payments")

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            type_=sa.Enum(
                "Initiated",
                "Approved",
                "Cancelled",
                "Refused",
                "Expired",
                name="paymentstatus",
            ),
            existing_type=sa.Enum(
                "Initiated",
                "Approved",
                "Cancelled",
                "Refused",
                "Expired",
                "Refunded",
                name="paymentstatus",
            ),
        )
        batch_op.alter_column(
            "buyer_id", new_column_name="creditor_id", existing_type=sa.Integer
        )

    if bind.engine.name == "sqlite":
        op.create_index(
            op.f("ix_payments_creditor_id"), "payments", ["creditor_id"], unique=False
        )
    # ### end Alembic commands ###
