"""remove equipment rental feature

Drops the equipment/reservation tables and the associated roles: the rental
feature was never used in production and its code has been removed.

Revision ID: b7c3e1d94f20
Revises: dfadf58f0fac
Create Date: 2026-09-08 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c3e1d94f20"
down_revision = "dfadf58f0fac"
branch_labels = None
depends_on = None

EQUIPMENT_ROLES = ("EquipmentManager", "EquipmentVolunteer")
""" Names of the removed equipment rental roles, as stored in the enum columns. """

ROLE_TABLES = ("roles", "group_role_conditions")
""" Tables holding a `role_id` column typed with the `roleids` enum. """

REMAINING_ROLES = (
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
    "ActivityStaff",
)
""" Role names left in the `roleids` enum once the equipment roles are gone. """

PREVIOUS_ROLES = (*REMAINING_ROLES, *EQUIPMENT_ROLES)
""" Role names the `roleids` enum held before this revision. """


def _alter_role_enum(from_values, to_values):
    """Retype the `role_id` column of every role table.

    :param from_values: role names currently allowed by the enum
    :param to_values: role names to allow instead
    """
    for table in ROLE_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column(
                "role_id",
                type_=sa.Enum(*to_values, name="roleids"),
                existing_type=sa.Enum(*from_values, name="roleids"),
            )


def upgrade():
    # Roles are dropped before the enum is retyped, otherwise the remaining
    # rows would hold a value the column no longer accepts. `role_id` stores
    # the enum *name*, not the numeric RoleIds value.
    for table in ROLE_TABLES:
        op.execute(
            sa.text(f"DELETE FROM {table} WHERE role_id IN :names").bindparams(
                sa.bindparam("names", EQUIPMENT_ROLES, expanding=True)
            )
        )
    _alter_role_enum(PREVIOUS_ROLES, REMAINING_ROLES)

    op.drop_table("reservation_lines_equipments")
    op.drop_table("reservation_lines")
    op.drop_table("reservations")
    op.drop_table("equipments")
    op.drop_table("equipment_models")
    op.drop_table("equipment_types")


def downgrade():
    _alter_role_enum(REMAINING_ROLES, PREVIOUS_ROLES)

    op.create_table(
        "equipment_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_reference", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("reference_prefix", sa.String(length=10), nullable=False),
        sa.Column("path_img", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("deposit", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_prefix", name="UK_types_ref_prefix"),
    )
    op.create_table(
        "equipment_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("manufacturer", sa.String(length=50), nullable=True),
        sa.Column("equipment_type_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "equipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=False),
        sa.Column("purchase_date", sa.DateTime(), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("serial_number", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "Available",
                "Rented",
                "Unavailable",
                "InReview",
                name="equipmentstatus",
            ),
            nullable=False,
        ),
        sa.Column("equipment_model_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_model_id"], ["equipment_models.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    with op.batch_alter_table("equipments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_equipments_purchaseDate", ["purchase_date"], unique=False
        )

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collect_date", sa.DateTime(), nullable=False),
        sa.Column("return_date", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "Planned",
                "Ongoing",
                "Completed",
                "Cancelled",
                name="reservationstatus",
            ),
            nullable=False,
        ),
        sa.Column("extended", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("reservations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reservations_collect_date"), ["collect_date"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_reservations_return_date"), ["return_date"], unique=False
        )

    op.create_table(
        "reservation_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("equipment_type_id", sa.Integer(), nullable=True),
        sa.Column("reservation_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_types.id"]),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reservation_lines_equipments",
        sa.Column("reservation_line_id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipments.id"]),
        sa.ForeignKeyConstraint(["reservation_line_id"], ["reservation_lines.id"]),
        sa.PrimaryKeyConstraint("reservation_line_id", "equipment_id"),
    )
    # Deleted equipment role assignments are not restored: their data is gone.
