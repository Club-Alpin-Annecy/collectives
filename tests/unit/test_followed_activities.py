"""Unit tests for UserFollowedActivity model"""

import pytest

from collectives.models import ActivityType, User, UserFollowedActivity, db
from collectives.utils.time import current_time


def test_follow_activity(user1, event1):
    """Test following an activity"""
    # Get first activity from event1
    activity = event1.activity_types[0]

    # User should not be following initially
    assert not user1.is_following_activity(activity)

    # Follow the activity
    result = user1.follow_activity(activity)
    db.session.commit()

    # Should return True (success)
    assert result is True
    assert user1.is_following_activity(activity)


def test_unfollow_activity(user1, event1):
    """Test unfollowing an activity"""
    activity = event1.activity_types[0]

    # First follow
    user1.follow_activity(activity)
    db.session.commit()
    assert user1.is_following_activity(activity)

    # Then unfollow
    user1.unfollow_activity(activity)
    db.session.commit()

    # Should no longer be following
    assert not user1.is_following_activity(activity)


def test_explicit_unfollow_prevents_refollow(user1, event1):
    """Test that explicit unfollow prevents auto-refollow"""
    activity = event1.activity_types[0]

    # First unfollow explicitly (without ever following)
    user1.unfollow_activity(activity)
    db.session.commit()

    # Try to follow
    result = user1.follow_activity(activity)
    db.session.commit()

    # Should return False (blocked by explicit unfollow)
    assert result is False
    assert not user1.is_following_activity(activity)


def test_get_followed_activities(user1, event1):
    """Test getting list of followed activities"""
    activities = event1.activity_types

    # Initially no followed activities
    assert len(user1.get_followed_activities()) == 0

    # Follow all activities
    for activity in activities:
        user1.follow_activity(activity)
    db.session.commit()

    # Should have all activities
    followed = user1.get_followed_activities()
    assert len(followed) == len(activities)


def test_activity_followed_by(user1, event1):
    """Test activity.followed_by() method"""
    activity = event1.activity_types[0]

    # Not followed initially
    assert not activity.followed_by(user1)

    # Follow and check
    user1.follow_activity(activity)
    db.session.commit()
    assert activity.followed_by(user1)

    # Unfollow and check
    user1.unfollow_activity(activity)
    db.session.commit()
    assert not activity.followed_by(user1)
