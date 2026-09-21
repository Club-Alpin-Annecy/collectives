"""Tests that supervisors can only export roles of their own activities (audit M6)."""

from collectives.models import ActivityType


def test_export_role_refuses_unsupervised_activity(supervisor_client, supervisor_user):
    """Exporting roles of an activity the user does not supervise is refused."""
    supervised = {a.id for a in supervisor_user.get_supervised_activities()}
    other = next(a for a in ActivityType.get_all_types() if a.id not in supervised)

    response = supervisor_client.post(
        "/activity_supervision/roles/export/", data={"activity_id": other.id}
    )
    assert response.status_code == 400


def test_export_role_accepts_supervised_activity(supervisor_client, supervisor_user):
    """Exporting roles of a supervised activity works."""
    activity = supervisor_user.get_supervised_activities()[0]
    response = supervisor_client.post(
        "/activity_supervision/roles/export/", data={"activity_id": activity.id}
    )
    assert response.status_code == 200
