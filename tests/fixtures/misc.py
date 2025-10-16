import pytest

from collectives.models import ActivityType, BadgeCustomLevel, BadgeIds, db


@pytest.fixture
def custom_skill() -> BadgeCustomLevel:
    """Create a custom skill level without activity type."""
    custom_level = BadgeCustomLevel(
        badge_id=BadgeIds.Skill, name="Custom Skill 1", abbrev="S1"
    )
    db.session.add(custom_level)
    db.session.commit()
    return custom_level


@pytest.fixture
def custom_skill_with_expiry() -> BadgeCustomLevel:
    """Create a custom skill level without activity type."""
    custom_level = BadgeCustomLevel(
        badge_id=BadgeIds.Skill, name="Custom Skill 3", abbrev="S3", default_validity=48
    )
    db.session.add(custom_level)
    db.session.commit()
    return custom_level


@pytest.fixture
def custom_skill_with_activity_type(
    activity_name: str = "Alpinisme",
) -> BadgeCustomLevel:
    """Create a custom skill level with an activity type."""
    custom_level = BadgeCustomLevel(
        badge_id=BadgeIds.Skill, name="Custom Skill 2", abbrev="S2"
    )
    activity_type = ActivityType.query.filter_by(name=activity_name).first()
    custom_level.activity_type = activity_type

    db.session.add(custom_level)
    db.session.commit()
    return custom_level
