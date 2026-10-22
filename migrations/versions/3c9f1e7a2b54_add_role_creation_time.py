"""Add role creation time

Revision ID: 3c9f1e7a2b54
Revises: 420c243a17f8
Create Date: 2026-10-09 16:00:00.000000

"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c9f1e7a2b54"
down_revision = "420c243a17f8"
branch_labels = None
depends_on = None


roles = sa.table(
    "roles",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.Integer),
    sa.column("activity_id", sa.Integer),
    sa.column("creation_time", sa.DateTime),
)
events = sa.table(
    "events", sa.column("id", sa.Integer), sa.column("start", sa.DateTime)
)
event_leaders = sa.table(
    "event_leaders", sa.column("user_id", sa.Integer), sa.column("event_id", sa.Integer)
)
event_activity_types = sa.table(
    "event_activity_types",
    sa.column("activity_id", sa.Integer),
    sa.column("event_id", sa.Integer),
)
registrations = sa.table(
    "registrations",
    sa.column("user_id", sa.Integer),
    sa.column("event_id", sa.Integer),
    sa.column("level", sa.String),
    sa.column("status", sa.String),
)


def season_start(start: datetime) -> datetime:
    """:return: the 1st of September starting the season of ``start``"""
    year = start.year if start.month >= 9 else start.year - 1
    return datetime(year, 9, 1)


def first_led_events(connection, before: datetime) -> dict:
    """:return: the start of the first led or co-led event which started before
    ``before``, per (user, activity)"""
    led = (
        sa.select(
            event_leaders.c.user_id,
            event_activity_types.c.activity_id,
            sa.func.min(events.c.start),
        )
        .select_from(
            event_leaders.join(events, events.c.id == event_leaders.c.event_id).join(
                event_activity_types, event_activity_types.c.event_id == events.c.id
            )
        )
        .where(events.c.start < before)
        .group_by(event_leaders.c.user_id, event_activity_types.c.activity_id)
    )
    coled = (
        sa.select(
            registrations.c.user_id,
            event_activity_types.c.activity_id,
            sa.func.min(events.c.start),
        )
        .select_from(
            registrations.join(events, events.c.id == registrations.c.event_id).join(
                event_activity_types, event_activity_types.c.event_id == events.c.id
            )
        )
        .where(registrations.c.level == "CoLeader")
        .where(registrations.c.status.in_(("Active", "Present")))
        .where(events.c.start < before)
        .group_by(registrations.c.user_id, event_activity_types.c.activity_id)
    )

    first = {}
    for query in (led, coled):
        for user_id, activity_id, start in connection.execute(query):
            if start is None:
                continue
            if isinstance(start, str):  # SQLite without type information
                start = datetime.fromisoformat(start)
            key = (user_id, activity_id)
            if key not in first or start < first[key]:
                first[key] = start
    return first


def upgrade():
    op.add_column("roles", sa.Column("creation_time", sa.DateTime(), nullable=True))

    # The actual creation date of existing roles is unknown. Estimate it as the
    # start of the season of the first event the user led or co-led in the
    # activity. Upcoming events are ignored, as they would make old roles look
    # recent. Roles of users who never led anything are left null.
    connection = op.get_bind()
    first = first_led_events(connection, before=datetime.now())
    existing_roles = connection.execute(
        sa.select(roles.c.id, roles.c.user_id, roles.c.activity_id).where(
            roles.c.activity_id.isnot(None)
        )
    )
    for role_id, user_id, activity_id in existing_roles.fetchall():
        start = first.get((user_id, activity_id))
        if start is None:
            continue
        connection.execute(
            roles.update()
            .where(roles.c.id == role_id)
            .values(creation_time=season_start(start))
        )


def downgrade():
    op.drop_column("roles", "creation_time")
