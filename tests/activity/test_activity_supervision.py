"""Module to test activity supervision functions."""


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
