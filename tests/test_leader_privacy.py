"""Tests for the LEADER_PRIVACY configuration."""

from flask import url_for

# pylint: disable=unused-argument


def test_regular_user_can_access_leader_profile_by_default(user1_client, leader_user):
    """Without LEADER_PRIVACY, any logged-in user can access a leader profile."""
    response = user1_client.get(
        url_for("profile.show_leader", leader_id=leader_user.id)
    )
    assert response.status_code == 200


def test_leader_can_access_own_profile(
    leader_client, leader_user, enable_leader_privacy
):
    """A leader can always access their own profile, even with LEADER_PRIVACY enabled."""
    response = leader_client.get(
        url_for("profile.show_leader", leader_id=leader_user.id)
    )
    assert response.status_code == 200


def test_regular_user_cannot_access_leader_profile(
    user1_client, leader_user, enable_leader_privacy
):
    """With LEADER_PRIVACY, a regular user is redirected away from leader profile."""
    response = user1_client.get(
        url_for("profile.show_leader", leader_id=leader_user.id)
    )
    assert response.status_code == 302


def test_admin_can_access_leader_profile(
    admin_client, leader_user, enable_leader_privacy
):
    """Admin can always see leader profiles regardless of LEADER_PRIVACY."""
    response = admin_client.get(
        url_for("profile.show_leader", leader_id=leader_user.id)
    )
    assert response.status_code == 200


def test_supervisor_of_leader_activity_can_access_profile(
    supervisor_client, leader_user, enable_leader_privacy
):
    """Supervisor of the leader's activity can see the leader profile."""
    response = supervisor_client.get(
        url_for("profile.show_leader", leader_id=leader_user.id)
    )
    assert response.status_code == 200


def test_event_page_hides_leader_link_for_regular_user(
    user1_client, event1_with_reg, leader_user, enable_leader_privacy
):
    """With LEADER_PRIVACY, leader profile URL is absent from event page for regular users."""
    response = user1_client.get(
        f"/collectives/{event1_with_reg.id}", follow_redirects=True
    )
    assert response.status_code == 200
    leader_url = f"/profile/organizer/{leader_user.id}"
    assert leader_url not in response.text


def test_event_page_shows_leader_link_for_supervisor(
    supervisor_client, event1_with_reg, leader_user, enable_leader_privacy
):
    """With LEADER_PRIVACY, a supervisor of the leader's activity still sees the profile link."""
    response = supervisor_client.get(
        f"/collectives/{event1_with_reg.id}", follow_redirects=True
    )
    assert response.status_code == 200
    leader_url = f"/profile/organizer/{leader_user.id}"
    assert leader_url in response.text
