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
    assert user1.badges[0].grantor == supervisor_client.user
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


def _add_badge(user, badge_id, level=None, activity_name=None) -> Badge:
    """Adds a badge to a user, optionally associated with an activity."""
    badge = Badge(
        user_id=user.id,
        badge_id=badge_id,
        level=level,
        creation_time=datetime.now(),
        expiration_date=date(2020, 1, 1),
    )
    if activity_name:
        badge.activity_id = ActivityType.query.filter_by(name=activity_name).first().id
    db.session.add(badge)
    db.session.commit()
    return badge


def test_supervisor_badge_scope(supervisor_client, user1, user2, user3, custom_skill):
    """Tests which badges a supervisor may list, export, renew and delete.

    supervisor_client supervises Alpinisme only."""
    skill = _add_badge(user1, BadgeIds.Skill, custom_skill.level)
    supervised = _add_badge(user2, BadgeIds.Practitioner, 2, "Alpinisme")
    other_activity = _add_badge(user3, BadgeIds.Practitioner, 2, "Canyon")
    suspension = _add_badge(user3, BadgeIds.Suspended)
    expired = skill.expiration_date
    managed_ids = {skill.id, supervised.id}
    unmanaged_ids = {other_activity.id, suspension.id}

    # Listing, even when not restricting badge types
    response = supervisor_client.get("/api/badges/")
    assert response.status_code == 200
    data = json.loads(response.text)["data"]
    assert {row["user"]["mail"] for row in data} == {user1.mail, user2.mail}

    # Export of all activities includes the skill badge without activity
    response = supervisor_client.post(
        "/activity_supervision/competency_badge_holders/export",
        data={"export-activity_id": ActivityTypeSelectionForm.ALL_ACTIVITIES},
    )
    assert response.status_code == 200
    worksheet = openpyxl.load_workbook(filename=BytesIO(response.data)).active
    licenses = {row[0] for row in worksheet.iter_rows(min_row=2, values_only=True)}
    assert licenses == {user1.license, user2.license}

    # Renewal
    for badge_id in managed_ids | unmanaged_ids:
        response = supervisor_client.post(
            f"/activity_supervision/competency_badge_holders/renew/{badge_id}"
        )
        assert response.status_code == 302
    for badge_id in managed_ids:
        assert db.session.get(Badge, badge_id).expiration_date != expired
    for badge_id in unmanaged_ids:
        assert db.session.get(Badge, badge_id).expiration_date == expired

    # Deletion
    for badge_id in managed_ids | unmanaged_ids:
        response = supervisor_client.post(
            f"/activity_supervision/competency_badge_holders/delete/{badge_id}"
        )
        assert response.status_code == 302
    for badge_id in managed_ids:
        assert db.session.get(Badge, badge_id) is None
    for badge_id in unmanaged_ids:
        assert db.session.get(Badge, badge_id) is not None


def test_hotline_badge_scope(hotline_client, user1, user2, custom_skill):
    """Tests that hotline users manage every badge, with or without activity."""
    _add_badge(user1, BadgeIds.Skill, custom_skill.level)
    suspension = _add_badge(user2, BadgeIds.Suspended)

    response = hotline_client.get("/api/badges/")
    data = json.loads(response.text)["data"]
    assert {row["user"]["mail"] for row in data} == {user1.mail, user2.mail}

    response = hotline_client.post(
        "/administration/badges/export/",
        data={"export-activity_id": ActivityTypeSelectionForm.ALL_ACTIVITIES},
    )
    assert response.status_code == 200
    worksheet = openpyxl.load_workbook(filename=BytesIO(response.data)).active
    assert worksheet.max_row == 3

    response = hotline_client.post(f"/administration/badges/delete/{suspension.id}")
    assert response.status_code == 302
    assert db.session.get(Badge, suspension.id) is None


def test_export_badge_type_and_level(
    supervisor_client, user1, user2, user3, custom_skill
):
    """Tests exporting competency badges of a given type and level."""
    _add_badge(user1, BadgeIds.Skill, custom_skill.level)
    _add_badge(user2, BadgeIds.Practitioner, 2, "Alpinisme")
    _add_badge(user3, BadgeIds.Practitioner, 3, "Alpinisme")

    def export(badge_id, level=""):
        response = supervisor_client.post(
            "/activity_supervision/competency_badge_holders/export",
            data={
                "export-badge_id": int(badge_id),
                "export-activity_id": ActivityTypeSelectionForm.ALL_ACTIVITIES,
                "export-level": level,
            },
        )
        assert response.status_code == 200
        worksheet = openpyxl.load_workbook(filename=BytesIO(response.data)).active
        return {row[0] for row in worksheet.iter_rows(min_row=2, values_only=True)}

    assert export(BadgeIds.Skill) == {user1.license}
    assert export(BadgeIds.Practitioner) == {user2.license, user3.license}
    assert export(BadgeIds.Practitioner, 3) == {user3.license}
