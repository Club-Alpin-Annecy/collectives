"""Module to test activity supervision functions."""

from collectives.models import db
from collectives.models.activity_type import ActivityKind, ActivityType
from collectives.models.badge import BadgeCustomLevel


def test_index(supervisor_client):
    """Test regular acces to activity index.

    See :py:func:`collectives.routes.activity_supervision.activity_supervision`
    """
    response = supervisor_client.get("/activity_supervision/index")
    assert response.status_code == 200


def test_wrong_user(user1_client):
    """Test regular acces to activity index.

    See :py:func:`collectives.routes.activity_supervision.activity_supervision`
    """
    response = user1_client.get("/activity_supervision/index")
    assert response.status_code == 302


def test_leader_list(supervisor_client):
    """Test regular acces to activity leader list

    See :py:func:`collectives.routes.activity_supervision.leader_list`
    """
    response = supervisor_client.get("/activity_supervision/leader")
    assert response.status_code == 200


def test_leader_export(supervisor_client):
    """Test export of leader of one activity.

    See :py:func:`collectives.routes.activity_supervision.export_role`
    """
    data = {"activity_id": "1"}
    response = supervisor_client.post("/activity_supervision/roles/export/", data=data)
    assert response.status_code == 200


def test_activity_doc(supervisor_client):
    """Test regular acces to document upload page.

    See :py:func:`collectives.routes.activity_supervision.activity_documents`
    """
    response = supervisor_client.get("/activity_supervision/activity_documents")
    assert response.status_code == 200


def test_add_service(admin_client):
    """Test adding a new service"""

    # Fetch the route to create a new activity
    response = admin_client.get("/activity_supervision/configuration/add")
    assert response.status_code == 200

    # Parse the form from the response
    form_data = {
        "name": "Test Service",
        "trigram": "TS",
        "is_deprecated": False,
    }

    # Submit the form with our values
    response = admin_client.post(
        "/activity_supervision/configuration/add",
        data=form_data,
        follow_redirects=True,
    )
    assert response.status_code == 200

    # Check the result
    assert "Activité Test Service modifiée avec succès." in response.text

    activity = ActivityType.query.filter_by(name="Test Service").first()
    assert activity is not None
    assert activity.trigram == "TS"
    assert activity.kind == ActivityKind.Service
    assert activity.short == "test-service"

    # Submit the form once again
    response = admin_client.post(
        "/activity_supervision/configuration/add",
        data=form_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Activité Test Service modifiée avec succès." not in response.text
    assert "Ce trigramme est déjà utilisé" in response.text

    # Change trigram and submit again
    form_data = {
        "name": "Test Service",
        "trigram": "TS2",
        "is_deprecated": False,
    }
    response = admin_client.post(
        "/activity_supervision/configuration/add",
        data=form_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Activité Test Service modifiée avec succès." in response.text

    activity = ActivityType.query.filter_by(trigram="TS2").first()
    assert activity is not None
    assert activity.short == f"test-service-{activity.id}"


def test_manage_custom_skills(supervisor_client):
    """Test access to custom skill management page"""
    response = supervisor_client.get("/activity_supervision/custom_skills")
    assert response.status_code == 200
    assert "Spécialisations" in response.text

    response = supervisor_client.get("/activity_supervision/custom_skill/999999")
    assert response.status_code == 302  # Redirect due to non-existing skill
    assert response.location.endswith("/activity_supervision/custom_skills")

    # Test adding a new custom skill level
    data = {
        "name": "Test Skill",
        "abbrev": "TS",
        "activity_id": "",  # No activity
        "default_validity": "0",
    }
    response = supervisor_client.post(
        "/activity_supervision/custom_skills", data=data, follow_redirects=True
    )
    assert response.status_code == 200
    assert "Spécialisations" in response.text

    skill = BadgeCustomLevel.query.filter_by(name="Test Skill").first()
    assert skill is not None
    assert skill.abbrev == "TS"
    assert skill.activity_id is None
    assert skill.default_validity == 0

    # Test editing the custom skill level
    edit_url = f"/activity_supervision/custom_skill/{skill.id}"
    data["name"] = "Updated Test Skill"
    data["abbrev"] = "UTS"
    data["default_validity"] = "12"
    response = supervisor_client.post(edit_url, data=data, follow_redirects=True)
    assert response.status_code == 200
    assert "Spécialisations" in response.text

    updated_skill = db.session.get(BadgeCustomLevel, skill.id)
    assert updated_skill.name == "Updated Test Skill"
    assert updated_skill.abbrev == "UTS"
    assert updated_skill.default_validity == 12
