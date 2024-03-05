"""Add EquipmentType.last_reference

Revision ID: 800a231d8e8e
Revises: 01a7e5bb3506
Create Date: 2022-03-09 17:06:23.442104

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "800a231d8e8e"
down_revision = "01a7e5bb3506"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("equipment_types") as batch_op:
        batch_op.add_column(
            sa.Column("last_reference", sa.Integer(), default=0),
        )
        batch_op.create_unique_constraint("UK_last_reference", ["last_reference"])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("equipment_types") as batch_op:
        batch_op.drop_constraint("UK_last_reference", type_="unique")
        batch_op.drop_column("last_reference")
    # ### end Alembic commands ###
