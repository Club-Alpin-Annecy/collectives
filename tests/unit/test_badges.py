"""Unit tests for Badge class"""

from datetime import date, timedelta
from collectives.models.activity_type import ActivityType
from collectives.models.badge import Badge, BadgeIds
from collectives.models.user import User
from collectives.models import (
    db,
    Event,
    Registration,
    RegistrationLevels,
    RegistrationStatus,
)


def test_add_a_valid_badge(user1):
    """Test adding a badge to a user"""
    activity1 = db.session.get(ActivityType, 1)

    # Get today's date
    today = date.today()

    # Compute tomorrow's date
    tomorrow = today + timedelta(days=1)

    benevole_badge_ok = Badge(
        user_id=user1.id,
        activity_id=activity1.id,
        badge_id=int(BadgeIds.Benevole),
        expiration_date=tomorrow,
    )
    user1.badges.append(benevole_badge_ok)

    db.session.add(user1)
    db.session.commit()

    retrieved_user = User.query.filter_by(id=user1.id).first()
    assert len(retrieved_user.badges) == 1
    assert retrieved_user.has_a_valid_benevole_badge()


def test_add_an_invalid_badge(user2):
    """Test adding a badge to a user"""
    activity1 = db.session.get(ActivityType, 1)

    # Get today's date
    today = date.today()

    # Compute yesterday's date
    yesterday = today - timedelta(days=1)

    benevole_badge_nok = Badge(
        user_id=user2.id,
        activity_id=activity1.id,
        badge_id=int(BadgeIds.Benevole),
        expiration_date=yesterday,
    )
    user2.badges.append(benevole_badge_nok)

    db.session.add(user2)
    db.session.commit()

    retrieved_user = User.query.filter_by(id=user2.id).first()
    assert len(retrieved_user.badges) == 1
    assert not retrieved_user.has_a_valid_benevole_badge()


def test_assign_badge(user1, session_monkeypatch):
    """
    Assigns a badge to a user and verifies the session changes.

    Args:
        user1: The user to assign the badge to.
        session_monkeypatch: The monkeypatched session for testing.

    Returns:
        None
    """
    badge_id = int(BadgeIds.UnjustifiedAbsenceWarning)
    expiration_date = date.today() + timedelta(days=1)

    user1.assign_badge(badge_id, expiration_date=expiration_date, level=1)

    assert len(session_monkeypatch["add"]) == 1  # Badge instance should be added
    assert session_monkeypatch["commit"] == 1  # Commit should be called once
    assert session_monkeypatch["rollback"] == 0  # Rollback should not be called


def test_increment_warning_badges_no_updates(
    user1, event1_with_reg, session_monkeypatch, monkeypatch
):
    """
    Tests the increment_warning_badges method without any
    badge updates and verifies the session changes.

    Args:
        user1: The user whose warning badges are being updated.
        session_monkeypatch: The monkeypatched session for testing.
        monkeypatch: The pytest monkeypatch fixture for mocking.

    Returns:
        None
    """
    # Mock the badge condition checks to simulate no updates
    monkeypatch.setattr(user1, "has_a_valid_badge", lambda x: False)
    monkeypatch.setattr(user1, "has_badge", lambda x: False)

    reg = event1_with_reg.existing_registrations(user1)[0]

    user1.increment_warning_badges(reg)

    # Verify database operations were performed
    assert len(session_monkeypatch["add"]) == 1  # New badge should be added
    assert session_monkeypatch["commit"] == 1  # New commit should occur
    assert session_monkeypatch["rollback"] == 0  # No rollback should occur

    monkeypatch.setattr(
        user1,
        "has_a_valid_badge",
        lambda badge_ids: BadgeIds.UnjustifiedAbsenceWarning in badge_ids,
    )
    monkeypatch.setattr(
        user1,
        "has_badge",
        lambda badge_ids: BadgeIds.UnjustifiedAbsenceWarning in badge_ids,
    )

    user1.increment_warning_badges(reg)

    # Verify database operations were performed
    assert len(session_monkeypatch["add"]) == 2  # New badge should be added
    assert session_monkeypatch["commit"] == 2  # New commit should occur
    assert session_monkeypatch["rollback"] == 0  # No rollback should occur

    # Mock `matching_badges` to simulate finding more than one badge of a specified type
    monkeypatch.setattr(user1, "has_badge", lambda x: True)
    monkeypatch.setattr(
        user1,
        "matching_badges",
        lambda badge_ids=None: [
            BadgeIds.UnjustifiedAbsenceWarning,
            BadgeIds.UnjustifiedAbsenceWarning,
        ],
    )

    assert len(user1.matching_badges()) == 2

    # Verify no database operations were performed
    assert len(session_monkeypatch["add"]) == 2  # No badge should be added
    assert session_monkeypatch["commit"] == 2  # No commit should occur
    assert session_monkeypatch["rollback"] == 0  # No rollback should occur


def test_remove_sanction_badge(user1: User, event: Event):
    """Test that removing a warning badge removes suspension
    if that warning was counted towards suspension"""

    db.session.add(event)
    db.session.commit()

    expiration_date = date.today() + timedelta(days=1)

    reg1 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.UnJustifiedAbsentee,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg2 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.UnJustifiedAbsentee,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    reg3 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.UnJustifiedAbsentee,
        level=RegistrationLevels.Normal,
        is_self=True,
    )
    event.registrations.append(reg1)
    event.registrations.append(reg2)
    event.registrations.append(reg3)

    user1.assign_badge(
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=expiration_date,
        registration=reg1,
    )
    user1.assign_badge(
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=expiration_date,
        registration=reg2,
    )
    user1.assign_badge(
        BadgeIds.Suspended,
        expiration_date=expiration_date,
        registration=reg2,
    )
    user1.assign_badge(
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=expiration_date,
        registration=reg3,
    )
    user1.assign_badge(
        BadgeIds.Suspended,
        expiration_date=expiration_date,
        registration=reg3,
    )
    db.session.commit()

    assert user1.has_a_valid_suspended_badge()
    assert user1.number_of_valid_warning_badges() == 3

    user1.remove_warning_badges(reg1)
    db.session.commit()

    assert user1.has_a_valid_suspended_badge()
    assert user1.number_of_valid_warning_badges() == 2

    user1.remove_warning_badges(reg2)
    db.session.commit()

    assert not user1.has_a_valid_suspended_badge()
    assert user1.number_of_valid_warning_badges() == 1
