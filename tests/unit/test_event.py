import unittest
import datetime
from os import environ
from io import StringIO

import flask_testing

# pylint: disable=C0301
from collectives.models import db, ActivityType, Event
from collectives.models import Registration, RegistrationLevels, RegistrationStatus

from tests.fixtures.user import promote_to_leader


def test_event_validity(event1, user1, user2):
    """Test event validity checks"""
    activity1 = ActivityType.query.get(1)
    activity2 = ActivityType.query.get(2)

    promote_to_leader(user1, activity=activity1.name)
    promote_to_leader(user2, activity=activity2.name)

    event = event1
    event.activity_types.clear()
    # Event has no activity, not valid
    assert not event.is_valid()

    # Test leaders
    event.activity_types.append(activity1)
    assert not event.has_valid_leaders()
    event.leaders.append(user1)
    assert event.has_valid_leaders()

    event.activity_types.append(activity2)
    assert not event.has_valid_leaders()
    event.leaders.append(user2)
    assert event.has_valid_leaders()

    assert event.is_valid()

    # Test slots
    event.num_slots = 0
    event.num_online_slots = 1
    assert not event.is_valid()
    event.num_online_slots = 0
    assert event.is_valid()
    event.num_slots = -1
    assert not event.is_valid()
    event.num_slots = 0
    assert event.is_valid()

    # Test dates
    event.end = datetime.datetime.now()
    assert not event.is_valid()
    event.end = event.start
    assert event.is_valid()

    event.num_online_slots = 1
    event.registration_open_time = datetime.datetime.now()
    event.registration_close_time = datetime.datetime.now() + datetime.timedelta(days=1)

    assert event.is_registration_open_at_time(datetime.datetime.now())

    event.registration_open_time = event.registration_close_time + datetime.timedelta(
        hours=1
    )
    assert not event.opens_before_closes()
    assert not event.is_valid()

    event.registration_open_time = datetime.datetime.combine(
        event.end, datetime.datetime.min.time()
    ) + datetime.timedelta(days=1)
    event.registration_close_time = event.registration_open_time + datetime.timedelta(
        hours=1
    )
    assert event.opens_before_closes()
    assert not event.opens_before_ends()
    assert not event.is_valid()

    assert not event.is_registration_open_at_time(datetime.datetime.now())


def test_add_registration(event1, user1, user2):
    """Test registering users to an event"""

    def make_registration(user):
        """Utility func to create a registration for the given user"""
        datetime.datetime.timestamp(datetime.datetime.now())
        return Registration(
            user=user, status=RegistrationStatus.Active, level=RegistrationLevels.Normal
        )

    event = event1
    event.num_online_slots = 2
    event.registration_open_time = datetime.datetime.now()
    event.registration_close_time = datetime.datetime.now() + datetime.timedelta(days=1)

    db.session.add(event)
    db.session.commit()

    now = datetime.datetime.now()
    assert event.is_registration_open_at_time(now)
    assert event.has_free_online_slots()

    assert event.can_self_register(user1, now)
    assert event.can_self_register(user2, now)

    event.registrations.append(make_registration(user1))
    db.session.commit()
    assert not event.can_self_register(user1, now)
    assert event.can_self_register(user2, now)

    event.num_online_slots = 1

    assert not event.has_free_online_slots()
    assert not event.can_self_register(user2, now)

    event.registrations[0].status = RegistrationStatus.Rejected
    assert event.has_free_online_slots()
    assert not event.can_self_register(user1, now)
    assert event.can_self_register(user2, now)

    db.session.commit()

    # Test db has been updated
    db_event = Event.query.filter_by(id=event.id).first()
    assert db_event.has_free_online_slots()
    assert not db_event.can_self_register(user1, now)
    assert db_event.can_self_register(user2, now)
