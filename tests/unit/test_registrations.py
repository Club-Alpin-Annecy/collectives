""" Unit tests for registrations"""

from collectives.models import db, RegistrationStatus, Registration, RegistrationLevels


def test_overflow(user1, user2, user3, user4, event):
    """Test an auto registration to a full event without waiting list"""

    event.num_waiting_slots = 1
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

    event.registrations.append(reg1)
    event.registrations.append(reg2)
    event.registrations.append(reg3)
    event.registrations.append(reg4)

    db.session.add(event)
    db.session.commit()

    assert reg1.is_overbooked() == False
    assert reg2.is_overbooked() == True
    assert reg3.is_overbooked() == False
    assert reg4.is_overbooked() == True
