"""Tests for the rules attached to event types and services (volunteer time,
collective events, service roles, club announcements)."""

# pylint: disable=unused-argument

from datetime import date, timedelta

import pytest

from collectives.forms.event import available_activities
from collectives.models import (
    ActivityKind,
    ActivityType,
    EventStatus,
    EventType,
    RoleIds,
    db,
)
from collectives.routes.event import highlighted_club_announcements
from collectives.utils.time import current_time
from tests.fixtures.user import promote_user


@pytest.fixture
def announcement_service(app):
    """:returns: The service whose events are club announcements"""
    service = ActivityType(
        name="Annonce club",
        short=app.config["CLUB_ANNOUNCEMENT_ACTIVITY"],
        trigram="ANN",
        kind=ActivityKind.Service,
    )
    db.session.add(service)
    db.session.commit()
    return service


@pytest.fixture
def board_service(app):
    """:returns: The service gathering board members"""
    service = ActivityType(
        name="Comité directeur",
        short=app.config["BOARD_ACTIVITY"],
        trigram="CD",
        kind=ActivityKind.Service,
    )
    db.session.add(service)
    db.session.commit()
    return service


def _set_type(event, short):
    event.event_type = EventType.query.filter_by(short=short).one()
    db.session.commit()


def test_volunteer_days_by_event_type(event1_with_reg):
    """Who counts as volunteer depends on the event type"""
    event = event1_with_reg
    db.session.commit()
    days = event.duration_in_ffcam_days()
    leaders = len(event.leaders)
    participants = len(event.active_registrations())
    assert participants == 4

    _set_type(event, "collective")
    assert event.volunteer_days() == days * leaders

    _set_type(event, "soiree")
    assert event.volunteer_days() == days * leaders

    _set_type(event, "inscription")
    assert event.volunteer_days() == 0

    _set_type(event, "shopping")
    assert event.volunteer_days() == 0

    _set_type(event, "organisation")
    assert event.volunteer_days() == days * (leaders + participants)

    # Deprecated types keep the former rule: leaders only
    _set_type(event, "benevolat")
    assert event.volunteer_days() == days * leaders


def test_collective_requires_activity_not_service(admin_client, service):
    """A collective event cannot be attached to services only"""
    now = current_time()
    data = {
        "update_activity": "0",
        "event_type_id": str(EventType.query.filter_by(short="collective").one().id),
        "single_activity_type": service.id,
        "leader_actions-0-leader_id": admin_client.user.id,
        "main_leader_id": admin_client.user.id,
        "add_leader": "0",
        "update_leaders": "0",
        "title": "Collective de service",
        "status": int(EventStatus.Confirmed),
        "num_slots": "5",
        "start": (now + timedelta(days=10)).strftime("%Y-%m-%d %X"),
        "end": (now + timedelta(days=10, hours=3)).strftime("%Y-%m-%d %X"),
        "num_online_slots": "0",
        "description": "Test",
        "edit_session_id": "ef32c979-57f6-48f8-a8d5-753050ff2f55",
    }
    response = admin_client.post("/collectives/add", data=data)
    assert response.status_code == 200
    assert "pas seulement à un service" in response.text


def test_role_names_by_activity_kind(user1, service):
    """Activity roles are named after the kind of activity they are held on"""
    initiative = ActivityType(
        name="Trappeurs", short="trappeurs", trigram="TRP", kind=ActivityKind.Initiative
    )
    db.session.add(initiative)
    db.session.commit()

    promote_user(user1, RoleIds.ActivitySupervisor, activity_name=service.name)
    promote_user(user1, RoleIds.ActivityStaff, activity_name=service.name)
    promote_user(user1, RoleIds.ActivitySupervisor, activity_name=initiative.name)
    promote_user(user1, RoleIds.ActivitySupervisor, activity_name="Alpinisme")
    promote_user(user1, RoleIds.Trainee, activity_name="Alpinisme")
    db.session.commit()

    names = {(role.activity_type.name, role.name) for role in user1.roles}
    assert names == {
        ("Service", "Responsable de service"),
        ("Service", "Organisateur"),
        ("Trappeurs", "Responsable d'initiative"),
        ("Alpinisme", "Responsable d'activité"),
        ("Alpinisme", "Encadrant en formation"),
    }


def test_club_announcement_permission(
    app, user1, user2, announcement_service, board_service
):
    """Only board members can attach an event to the club announcement service"""
    promote_user(user1, RoleIds.ActivityStaff, activity_name=announcement_service.name)
    promote_user(user2, RoleIds.ActivityStaff, activity_name=announcement_service.name)
    promote_user(user2, RoleIds.ActivityStaff, activity_name=board_service.name)
    db.session.commit()

    assert not user1.can_publish_club_announcements()
    assert user2.can_publish_club_announcements()

    event_type = EventType.query.filter_by(short="soiree").one()
    with app.test_request_context():
        # pylint: disable=import-outside-toplevel
        from flask_login import login_user

        login_user(user1)
        choices = available_activities([], [user1], event_type, False)
        assert announcement_service not in choices
        # Already attached: kept
        choices = available_activities(
            [announcement_service], [user1], event_type, False
        )
        assert announcement_service in choices

        login_user(user2)
        choices = available_activities([], [user2], event_type, False)
        assert announcement_service in choices


def test_highlighted_club_announcements(app, event, client, announcement_service):
    """Upcoming club announcements are highlighted until they are full"""
    event.activity_types = [announcement_service]
    event.num_slots = 5
    event.start = date.today() + timedelta(days=3)
    event.end = date.today() + timedelta(days=3)
    db.session.commit()

    with app.test_request_context():
        assert highlighted_club_announcements() == [event]

    response = client.get("/collectives/")
    assert event.title in response.text

    event.num_slots = 0
    db.session.commit()
    with app.test_request_context():
        assert not highlighted_club_announcements()


def test_board_member_publishes_announcement(
    user1, user1_client, announcement_service, board_service
):
    """A role on the board service is enough to publish a club announcement"""
    promote_user(user1, RoleIds.ActivityStaff, activity_name=board_service.name)
    db.session.commit()

    assert announcement_service in user1.get_organizable_activities()
    assert announcement_service not in user1.get_organizable_activities(
        need_leader=True
    )

    now = current_time()
    data = {
        "update_activity": "0",
        "event_type_id": str(EventType.query.filter_by(short="soiree").one().id),
        "single_activity_type": announcement_service.id,
        "leader_actions-0-leader_id": user1.id,
        "main_leader_id": user1.id,
        "add_leader": "0",
        "update_leaders": "0",
        "title": "Assemblée générale",
        "status": int(EventStatus.Confirmed),
        "num_slots": "50",
        "start": (now + timedelta(days=10)).strftime("%Y-%m-%d %X"),
        "end": (now + timedelta(days=10, hours=3)).strftime("%Y-%m-%d %X"),
        "num_online_slots": "0",
        "description": "Annonce",
        "edit_session_id": "ef32c979-57f6-48f8-a8d5-753050ff2f56",
    }
    response = user1_client.post("/collectives/add", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert "collectives/add" not in response.request.path
    assert "Assemblée générale" in response.text
