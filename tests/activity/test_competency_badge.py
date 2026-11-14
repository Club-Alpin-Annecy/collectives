"""Tests for bulk badge import via CSV."""

import json
from datetime import date, datetime
from io import BytesIO

import openpyxl

from collectives.forms.activity_type import ActivityTypeSelectionForm
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
        "license; level; activite\n"
        f"{user1.license};{custom_skill.name};\n"
        f"{user1.license};{custom_skill.name};\n"
        f"{user2.license};{custom_skill_with_expiry.name}\n"
        f"{user3.license};{custom_skill_with_activity_type.name}; NonExisting\n"
        f"{user3.license};{custom_skill_with_activity_type.name}; {activity_name}\n"
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


def test_competency_bulk_add_latin1_semicolon(supervisor_client, user1):
    """Test bulk badge import with a latin-1 encoded CSV using semicolons."""

    csv = f"licence;niveau;activité\n{user1.license};;\n"
    file = BytesIO(csv.encode("iso-8859-1"))

    response = supervisor_client.get("/activity_supervision/competency_badge_holders/")
    data = utils.load_data_from_form(response.text, "user-search-form")
    data["activity_id"] = ActivityType.query.filter_by(name="Alpinisme").first().id
    data["csv_file"] = (file, "import.csv")
    data["badge_id"] = str(int(BadgeIds.Practitioner))
    data["level"] = 2

    response = supervisor_client.post(
        "/activity_supervision/competency_badge/add", data=data
    )

    assert response.status_code == 302
    assert len(user1.badges) == 1
    assert user1.badges[0].badge_id == BadgeIds.Practitioner


def test_export_competency_badges(
    supervisor_client, user1, user2, user3, custom_skill, custom_skill_with_expiry
):
    """Tests the export of competency badges filtered by type, activity and level."""
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    for user, badge_id, level, activity_id in (
        (user1, BadgeIds.Skill, custom_skill.level, None),
        (user2, BadgeIds.Skill, custom_skill_with_expiry.level, None),
        (user2, BadgeIds.Practitioner, 2, alpinisme.id),
        (user3, BadgeIds.Practitioner, 3, alpinisme.id),
        (user3, BadgeIds.Practitioner, 2, canyon.id),
    ):
        db.session.add(
            Badge(
                user_id=user.id,
                badge_id=badge_id,
                level=level,
                activity_id=activity_id,
                creation_time=datetime.now(),
            )
        )
    db.session.commit()

    response = supervisor_client.get("/activity_supervision/competency_badge_holders/")
    assert response.status_code == 200
    assert 'id="export-badge_id"' in response.text
    assert 'id="export-level"' in response.text

    def export(badge_id, activity_id, level=""):
        response = supervisor_client.post(
            "/activity_supervision/competency_badge_holders/export",
            data={
                "export-badge_id": int(badge_id),
                "export-activity_id": activity_id,
                "export-level": level,
            },
        )
        assert response.status_code == 200
        worksheet = openpyxl.load_workbook(filename=BytesIO(response.data)).active
        return sorted(
            row[0] for row in worksheet.iter_rows(min_row=2, values_only=True)
        )

    no_activity = ActivityTypeSelectionForm.NO_ACTIVITY
    all_activities = ActivityTypeSelectionForm.ALL_ACTIVITIES

    # Skill badges without activity
    assert export(BadgeIds.Skill, no_activity) == sorted([user1.license, user2.license])
    assert export(BadgeIds.Skill, no_activity, custom_skill.level) == [user1.license]
    assert export(BadgeIds.Skill, all_activities) == sorted(
        [user1.license, user2.license]
    )

    # Practitioner badges; Canyon is not supervised by supervisor_client
    assert export(BadgeIds.Practitioner, alpinisme.id) == sorted(
        [user2.license, user3.license]
    )
    assert export(BadgeIds.Practitioner, alpinisme.id, 3) == [user3.license]
    assert export(BadgeIds.Practitioner, all_activities, 2) == [user2.license]
    assert export(BadgeIds.Practitioner, no_activity) == []


def test_list_skill_without_activity(supervisor_client, user1, custom_skill):
    """Tests that supervisors see skill badges without activity in the badge list."""
    db.session.add(
        Badge(
            user_id=user1.id,
            badge_id=BadgeIds.Skill,
            level=custom_skill.level,
            creation_time=datetime.now(),
        )
    )
    db.session.commit()

    response = supervisor_client.get(
        "/api/badges/",
        query_string={"badge_ids": [int(BadgeIds.Practitioner), int(BadgeIds.Skill)]},
    )
    assert response.status_code == 200
    data = json.loads(response.text)["data"]
    assert len(data) == 1
    assert data[0]["user"]["mail"] == user1.mail
