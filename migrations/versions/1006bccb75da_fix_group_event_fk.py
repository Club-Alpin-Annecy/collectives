"""Fix foreign key constraint on group_event_conditions

Revision ID: 1006bccb75da
Revises: 604ff8589a3a
Create Date: 2023-01-15 20:58:48.331513

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1006bccb75da"
down_revision = "604ff8589a3a"
branch_labels = None
depends_on = None


def upgrade():

    # Findbad existing FK constraints on event_id
    meta = sa.MetaData()
    table = sa.Table("group_event_conditions", meta, autoload_with=op.get_bind().engine)
    existing_foreign_keys = table.c.event_id.foreign_keys

    with op.batch_alter_table("group_event_conditions") as batch_op:
        for existing_fkey in existing_foreign_keys:
            if existing_fkey.name:
                batch_op.drop_constraint(existing_fkey.name, type_="foreignkey")
        batch_op.create_foreign_key("fk_event_id", "events", ["event_id"], ["id"])


def downgrade():
    with op.batch_alter_table("group_event_conditions") as batch_op:
        batch_op.drop_constraint("fk_event_id", type_="foreignkey")
