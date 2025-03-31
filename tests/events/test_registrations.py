"""Event actions tests related to registrations"""

from datetime import date, timedelta
from collectives.models import db, RegistrationStatus, BadgeIds
from collectives.utils.time import current_time


# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
# pylint: disable=unused-import

from tests.mock.mail import mail_success_monkeypatch


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


def test_swiss_phone_autoregistration(user1, user1_client, event):
    """Test user auto registration with a user with a wrong phone number"""
    user1.phone = "+41 22 767 6111"

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 1


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


def test_full_event_autoregistration_with_waiting_list(user1, user1_client, event):
    """Test an auto registration to a full event with waiting list"""

    event.num_online_slots = 0
    event.num_waiting_list = 1
    db.session.add(event)
    db.session.commit()

    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 0
    assert len(event.waiting_registrations()) == 1


def test_unregister(user1_client, event1_with_reg, mail_success_monkeypatch):
    """Tests self unregistering of a user"""
    event = event1_with_reg

    response = user1_client.post(
        f"/collectives/{event.id}/self_unregister",
        follow_redirects=True,
        data={"reason": "la flemme"},
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 3
    assert len(event.registrations) == 4

    # One mail sent to leader
    assert (
        "flemme"
        in mail_success_monkeypatch.sent_to(event.leaders[0].mail)[0]["message"]
    )


def test_unregister_with_waiting_list(
    user1_client, event1_with_reg_waiting_list, mail_success_monkeypatch
):
    """Tests self unregistering of a client, with waiting list update"""
    event = event1_with_reg_waiting_list

    response = user1_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 2
    assert len(event.waiting_registrations()) == 1
    assert len(event.registrations) == 4

    # One to leader, one to promoted user
    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert mail_success_monkeypatch.sent_to(event.active_registrations()[-1].user.mail)


def test_unregister_from_waiting_list(user3_client, event1_with_reg_waiting_list):
    """Tests self unregistering of a client from the waiting list."""
    event = event1_with_reg_waiting_list

    response = user3_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 2
    assert len(event.waiting_registrations()) == 1
    assert len(event.registrations) == 3


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


# Late unregistration-related tests
def test_unregister_in_grace_period(
    user1_client, user1, event_in_less_than_x_hours_with_reg, mail_success_monkeypatch
):
    """
    Tests the late self-unregistration of a user without any unregistration-related warning badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg

    # Register
    response = user1_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 7
    assert len(event.registrations) == 7

    # Immediately unregister
    response = user1_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 6
    assert len(event.registrations) == 7

    assert not event.is_late_unregistered(user1)
    assert not user1.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)


def test_unregister_lately_no_warning(
    client_with_no_warning_badge,
    user_with_no_warning_badge,
    event_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user without any unregistration-related warning badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_no_warning_badge
    user = user_with_no_warning_badge
    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 5
    assert len(event.registrations) == 6

    assert event.is_late_unregistered(user)
    assert user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 1

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert (
        "premier avertissement"
        in mail_success_monkeypatch.sent_to(user.mail)[0]["subject"]
    )


def test_unregister_lately_valid_first_warning(
    client_with_valid_first_warning_badge,
    user_with_valid_first_warning_badge,
    event_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user with a valid first warning badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_valid_first_warning_badge
    user = user_with_valid_first_warning_badge
    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 5
    assert len(event.registrations) == 6

    assert event.is_late_unregistered(user)
    assert user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 2

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert (
        "dernier avertissement"
        in mail_success_monkeypatch.sent_to(user.mail)[0]["subject"]
    )


def test_unregister_lately_expired_first_warning(
    client_with_expired_first_warning_badge,
    user_with_expired_first_warning_badge,
    event_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user with an expired first warning badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_expired_first_warning_badge
    user = user_with_expired_first_warning_badge

    assert not user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.has_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 0

    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 5
    assert len(event.registrations) == 6

    assert event.is_late_unregistered(user)
    assert user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 1

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert (
        "premier avertissement"
        in mail_success_monkeypatch.sent_to(user.mail)[0]["subject"]
    )


def test_unregister_lately_valid_second_warning(
    client_with_valid_second_warning_badge,
    user_with_valid_second_warning_badge,
    event_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user with a valid second warning badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_valid_second_warning_badge
    user = user_with_valid_second_warning_badge
    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 5
    assert len(event.registrations) == 6

    assert event.is_late_unregistered(user)
    assert user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 3
    assert user.has_a_valid_badge([BadgeIds.Suspended])

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert (
        "suspension"
        in mail_success_monkeypatch.sent_to(user.mail)[0]["subject"].lower()
    )


def test_unregister_lately_expired_second_warning(
    client_with_expired_second_warning_badge,
    user_with_expired_second_warning_badge,
    event_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user with an expired second warning badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_expired_second_warning_badge
    user = user_with_expired_second_warning_badge

    assert user.number_of_valid_warning_badges() == 1

    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 5
    assert len(event.registrations) == 6

    assert event_in_less_than_x_hours_with_reg.is_late_unregistered(user)
    # First Warning badge did not exist so it is assigned to the user before a new Second Warning
    assert user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 2
    assert not user.has_a_valid_badge([BadgeIds.Suspended])

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert (
        "dernier avertissement"
        in mail_success_monkeypatch.sent_to(user.mail)[0]["subject"]
    )


def test_unregister_lately_from_event_with_no_activity_type(
    client_with_no_warning_badge,
    user_with_no_warning_badge,
    event_with_no_activity_type_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user to an event not requiring an
    activity type without any unregistration-related warning badge. Verifies that the user
    is correctly unregistered and that badges are assigned as expected.
    """
    event = event_with_no_activity_type_in_less_than_x_hours_with_reg
    user_client = client_with_no_warning_badge
    user = user_with_no_warning_badge
    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 1
    assert len(event.registrations) == 2

    assert not event.is_late_unregistered(user)
    assert event.is_unregistered(user)
    assert not user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert len(mail_success_monkeypatch.sent_to(user.mail)) == 0


def test_unregister_lately_expired_suspended(
    client_with_expired_suspended_badge,
    user_with_expired_suspended_badge,
    event_in_less_than_x_hours_with_reg,
    mail_success_monkeypatch,
):
    """
    Tests the late self-unregistration of a user with an expired suspended badge.
    Verifies that the user is correctly unregistered and that badges are assigned as expected.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_expired_suspended_badge
    user = user_with_expired_suspended_badge

    assert not user.has_a_valid_badge([BadgeIds.Suspended])

    response = user_client.post(
        f"/collectives/{event.id}/self_unregister", follow_redirects=True
    )
    assert response.status_code == 200
    assert event.num_taken_slots() == 5
    assert len(event.registrations) == 6

    assert event_in_less_than_x_hours_with_reg.is_late_unregistered(user)
    # First Warning did not exist so it is assigned to the user before a new Second Warning
    assert user.has_a_valid_badge([BadgeIds.UnjustifiedAbsenceWarning])
    assert user.number_of_valid_warning_badges() == 1
    assert not user.has_a_valid_badge([BadgeIds.Suspended])

    assert mail_success_monkeypatch.sent_to(event.leaders[0].mail)
    assert (
        "premier avertissement"
        in mail_success_monkeypatch.sent_to(user.mail)[0]["subject"]
    )


def test_register_for_valid_suspended_user(
    client_with_valid_suspended_badge,
    user_with_valid_suspended_badge,
    event_in_less_than_x_hours_with_reg,
):
    """
    Tests the self-registration of a user with a valid suspended badge.
    Verifies that the user cannot register to the event and that badges are assigned properly.
    """
    event = event_in_less_than_x_hours_with_reg
    user_client = client_with_valid_suspended_badge
    user = user_with_valid_suspended_badge
    response = user_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert user.has_a_valid_badge([BadgeIds.Suspended])
    assert user.has_a_valid_suspended_badge()
    assert len(event.registrations) == 6
    assert not event.can_self_register(user, current_time())

    response = user_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 6


def test_register_for_valid_second_warning_user(
    client_with_valid_second_warning_badge,
    user_with_valid_second_warning_badge,
    event_in_less_than_x_hours,
):
    """
    Tests the self-registration of a user with a valid second warning badge.
    Verifies that the user is correctly registered to the event.
    """
    event = event_in_less_than_x_hours
    user_client = client_with_valid_second_warning_badge
    response = user_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert len(event.registrations) == 0

    response = user_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 1


def test_register_for_valid_first_warning_user(
    client_with_valid_first_warning_badge,
    user_with_valid_first_warning_badge,
    event_in_less_than_x_hours,
):
    """
    Tests the self-registration of a user with a valid first warning badge.
    Verifies that the user is correctly registered to the event.
    """
    event = event_in_less_than_x_hours
    user_client = client_with_valid_first_warning_badge
    response = user_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert len(event.registrations) == 0

    response = user_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event.registrations) == 1


def test_register_for_expired_suspended_user(
    client_with_expired_suspended_badge,
    user_with_expired_suspended_badge,
    event_in_less_than_x_hours,
):
    """
    Tests the self-registration of a user with an expired suspended badge.
    Verifies that the user is correctly registered to the event.
    """
    event = event_in_less_than_x_hours
    user_client = client_with_expired_suspended_badge
    user = user_with_expired_suspended_badge

    response = user_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200

    assert len(event.registrations) == 0
    assert not event.is_registered(user)

    response = user_client.post(
        f"/collectives/{event.id}/self_register", follow_redirects=True
    )

    assert response.status_code == 200

    assert event.is_registered(user)
    assert len(event.registrations) == 1
    assert not user.has_a_valid_suspended_badge()
