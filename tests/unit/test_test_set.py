"""Regression tests for the test dataset generator (etc/test_set.py)"""

from collectives.models import ActivityKind, ActivityType, db
from etc import test_set


def test_event_activities_exclude_services_and_deprecated(app):
    """Generated events must only use non-deprecated, non-service activities

    Regression test (TEST1): `get_event_activities` used to pass an
    `include_services` keyword to `ActivityType.get_all_types()`, which its
    signature does not accept, crashing the dataset generator with a
    TypeError before any data was created.
    """
    # The seeded activities are all regular; turn one into a service so
    # the filter is actually exercised.
    service_activity = ActivityType.query.filter_by(deprecated=False).first()
    service_activity.kind = ActivityKind.Service
    db.session.add(service_activity)

    activities = test_set.get_event_activities()

    assert activities
    assert ActivityKind.Service not in {activity.kind for activity in activities}
    assert all(not activity.deprecated for activity in activities)
    assert service_activity not in activities
