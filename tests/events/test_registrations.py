""" Event actions tests related to registrations"""
from datetime import date, timedelta
from collectives.models import db, RegistrationStatus

# pylint: disable=unused-argument


def test_valid_event_autoregistration(user1, user1_client, user2, event):
    """Test user auto registration"""
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 1
    assert len(event.active_registrations()) == 1
    assert len(event.active_normal_registrations()) == 1
    assert len(event.holding_slot_registrations()) == 1
    assert event.num_taken_slots() == 1
    assert event.num_pending_registrations() == 0
    assert event.has_free_slots() == True
    assert event.has_free_online_slots() == False
    assert len(event.existing_registrations(user1_client.user)) == 1
    assert event.is_registered(user1_client.user) == True
    assert event.is_registered(user2) == False
    assert event.num_taken_slots() == 1
    assert event.active_registrations()[0].user == user1


def test_wrong_phone_autoregistration(user1, user1_client, event):
    """Test user auto registration with a user with a wrong phone number"""
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200

    user1.phone = "Not a number"

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 0


def test_wrong_emergency_phone_autoregistration(user1, user1_client, event):
    """Test user auto registration with a user with a wrong phone number"""
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200

    user1.emergency_contact_phone = "Not a number"

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 0


def test_late_event_autoregistration(user1, user1_client, event):
    """Test a too late user auto registration"""

    event.registration_close_time = date.today() - timedelta(days=1)
    db.session.add(event)
    db.session.commit()

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 0


def test_full_event_autoregistration(user1, user1_client, event):
    """Test an auto registration to a full event without waiting list"""

    event.num_online_slots = 0
    db.session.add(event)
    db.session.commit()

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 0


def test_leader_register_user(leader_client, user1, event):
    """Test registration of a user by the leader to a non paying event."""
    response = leader_client.post(
        f"/collectives/{event.id}/register_user", data={"user_id": user1.id}
    )
    assert response.status_code == 302
    assert event.num_taken_slots() == 1
    assert event.is_registered(user1) == True
    assert event.registrations[0].status == RegistrationStatus.Active

    response = leader_client.post(
        f"/collectives/{event.id}/register_user", data={"user_id": user1.id}
    )
    assert response.status_code == 302
    assert event.num_taken_slots() == 1
    assert event.is_registered(user1) == True
    assert event.registrations[0].status == RegistrationStatus.Active


def test_leader_register_paying_user(leader_client, user1, paying_event):
    """Test registration of a user by the leader to a paying event. Registering again an active
    registration should keep it active.
    """
    response = leader_client.post(
        f"/collectives/{paying_event.id}/register_user", data={"user_id": user1.id}
    )
    assert response.status_code == 302
    assert paying_event.num_taken_slots() == 1
    assert paying_event.is_registered(user1) == True
    assert paying_event.registrations[0].status == RegistrationStatus.PaymentPending

    response = leader_client.post(
        f"/collectives/{paying_event.id}/register_user", data={"user_id": user1.id}
    )
    assert response.status_code == 302
    assert paying_event.num_taken_slots() == 1
    assert paying_event.is_registered(user1) == True
    assert paying_event.registrations[0].status == RegistrationStatus.PaymentPending

    paying_event.registrations[0].status = RegistrationStatus.Active
    response = leader_client.post(
        f"/collectives/{paying_event.id}/register_user", data={"user_id": user1.id}
    )
    assert response.status_code == 302
    assert paying_event.num_taken_slots() == 1
    assert paying_event.is_registered(user1) == True
    assert paying_event.registrations[0].status == RegistrationStatus.Active


def test_youth_event_autoregistration(youth_user, youth_client, youth_event):
    """Test user auto registration"""
    response = youth_client.get(f"/collectives/{youth_event.id}", follow_redirects=True)
    assert response.status_code == 200

    response = youth_client.post(
        f"/collectives/{youth_event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(youth_event.registrations) == 1
    assert youth_event.num_taken_slots() == 1
    assert youth_event.is_registered(youth_user) == True
    assert youth_event.registrations[0].status == RegistrationStatus.Active


def test_youth_event_failed_autoregistration(user1, user1_client, youth_event):
    """Test user auto registration"""
    response = user1_client.get(f"/collectives/{youth_event.id}", follow_redirects=True)
    assert response.status_code == 200

    response = user1_client.post(
        f"/collectives/{youth_event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert youth_event.num_taken_slots() == 0
