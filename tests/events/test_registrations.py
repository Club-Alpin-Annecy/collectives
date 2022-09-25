""" Event actions tests related to registrations"""
from datetime import date, timedelta
from collectives.models import db

# pylint: disable=unused-argument


def test_valid_event_autoregistration(user1, user1_client, event):
    """Test user auto registration"""
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 1
    assert event.active_registrations()[0].user == user1


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
