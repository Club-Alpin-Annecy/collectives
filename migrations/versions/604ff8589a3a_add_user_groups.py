"""Add UserGrpup and related tables

Revision ID: 604ff8589a3a
Revises: 701afd89fc19
Create Date: 2022-11-13 21:13:05.010246

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "604ff8589a3a"
down_revision = "701afd89fc19"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "group_event_conditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("is_leader", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["activity_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["user_groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_group_event_conditions_group_id"),
        "group_event_conditions",
        ["group_id"],
        unique=False,
    )
    op.create_table(
        "group_license_conditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("license_category", sa.String(length=2), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["user_groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_group_license_conditions_group_id"),
        "group_license_conditions",
        ["group_id"],
        unique=False,
    )
    op.create_table(
        "group_role_conditions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column(
            "role_id",
            sa.Enum(
                "Moderator",
                "Administrator",
                "President",
                "Technician",
                "Hotline",
                "Accountant",
                "Staff",
                "EventLeader",
                "ActivitySupervisor",
                "Trainee",
                "EquipmentManager",
                "EquipmentVolunteer",
                name="roleids",
            ),
            nullable=True,
        ),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activity_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["user_groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_group_role_conditions_group_id"),
        "group_role_conditions",
        ["group_id"],
        unique=False,
    )

    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("user_group_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fkey_user_group_id", "user_groups", ["user_group_id"], ["id"]
        )

    with op.batch_alter_table("item_prices") as batch_op:
        batch_op.add_column(sa.Column("user_group_id", sa.Integer(), nullable=True))

        batch_op.alter_column("leader_only", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key(
            "fkey_ip_user_group_id", "user_groups", ["user_group_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("item_prices") as batch_op:
        batch_op.drop_constraint("fkey_ip_user_group_id", type_="foreignkey")
        batch_op.alter_column("leader_only", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("user_group_id")

    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_constraint("fkey_user_group_id", type_="foreignkey")
        batch_op.drop_column("user_group_id")
        pass

    op.drop_table("group_role_conditions")
    op.drop_table("group_license_conditions")
    op.drop_table("group_event_conditions")
    op.drop_table("user_groups")
