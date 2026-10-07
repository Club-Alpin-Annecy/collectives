"""Unit tests for database initialisation from configuration"""

from collectives.models import ActivityKind, ActivityType, EventType, db
from collectives.utils import init


def test_obsolete_event_type_in_use_is_kept(app, event1):
    """An event type removed from config must not be deleted while events use it"""
    event_type_id = event1.event_type_id
    unused_type_id = next(
        tid for tid in app.config["EVENT_TYPES"] if tid != event_type_id
    )

    event_types = dict(app.config["EVENT_TYPES"])
    del event_types[event_type_id]
    del event_types[unused_type_id]
    app.config["EVENT_TYPES"] = event_types

    init.event_types(app)

    assert db.session.get(EventType, event_type_id) is not None
    assert db.session.get(EventType, unused_type_id) is None
    assert event1.event_type is not None


def test_activity_kind_from_config(app):
    """ACTIVITY_TYPES may set the kind of an activity, Regular by default"""
    activity_types = {
        tid: dict(atype) for tid, atype in app.config["ACTIVITY_TYPES"].items()
    }
    first_id, second_id = list(activity_types)[:2]
    activity_types[first_id]["kind"] = "Initiative"
    app.config["ACTIVITY_TYPES"] = activity_types

    init.activity_types(app)

    first = ActivityType.query.filter_by(short=activity_types[first_id]["short"]).one()
    second = ActivityType.query.filter_by(
        short=activity_types[second_id]["short"]
    ).one()
    assert first.kind == ActivityKind.Initiative
    assert second.kind == ActivityKind.Regular
