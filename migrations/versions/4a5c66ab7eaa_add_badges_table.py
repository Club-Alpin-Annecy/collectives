"""empty message

Revision ID: 4a5c66ab7eaa
Revises: 92a84e14f157
Create Date: 2023-06-28 10:08:21.474761

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4a5c66ab7eaa"
down_revision = "92a84e14f157"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("badge_id", sa.Enum("Benevole", name="badgeids"), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activity_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("badges", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_badges_activity_id"), ["activity_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_badges_user_id"), ["user_id"], unique=False
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    with op.batch_alter_table("badges", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_badges_user_id"))
        batch_op.drop_index(batch_op.f("ix_badges_activity_id"))

    op.drop_table("badges")
    # ### end Alembic commands ###
