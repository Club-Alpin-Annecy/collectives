""" Unit tests for registrations"""

import pytest
from collectives.models import db, RegistrationStatus, Registration, RegistrationLevels
from collectives.models.event import (
    Event,
    DuplicateRegistrationError,
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
