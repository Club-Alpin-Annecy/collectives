"""Unit tests for Event class"""

import datetime

# pylint: disable=C0301
from collectives.models import db, ActivityType, Event, User, RoleIds, ItemPrice
from collectives.models import Registration, RegistrationLevels, RegistrationStatus

from collectives.models.user_group import UserGroup, GroupRoleCondition

from collectives.routes.event import update_waiting_list
from collectives.utils.time import current_time

from tests.fixtures.user import promote_to_leader


def test_event_validity(event1, user1, user2):
    """Test event validity checks"""
    activity1 = db.session.get(ActivityType, 1)
    activity2 = db.session.get(ActivityType, 2)

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
    event.end = current_time()
    assert not event.is_valid()
    event.end = event.start
    assert event.is_valid()

    event.num_online_slots = 1
    event.registration_open_time = current_time()
    event.registration_close_time = current_time() + datetime.timedelta(days=1)

    assert event.is_registration_open_at_time(current_time())

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

    assert not event.is_registration_open_at_time(current_time())


def test_add_registration(event1, user1, user2):
    """Test registering users to an event"""

    def make_registration(user):
        """Utility func to create a registration for the given user"""
        datetime.datetime.timestamp(current_time())
        return Registration(
            user=user, status=RegistrationStatus.Active, level=RegistrationLevels.Normal
        )

    event = event1
    event.num_online_slots = 2
    event.registration_open_time = current_time()
    event.registration_close_time = current_time() + datetime.timedelta(days=1)

    db.session.add(event)
    db.session.commit()

    now = current_time()
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


def test_event_include_leaders_in_counts(event, user1):
    """Test including leaders when counting slots"""
    now = datetime.datetime.now()

    event.num_online_slots = 1
    assert event.num_taken_slots() == 0
    assert event.can_self_register(user1, now)

    event.include_leaders_in_counts = True
    assert event.num_taken_slots() == 1
    assert not event.can_self_register(user1, now)


def test_event_volunteer_duration(event):
    """Test volunteer duration calculation"""
    assert event.volunteer_duration() == 1

    event.end = event.start + datetime.timedelta(hours=1)
    assert event.volunteer_duration() == 0.25

    event.end = event.start + datetime.timedelta(hours=2)
    assert event.volunteer_duration() == 0.25

    event.end = event.start + datetime.timedelta(hours=3)
    assert event.volunteer_duration() == 0.5

    event.end = event.start + datetime.timedelta(hours=4)
    assert event.volunteer_duration() == 0.5

    event.end = event.start + datetime.timedelta(hours=6)
    assert event.volunteer_duration() == 1

    event.end = event.start + datetime.timedelta(days=1)
    assert event.volunteer_duration() == 1

    event.end = event.start + datetime.timedelta(days=1, hours=6)
    assert event.volunteer_duration() == 2


def test_waiting_list_update(event1: Event, event2: Event, user1: User, user2: User):
    """Test waiting list update when users are registered to multiple simultaneaous events"""

    event1.num_online_slots = 1
    event1.num_waiting_list = 2
    event1.registration_open_time = current_time()
    event1.registration_close_time = current_time() + datetime.timedelta(days=1)

    event2.num_online_slots = 1
    event2.num_waiting_list = 2
    event2.registration_open_time = current_time()
    event2.registration_close_time = current_time() + datetime.timedelta(days=1)

    def make_registration(event, user, status):
        """Utility func to create a registration for the given user"""
        reg = Registration(
            event=event, user=user, status=status, level=RegistrationLevels.Normal
        )
        db.session.add(reg)
        return reg

    reg_u1_e1 = make_registration(event1, user1, RegistrationStatus.Active)
    db.session.commit()

    # Check that user1 cannot register to event2 if Confirmed on event1, but can if waiting
    assert len(user1.registrations_during(event2.start, event2.end, event2.id)) == 1
    reg_u1_e1.status = RegistrationStatus.Waiting
    assert len(user1.registrations_during(event2.start, event2.end, event2.id)) == 0

    # Make user 1 waiting on both events, user 2 waiting on event 1
    reg_u1_e2 = make_registration(event2, user1, RegistrationStatus.Waiting)
    reg_u2_e1 = make_registration(event1, user2, RegistrationStatus.Waiting)
    db.session.commit()

    assert event1.has_free_online_slots()
    # Update waiting list for event 1
    # User 1 should get confirmed and removed from event 2 waiting list
    # User 1 should get confirmed
    update_waiting_list(event1)
    db.session.commit()
    assert len(event1.active_registrations()) == 1
    assert len(event1.registrations) == 2
    assert len(event2.registrations) == 0
    assert reg_u1_e2.status == RegistrationStatus.Waiting
    assert reg_u2_e1.status == RegistrationStatus.Waiting
    assert reg_u1_e1.status == RegistrationStatus.Active

    # Make both users wait on event 2
    reg_u1_e2 = make_registration(event2, user1, RegistrationStatus.Waiting)
    reg_u2_e2 = make_registration(event2, user2, RegistrationStatus.Waiting)
    db.session.commit()

    assert event2.has_free_online_slots()
    # Update waiting list for event 2
    # User 1 should get skipped because already registered to an event
    # User 2 should become confirmed
    update_waiting_list(event2)
    db.session.commit()

    assert len(event2.active_registrations()) == 1
    assert len(event2.registrations) == 2

    assert reg_u1_e2.status == RegistrationStatus.Waiting
    assert reg_u2_e2.status == RegistrationStatus.Active


def test_paying_event_waiting_list_update(
    paying_event: Event, user1: User, president_user: User
):
    """Test waiting list update when users do not have prices available"""

    paying_event.num_online_slots = 1
    paying_event.num_waiting_list = 2
    paying_event.registration_open_time = current_time()
    paying_event.registration_close_time = current_time() + datetime.timedelta(days=1)

    def make_waiting_registration(event, user):
        """Utility func to create a registration for the given user"""
        reg = Registration(
            event=event,
            user=user,
            status=RegistrationStatus.Waiting,
            level=RegistrationLevels.Normal,
        )
        db.session.add(reg)
        return reg

    reg_u1 = make_waiting_registration(paying_event, user1)
    reg_president = make_waiting_registration(paying_event, president_user)
    db.session.commit()

    # User1 was registered first, so should get out of waiting list first
    # However, if the price is only available to the president, user 1 should get skipped
    user_group = UserGroup()
    role_condition = GroupRoleCondition(role_id=RoleIds.President)
    user_group.role_conditions.append(role_condition)
    price: ItemPrice = paying_event.payment_items[0].prices[0]
    price.user_group = user_group
    price.start_date = datetime.date.today()
    price.end_date = datetime.date.today() + datetime.timedelta(days=1)
    db.session.commit()

    update_waiting_list(paying_event)

    assert reg_u1.status == RegistrationStatus.Waiting
    assert reg_president.status == RegistrationStatus.PaymentPending
