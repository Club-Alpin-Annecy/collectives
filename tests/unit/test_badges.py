"""Unit tests for Badge class"""

from datetime import date, timedelta
from collectives.models.activity_type import ActivityType
from collectives.models.badge import Badge, BadgeIds
from collectives.models import db
from collectives.models.user import User


def test_add_a_valid_badge(user1):
    """Test adding a badge to a user"""
    activity1 = ActivityType.query.get(1)

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
    activity1 = ActivityType.query.get(1)

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
