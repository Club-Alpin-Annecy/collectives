"""" Testing administration """

from collectives.models import User


def test_index(admin_client):
    """Test display of administration index page."""
    response = admin_client.get("/administration/")
    assert response.status_code == 200


def test_user_access(user1_client):
    """Test access refusal to a non admin user."""
    response = user1_client.get("/administration/")
    assert response.status_code == 302


def test_add_user(admin_client):
    """Test display of the user add form."""
    response = admin_client.get("/administration/users/add")
    assert response.status_code == 200


def test_modify_user(admin_client, admin_user):
    """Test display of a user modification form."""
    response = admin_client.get(f"/administration/users/{admin_user.id}")
    assert response.status_code == 200


def test_add_user_role(admin_client, admin_user):
    """Test display of a user role modification form."""
    response = admin_client.get(f"/administration/user/{admin_user.id}/roles")
    assert response.status_code == 200


# TODO: add badges route test
def test_add_user_badge(admin_client, admin_user):
    """Test display of a user badge modification form."""
    response = admin_client.get(f"/administration/user/{admin_user.id}/badges")
    assert response.status_code == 200


def test_export_roles(admin_client):
    """Test exports of user roles"""
    response = admin_client.get("/administration/roles/export/")
    assert response.status_code == 302

    response = admin_client.get("/administration/roles/export/tnone")
    assert response.status_code == 200

    response = admin_client.get("/administration/roles/export/t5-r10")
    assert response.status_code == 200


def test_admin_create_valideuser(admin_client):
    """Test  creation a new user."""
    response = admin_client.post(
        "/administration/users/add",
        data={
            "mail": "user1@mail.domain",
            "password": "foobar1+",
            "confirm": "foobar1+",
            "first_name": "user",
            "last_name": "LastName",
            "license": "987987981234",
            "phone": "0123456789",
        },
    )
    assert response.headers["Location"].endswith("/administration/")
    users = User.query.all()
    assert users[1].mail == "user1@mail.domain"
