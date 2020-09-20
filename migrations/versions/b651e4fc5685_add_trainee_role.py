"""Add Trainee role

Revision ID: b651e4fc5685
Revises: b8e4572a4af9
Create Date: 2020-09-20 19:03:50.504567

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b651e4fc5685'
down_revision = 'b8e4572a4af9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.alter_column(
            "role_id",
            type_=sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "EventLeader",
                "ActivitySupervisor",
                "Technician",
                "Trainee",
                name="roleids",
            ),
            existing_type_=sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "EventLeader",
                "ActivitySupervisor",
                "Technician",
                name="roleids",
            ),
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.alter_column(
            "role_id",
            existing_type=sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "EventLeader",
                "ActivitySupervisor",
                "Technician",
                "Trainee",
                name="roleids",
            ),
            type_=sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "EventLeader",
                "ActivitySupervisor",
                "Technician",
                name="roleids",
            ),
        )
    # ### end Alembic commands ###
