"""Unit tests for registrations"""

import pytest

from collectives.models import Registration, RegistrationLevels, RegistrationStatus, db
from collectives.models.event import (
    DuplicateRegistrationError,
    Event,
    OverbookedRegistrationError,
)


def test_overflow(user1, user2, user3, user4, event: Event):
    """Test an auto registration to a full event without waiting list"""

    event.num_waiting_list = 1
    event.num_slots = 1
    db.session.add(event)
    db.session.commit()

    reg1 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg2 = Registration(
        user_id=user2.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg3 = Registration(
        user_id=user3.id,
        status=RegistrationStatus.Waiting,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg4 = Registration(
        user_id=user4.id,
        status=RegistrationStatus.Waiting,
        level=RegistrationLevels.Normal,
        is_self=True,
    )

    event.add_registration_check_race_conditions(reg1)
    with pytest.raises(OverbookedRegistrationError):
        event.add_registration_check_race_conditions(reg2)
    event.add_registration_check_race_conditions(reg3)
    with pytest.raises(OverbookedRegistrationError):
        event.add_registration_check_race_conditions(reg4)

    assert len(event.registrations) == 2
    assert (event.registrations[0]) == reg1
    assert (event.registrations[1]) == reg3


def test_overflow_with_leaders_in_counts(user1, user2, user3, event: Event):
    """Leaders included in the counts take slots: a registration committed
    at the same time as another one must not go over the maximum."""

    num_leaders = len(event.leaders)
    assert num_leaders > 0
    event.include_leaders_in_counts = True
    event.num_slots = num_leaders + 1
    event.num_online_slots = num_leaders + 1
    event.num_waiting_list = 1
    db.session.add(event)
    db.session.commit()

    def registration(user, status):
        return Registration(
            user_id=user.id,
            status=status,
            level=RegistrationLevels.Normal,
            is_self=True,
        )

    reg1 = registration(user1, RegistrationStatus.Active)
    reg2 = registration(user2, RegistrationStatus.Active)
    reg3 = registration(user3, RegistrationStatus.Waiting)

    event.add_registration_check_race_conditions(reg1)
    with pytest.raises(OverbookedRegistrationError):
        event.add_registration_check_race_conditions(reg2)
    assert event.num_taken_slots() == event.num_slots

    # The waiting list is not affected by the leaders
    event.add_registration_check_race_conditions(reg3)
    assert event.registrations == [reg1, reg3]

    # Leaders left out of the counts: the slot they took is free again
    event.include_leaders_in_counts = False
    event.num_slots = 2
    event.num_online_slots = 2
    db.session.commit()
    reg4 = registration(user2, RegistrationStatus.Active)
    event.add_registration_check_race_conditions(reg4)
    assert event.num_taken_slots() == 2


def test_overflow_online_slots_count_leader_registrations(
    user1, user2, user3, event: Event
):
    """Registrations made by a leader take online slots too: a self-registration
    committed once they fill the online slots must be refused, as
    Event.has_free_online_slots() would have refused it beforehand."""

    event.num_slots = 3
    event.num_online_slots = 1
    db.session.add(event)
    db.session.commit()

    def registration(user, is_self):
        return Registration(
            user_id=user.id,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal,
            is_self=is_self,
        )

    event.add_registration_check_race_conditions(registration(user1, False))
    assert not event.has_free_online_slots()

    with pytest.raises(OverbookedRegistrationError):
        event.add_registration_check_race_conditions(registration(user2, True))

    # A leader can still register someone up to the total number of slots
    event.add_registration_check_race_conditions(registration(user3, False))
    assert event.num_taken_slots() == 2


def test_duplicate(user1, user2, event: Event):
    """Test duplicate resgistration to an event"""

    event.num_online_slots = 2

    db.session.add(event)
    db.session.commit()

    reg1 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg2 = Registration(
        user_id=user2.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg3 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
    )

    event.add_registration_check_race_conditions(reg1)
    event.add_registration_check_race_conditions(reg2)
    with pytest.raises(DuplicateRegistrationError):
        event.add_registration_check_race_conditions(reg3)

    assert len(event.registrations) == 2
    assert (event.registrations[0]) == reg1
    assert (event.registrations[1]) == reg2
