"""use the club's five retex levels

Replaces the retex statuses with the five levels defined by the club's
prevention team: Cancelled (0), GoodPractice (1), NearMiss (2), Incident (3)
and Accident (4).

Existing rows are converted as follows: Normal and Shortened become
GoodPractice, NearMissAccident becomes NearMiss. Cancelled and Accident keep
their name.

Revision ID: a4d2f7c9e130
Revises: 7babe0b3cfa2
Create Date: 2026-11-13 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a4d2f7c9e130"
down_revision = "7babe0b3cfa2"
branch_labels = None
depends_on = None

OLD_VALUES = ("Normal", "Cancelled", "Shortened", "NearMissAccident", "Accident")
NEW_VALUES = ("Cancelled", "GoodPractice", "NearMiss", "Incident", "Accident")
ALL_VALUES = tuple(dict.fromkeys(OLD_VALUES + NEW_VALUES))

UPGRADE_RENAMES = {
    "Normal": "GoodPractice",
    "Shortened": "GoodPractice",
    "NearMissAccident": "NearMiss",
}
DOWNGRADE_RENAMES = {
    "GoodPractice": "Normal",
    "NearMiss": "NearMissAccident",
    "Incident": "Shortened",
}


def _set_enum(from_values, to_values):
    """Change the set of values accepted by the retex status column."""
    with op.batch_alter_table("retex", schema=None) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(*from_values, name="retexstatus"),
            type_=sa.Enum(*to_values, name="retexstatus"),
            existing_nullable=False,
        )


def _rename(renames):
    """Rename the status of existing retex rows."""
    retex = sa.table("retex", sa.column("status", sa.String))
    for old, new in renames.items():
        op.execute(retex.update().where(retex.c.status == old).values(status=new))


def upgrade():
    _set_enum(OLD_VALUES, ALL_VALUES)
    _rename(UPGRADE_RENAMES)
    _set_enum(ALL_VALUES, NEW_VALUES)


def downgrade():
    _set_enum(NEW_VALUES, ALL_VALUES)
    _rename(DOWNGRADE_RENAMES)
    _set_enum(ALL_VALUES, OLD_VALUES)
