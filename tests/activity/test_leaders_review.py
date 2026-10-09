"""Module to test the leaders review of activity supervision."""

from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy import event

from collectives.models import (
    ActivityType,
    Event,
    EventStatus,
    EventType,
    Registration,
    RegistrationLevels,
    RegistrationStatus,
    Role,
    RoleIds,
    UserType,
    db,
)
from collectives.utils.leaders_review import LeadersReview
from tests.fixtures.user import promote_user

# pylint: disable=unused-argument

NOW = datetime(2026, 10, 9, 12, 0)
""" Reference time for the review: start of the 2026/2027 season """


def _alpinisme():
    return ActivityType.query.filter_by(name="Alpinisme").first()


def _create_event(start, leaders, status=EventStatus.Confirmed, activity=None):
    """Creates a collective event at ``start``, led by ``leaders``."""
    event = Event()
    event.title = f"Collective du {start}"
    event.description = ""
    event.start = start
    event.end = start + timedelta(hours=8)
    event.registration_open_time = start - timedelta(days=10)
    event.registration_close_time = start - timedelta(days=1)
    event.num_online_slots = 4
    event.status = status
    event.event_type = EventType.query.filter_by(name="Collective").first()
    event.activity_types.append(activity or _alpinisme())
    event.leaders = list(leaders)
    event.main_leader = leaders[0]
    db.session.add(event)
    db.session.commit()
    return event


def _add_coleader(event, user, status=RegistrationStatus.Active):
    """Registers ``user`` as co-leader of ``event``."""
    registration = Registration(
        user=user,
        event=event,
        status=status,
        level=RegistrationLevels.CoLeader,
        is_self=False,
        registration_time=event.start - timedelta(days=5),
    )
    db.session.add(registration)
    db.session.commit()


def _age_roles():
    """Marks all existing roles as granted long before the review."""
    for role in Role.query.all():
        role.creation_time = datetime(2020, 1, 1)
    db.session.commit()


def _review_of(review, user):
    return next(leader for leader in review.leaders if leader.user == user)


def test_review_stats(supervisor_user, leader_user, leader2_user, user1, user2):
    """Test per-leader statistics and flags."""
    _age_roles()

    # leader_user: active during previous season, plus a cancelled event this season
    _create_event(datetime(2025, 11, 15), [leader_user])
    _create_event(datetime(2026, 9, 20), [leader_user], status=EventStatus.Cancelled)

    # leader2_user: last event three seasons ago
    _create_event(datetime(2023, 5, 1), [leader2_user])

    # user1: trainee co-leading an upcoming event, and an event of another activity
    promote_user(user1, RoleIds.Trainee)
    upcoming = _create_event(datetime(2026, 12, 1), [leader2_user])
    _add_coleader(upcoming, user1)
    other_activity = ActivityType.query.filter(ActivityType.name != "Alpinisme").first()
    _create_event(datetime(2025, 6, 1), [user1], activity=other_activity)

    # user2: recently granted leader who has not led anything yet
    db.session.commit()
    _age_roles()
    promote_user(user2, RoleIds.EventLeader)
    db.session.commit()
    Role.query.filter_by(user_id=user2.id).one().creation_time = datetime(2026, 3, 1)
    db.session.commit()

    review = LeadersReview(_alpinisme(), now=NOW)
    assert review.seasons == [2024, 2025, 2026]

    leader = _review_of(review, leader_user)
    assert leader.events_per_season == {2024: 0, 2025: 1, 2026: 0}
    assert leader.last_event_start == datetime(2025, 11, 15)
    assert leader.nb_upcoming_events == 0
    assert not leader.is_inactive
    assert not leader.is_new

    leader2 = _review_of(review, leader2_user)
    assert leader2.events_per_season == {2024: 0, 2025: 0, 2026: 1}
    assert leader2.last_event_start == datetime(2023, 5, 1)
    assert leader2.nb_upcoming_events == 1
    assert not leader2.is_inactive

    trainee = _review_of(review, user1)
    assert trainee.role.role_id == RoleIds.Trainee
    assert trainee.events_per_season == {2024: 0, 2025: 0, 2026: 1}
    assert trainee.last_event_start is None
    assert trainee.nb_upcoming_events == 1
    assert not trainee.is_inactive

    new_leader = _review_of(review, user2)
    assert new_leader.is_new
    assert not new_leader.is_inactive
    assert new_leader.last_event_start is None

    supervisor = _review_of(review, supervisor_user)
    assert supervisor.is_inactive
    assert not supervisor.can_be_removed

    # Leaders needing attention come first
    assert review.leaders[0] == supervisor


def test_review_inactive_leader(leader_user):
    """Test that a leader without any event for two full seasons is inactive."""
    _age_roles()
    _create_event(datetime(2024, 8, 30), [leader_user])
    _create_event(datetime(2025, 1, 10), [leader_user], status=EventStatus.Cancelled)

    leader = _review_of(LeadersReview(_alpinisme(), now=NOW), leader_user)
    assert leader.is_inactive
    assert leader.needs_attention
    assert leader.can_be_removed
    assert leader.last_event_start == datetime(2024, 8, 30)


def test_review_ignores_invalid_coleading(leader_user, user1):
    """Test that a rejected co-leader registration is not counted."""
    promote_user(user1, RoleIds.Trainee)
    db.session.commit()
    _age_roles()
    event = _create_event(datetime(2025, 10, 1), [leader_user])
    _add_coleader(event, user1, status=RegistrationStatus.Rejected)

    trainee = _review_of(LeadersReview(_alpinisme(), now=NOW), user1)
    assert trainee.events_per_season == {2024: 0, 2025: 0, 2026: 0}
    assert trainee.is_inactive


def test_review_page(supervisor_client, leader_user):
    """Test display of the review page."""
    response = supervisor_client.get("/activity_supervision/leader/review")
    assert response.status_code == 200
    assert "Revue des encadrants — Alpinisme" in response.text
    assert leader_user.full_name() in response.text
    assert "Retirer le rôle" in response.text


def test_review_page_unsupervised_activity(supervisor_client, leader_user):
    """Test that a supervisor cannot review an activity they do not supervise."""
    other_activity = ActivityType.query.filter(ActivityType.name != "Alpinisme").first()
    promote_user(leader_user, RoleIds.EventLeader, other_activity.name)
    db.session.commit()

    response = supervisor_client.get(
        f"/activity_supervision/leader/review?activity_id={other_activity.id}"
    )
    assert response.status_code == 200
    assert "Revue des encadrants — Alpinisme" in response.text


def test_review_page_forbidden(user1_client):
    """Test that a regular user cannot access the review page."""
    response = user1_client.get("/activity_supervision/leader/review")
    assert response.status_code == 302


def test_remove_role_from_review(supervisor_client, leader_user):
    """Test removing a role from the review page."""
    role = Role.query.filter_by(user_id=leader_user.id).one()
    role_id, activity_id = role.id, role.activity_id
    # Make sure the route loads relationships itself, as in a real request
    db.session.expire_all()

    response = supervisor_client.post(
        f"/activity_supervision/leader/delete/{role_id}", data={"from_review": "1"}
    )
    assert response.status_code == 302
    assert response.location.endswith(
        f"/activity_supervision/leader/review?activity_id={activity_id}"
    )
    assert Role.query.filter_by(user_id=leader_user.id).count() == 0

    response = supervisor_client.get(response.location)
    assert f"Rôle Encadrant retiré à {leader_user.full_name()}" in response.text


def test_role_creation_time(supervisor_client, user1):
    """Test that a newly granted role records its creation time."""
    response = supervisor_client.post(
        "/activity_supervision/leader/add",
        data={
            "user_id": user1.id,
            "activity_id": _alpinisme().id,
            "role_id": int(RoleIds.EventLeader),
        },
    )
    assert response.status_code == 302

    role = Role.query.filter_by(user_id=user1.id).one()
    assert role.creation_time is not None


def test_review_query_count_is_constant(supervisor_user, user1, user2):
    """Test that the review does not fire one user query per role holder."""
    _age_roles()

    def count_queries():
        statements = []

        def record(_conn, _cursor, statement, *_args):
            statements.append(statement)

        db.session.expire_all()
        event.listen(db.engine, "before_cursor_execute", record)
        try:
            LeadersReview(_alpinisme(), now=NOW)
        finally:
            event.remove(db.engine, "before_cursor_execute", record)
        return len(statements)

    count_queries()  # warm up
    baseline = count_queries()

    promote_user(user1, RoleIds.EventLeader)
    promote_user(user2, RoleIds.Trainee)
    db.session.commit()

    assert count_queries() == baseline


def test_review_unverified_account_badge(supervisor_client, leader_user):
    """Test that a not yet validated email is not reported as an expired licence."""
    leader_user.type = UserType.UnverifiedLocal
    db.session.commit()

    response = supervisor_client.get("/activity_supervision/leader/review")
    assert response.status_code == 200

    table = response.text.split('<table class="leaders-review-table">')[1]
    assert "Email non vérifié" in table
    assert "Licence expirée" not in table


def test_remove_orphan_role(supervisor_client):
    """Test removing a role which is not linked to any user anymore."""
    activity = _alpinisme()
    db.session.execute(
        sa.text(
            "INSERT INTO roles (user_id, activity_id, role_id) VALUES "
            "(NULL, :activity_id, 'EventLeader')"
        ),
        {"activity_id": activity.id},
    )
    db.session.commit()
    role_id = db.session.execute(sa.text("SELECT max(id) FROM roles")).scalar()

    response = supervisor_client.post(
        f"/activity_supervision/leader/delete/{role_id}", data={"from_review": "1"}
    )
    assert response.status_code == 302
    assert db.session.get(Role, role_id) is None

    response = supervisor_client.get(response.location)
    assert "retiré pour l" in response.text
