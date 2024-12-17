"""Add activity staff role to user groups

Revision ID: a11e6d8d8dd2
Revises: 75ca2437615d
Create Date: 2024-12-17 12:20:56.205689

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a11e6d8d8dd2"
down_revision = "75ca2437615d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("group_role_conditions", schema=None) as batch_op:
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
                "Hotline",
                "Accountant",
                "Staff",
                "EquipmentManager",
                "EquipmentVolunteer",
                "ActivityStaff",
                name="roleids",
            ),
            existing_type_=sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "EventLeader",
                "ActivitySupervisor",
                "Technician",
                "Trainee",
                "Hotline",
                "Accountant",
                "Staff",
                "EquipmentManager",
                "EquipmentVolunteer",
                name="roleids",
            ),
        )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("group_role_conditions", schema=None) as batch_op:
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
                "Hotline",
                "Accountant",
                "Staff",
                "EquipmentManager",
                "EquipmentVolunteer",
                name="roleids",
            ),
            existing_type_=sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "EventLeader",
                "ActivitySupervisor",
                "Technician",
                "Trainee",
                "Hotline",
                "Accountant",
                "Staff",
                "EquipmentManager",
                "EquipmentVolunteer",
                "ActivityStaff",
                name="roleids",
            ),
        )
    # ### end Alembic commands ###
