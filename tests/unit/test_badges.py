"""Unit tests for Badge class"""

from collectives.models.activity_type import ActivityType
from collectives.models.badge import Badge, BadgeIds
from collectives.models import db
from collectives.models.user import User


def test_add_badge(user1):
    """Test adding a badge to a user"""
    activity1 = ActivityType.query.get(1)

    benevole_badge = Badge(
        user_id=user1.id, activity_id=activity1.id, badge_id=int(BadgeIds.Benevole)
    )
    user1.badges.append(benevole_badge)

    db.session.add(user1)
    db.session.commit()

    retrieved_user = User.query.filter_by(id=user1.id).first()
    assert len(retrieved_user.badges) == 1
    assert retrieved_user.is_benevole()
