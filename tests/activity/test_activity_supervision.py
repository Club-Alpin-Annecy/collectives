"""Module to test activity supervision functions."""

from collectives.models import db
from collectives.models.activity_type import ActivityKind, ActivityType
from collectives.models.badge import (
    BadgeCustomLevel,
    BadgeCustomLevelScope,
    BadgeIds,
)


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


def test_leader_export(supervisor_client, supervisor_user):
    """Test export of leader of one supervised activity.

    See :py:func:`collectives.routes.activity_supervision.export_role`
    """
    activity = supervisor_user.get_supervised_activities()[0]
    data = {"activity_id": str(activity.id)}
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


def test_add_initiative(admin_client):
    """Test adding a new initiative, listed apart from activities and services"""
    form_data = {
        "kind": ActivityKind.Initiative.value,
        "name": "Refuge du Parmelan",
        "trigram": "RPA",
    }
    response = admin_client.post(
        "/activity_supervision/configuration/add",
        data=form_data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Activité Refuge du Parmelan modifiée avec succès." in response.text

    activity = ActivityType.query.filter_by(trigram="RPA").first()
    assert activity.kind == ActivityKind.Initiative
    assert activity.icon == "benevolat"

    response = admin_client.get("/activity_supervision/configuration")
    initiatives = response.text.split("Initiatives")[1].split("Services")[0]
    assert "Refuge du Parmelan" in initiatives


def test_cannot_add_regular_activity(admin_client):
    """Regular activities are defined in configuration, not created from the UI"""
    form_data = {
        "kind": ActivityKind.Regular.value,
        "name": "Nouveau sport",
        "trigram": "NSP",
    }
    admin_client.post("/activity_supervision/configuration/add", data=form_data)
    assert ActivityType.query.filter_by(trigram="NSP").first() is None


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


def test_custom_skills_supersedes(supervisor_client):
    """Test setting the "supersedes" relation between custom skills"""

    def add_skill(name: str, supersedes: list[int] | None = None, skill_id=None):
        data = {
            "name": name,
            "abbrev": name[:3],
            "activity_id": "",
            "default_validity": "0",
            "supersedes_ids": supersedes or [],
        }
        url = "/activity_supervision/custom_skills"
        if skill_id is not None:
            url = f"/activity_supervision/custom_skill/{skill_id}"
        return supervisor_client.post(url, data=data, follow_redirects=True)

    add_skill("Initiateur")
    initiateur = BadgeCustomLevel.query.filter_by(name="Initiateur").first()
    add_skill("Moniteur", [initiateur.id])
    moniteur = BadgeCustomLevel.query.filter_by(name="Moniteur").first()

    assert moniteur.supersedes == [initiateur]
    assert "Supérieure à : Initiateur" in add_skill("Guide").text

    # Cycles are refused
    response = add_skill("Initiateur", [moniteur.id], skill_id=initiateur.id)
    assert "est déjà supérieure" in response.text
    db.session.refresh(initiateur)
    assert initiateur.supersedes == []

    # The relation can be removed
    add_skill("Moniteur", [], skill_id=moniteur.id)
    db.session.refresh(moniteur)
    assert moniteur.supersedes == []


def test_custom_skills_supersedes_other_activity(supervisor_client):
    """A skill may not supersede a skill specific to another activity"""
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    escalade = ActivityType.query.filter_by(name="Escalade").first()
    other = BadgeCustomLevel(
        badge_id=BadgeIds.Skill,
        level=100,
        name="Initiateur escalade",
        abbrev="IE",
        activity_id=escalade.id,
    )
    db.session.add(other)
    db.session.commit()

    data = {
        "name": "Moniteur alpinisme",
        "abbrev": "MA",
        "scope": BadgeCustomLevelScope.SingleActivity.value,
        "activity_id": alpinisme.id,
        "default_validity": "0",
        "supersedes_ids": [other.id],
    }
    response = supervisor_client.post(
        "/activity_supervision/custom_skills", data=data, follow_redirects=True
    )
    assert "spécifique à une autre activité" in response.text
    assert BadgeCustomLevel.query.filter_by(name="Moniteur alpinisme").first() is None

    # Allowed for a skill not linked to an activity
    data["scope"] = BadgeCustomLevelScope.AllActivities.value
    data["activity_id"] = ""
    data["name"] = "Guide"
    supervisor_client.post(
        "/activity_supervision/custom_skills", data=data, follow_redirects=True
    )
    guide = BadgeCustomLevel.query.filter_by(name="Guide").first()
    assert guide.supersedes == [other]

    # ...but then the guide skill cannot be moved to another activity
    data["scope"] = BadgeCustomLevelScope.SingleActivity.value
    data["activity_id"] = alpinisme.id
    response = supervisor_client.post(
        f"/activity_supervision/custom_skill/{guide.id}",
        data=data,
        follow_redirects=True,
    )
    assert "spécifique à une autre activité" in response.text
    db.session.refresh(guide)
    assert guide.activity_id is None


def test_custom_skill_activity_scope(supervisor_client):
    """Test the three ways of linking a custom skill to activities.

    supervisor_client supervises Alpinisme only."""
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    escalade = ActivityType.query.filter_by(name="Escalade").first()
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    url = "/activity_supervision/custom_skills"

    data = {
        "name": "Secouriste",
        "abbrev": "SEC",
        "default_validity": "0",
        "scope": BadgeCustomLevelScope.SelectedActivities.value,
        "selected_activity_ids": [],
    }

    # A selection needs at least one activity
    response = supervisor_client.post(url, data=data, follow_redirects=True)
    assert "au moins une activité" in response.text
    assert BadgeCustomLevel.query.filter_by(name="Secouriste").first() is None

    # Activities can be selected without supervising them
    data["selected_activity_ids"] = [escalade.id, canyon.id]
    response = supervisor_client.post(url, data=data, follow_redirects=True)
    skill = BadgeCustomLevel.query.filter_by(name="Secouriste").first()
    assert skill.activity_scope == BadgeCustomLevelScope.SelectedActivities
    assert skill.activity_id is None
    assert set(skill.selected_activities) == {escalade, canyon}
    assert skill.activity_name() == "Escalade, Canyon"
    assert "Secouriste</strong> (Escalade, Canyon)" in response.text
    assert not skill.descriptor.concerns_any_activity({alpinisme.id})
    assert skill.descriptor.concerns_any_activity({alpinisme.id, canyon.id})

    # The skill can still be edited, here to a single supervised activity
    edit_url = f"/activity_supervision/custom_skill/{skill.id}"
    assert supervisor_client.get(edit_url).status_code == 200
    data["scope"] = BadgeCustomLevelScope.SingleActivity.value
    response = supervisor_client.post(edit_url, data=data, follow_redirects=True)
    assert "Merci de sélectionner une activité" in response.text

    data["activity_id"] = escalade.id
    response = supervisor_client.post(edit_url, data=data, follow_redirects=True)
    db.session.refresh(skill)
    assert skill.activity_scope == BadgeCustomLevelScope.SelectedActivities

    data["activity_id"] = alpinisme.id
    supervisor_client.post(edit_url, data=data, follow_redirects=True)
    db.session.refresh(skill)
    assert skill.activity_scope == BadgeCustomLevelScope.SingleActivity
    assert skill.activity_id == alpinisme.id
    assert skill.selected_activities == []

    # ... then to all activities: the leftover activity is ignored
    data["scope"] = BadgeCustomLevelScope.AllActivities.value
    supervisor_client.post(edit_url, data=data, follow_redirects=True)
    db.session.refresh(skill)
    assert skill.activity_scope == BadgeCustomLevelScope.AllActivities
    assert skill.activity_id is None
    assert skill.selected_activities == []
