"""Tests for bulk badge import via CSV."""

from datetime import date
from io import BytesIO

from collectives.models import ActivityType, Badge, BadgeIds, User, db
from tests import utils
from tests.fixtures.misc import (
    custom_skill,
    custom_skill_with_activity_type,
    custom_skill_with_expiry,
)


def test_competency_bulk_add(supervisor_client, user1, user2, user3):
    """Tests the ability for a supervisor to bulk-add competency badges to users"""

    levels = BadgeIds.Practitioner.levels()

    csv = (
        "license, level, activity\n"
        f"{user1.license},\n"
        f"{user2.license},{levels[2].name}\n"
        f"{user2.license},{levels[3].name}\n"
        f"{user2.license},{levels[1].name}\n"
        f"{user3.license},,Canyon\n"
    )

    response = supervisor_client.get("/activity_supervision/competency_badge_holders/")
    data = utils.load_data_from_form(response.text, "user-search-form")
    data["activity_id"] = ActivityType.query.filter_by(name="Alpinisme").first().id
    data["csv_file"] = (BytesIO(csv.encode("utf8")), "import.csv")
    data["badge_id"] = str(int(BadgeIds.Practitioner))
    data["level"] = 2

    response = supervisor_client.post(
        "/activity_supervision/competency_badge/add", data=data
    )

    assert response.status_code == 302

    assert len(user1.badges) == 1
    assert user1.badges[0].badge_id == BadgeIds.Practitioner
    assert user1.badges[0].level == 2
    assert user1.badges[0].activity_name == "Alpinisme"
    assert len(user2.badges) == 1
    assert user2.badges[0].badge_id == BadgeIds.Practitioner
    assert user2.badges[0].level == 3
    assert user2.badges[0].activity_name == "Alpinisme"

    # User3 should not have received a badge
    # as supervisor_client is not supervising "Canyon"
    assert len(user3.badges) == 0


def test_skill_bulk_add(
    supervisor_client,
    user1,
    user2,
    user3,
    custom_skill,
    custom_skill_with_expiry,
    custom_skill_with_activity_type,
):
    """Tests the ability for a supervisor to bulk-add competency badges to users"""

    levels = BadgeIds.Skill.levels()

    activity_name = ActivityType.get(custom_skill_with_activity_type.activity_id).name
    csv = (
        "license, level, activite\n"
        f"{user1.license},{custom_skill.name},\n"
        f"{user1.license},{custom_skill.name},\n"
        f"{user2.license},{custom_skill_with_expiry.name}\n"
        f"{user3.license},{custom_skill_with_activity_type.name}, NonExisting\n"
        f"{user3.license},{custom_skill_with_activity_type.name}, {activity_name}\n"
    )

    response = supervisor_client.get("/activity_supervision/competency_badge_holders/")
    data = utils.load_data_from_form(response.text, "user-search-form")
    data["csv_file"] = (BytesIO(csv.encode("utf8")), "import.csv")
    data["badge_id"] = str(int(BadgeIds.Skill))
    data["level"] = next(iter(levels.keys()))
    data["activity_id"] = "0"

    response = supervisor_client.post(
        "/activity_supervision/competency_badge/add", data=data
    )

    assert response.status_code == 302

    assert len(user1.badges) == 1
    assert user1.badges[0].badge_id == BadgeIds.Skill
    assert user1.badges[0].level == custom_skill.level
    assert user1.badges[0].activity_id is None
    assert user1.badges[0].expiration_date is None
    assert len(user2.badges) == 1
    assert user2.badges[0].badge_id == BadgeIds.Skill
    assert user2.badges[0].level == custom_skill_with_expiry.level
    assert user2.badges[0].activity_id is None
    assert user2.badges[0].expiration_date is not None
    assert len(user3.badges) == 1
    assert user3.badges[0].badge_id == BadgeIds.Skill
    assert user3.badges[0].level == custom_skill_with_activity_type.level
    assert user3.badges[0].activity_id == custom_skill_with_activity_type.activity_id
    assert user3.badges[0].expiration_date is None
