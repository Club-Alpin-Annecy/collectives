""" Module to create flask client from existing fixture users.

Connection to the application does not use http but a special client available
from the app object. See flask
`documentation
<https://flask.palletsprojects.com/en/2.2.x/testing/#sending-requests-with-the-test-client>`_.

This client is used to test GET and POST requests. Base client fixture is
:meth:`client`

For some requests, login is required. Thus, some basic fixtures are offered regarding
the client role that will be tested. EG: :meth:`admin_client` or :meth:`user1_client`.
Those client are based on :meth:`client`.

.. warning::
    Please note that Flask app offer ONLY ONE CLIENT. Thus, if you need to switch between
    roles in the same test, please use only one client fixture and change user using
    :meth:`login`
"""

from datetime import datetime
import pytest
from tests.fixtures import user

# pylint: disable=redefined-outer-name


def login(client, user, password=user.PASSWORD, deactivate_spam_protection=True):
    """Log the client with given user.

    If client has already a connected user, the user will be silently logout.

    :param client: The test client from the flask app.
    :param User user: the user that will be login
    :param string password: The password to use to login user. Default:
        see :attr:`tests.fixtures.user.PASSWORD`
    :param bool deactivate_spam_protection: allow to do as much connexion as wanted
    :returns: True if login is succesfull, False if not.
    """
    if client.user:
        logout(client)
    response = client.post(
        "/auth/login", data={"mail": user.mail, "password": password}
    )

    if deactivate_spam_protection:
        user.last_failed_login = datetime(2000, 1, 1)

    if response.status_code != 302 or response.location != "/":
        return False

    client.user = user
    return True


def logout(client):
    """Logs out a client

    :param client: The flask app test_client.
    :returns: True if logout is succesfull
    :rtype: bool"""
    response = client.get("/auth/logout")
    if response.status_code != 302:
        return False
    client.user = None
    return True


@pytest.fixture
def client(app):
    """Raw and unauthenticated flask client."""
    client = app.test_client()
    client.user = None
    return client


@pytest.fixture
def admin_client(client, admin_user, app):
    """Flask client authenticated as admin."""
    login(client, admin_user, app.config["ADMINPWD"])
    yield client
    logout(client)


@pytest.fixture
def supervisor_client(client, supervisor_user):
    """Flask client authenticated as Alpinisme activity supervisor."""
    login(client, supervisor_user)
    yield client
    logout(client)


@pytest.fixture
def hotline_client(client, hotline_user):
    """Flask client authenticated as hotline."""
    login(client, hotline_user)
    yield client
    logout(client)


@pytest.fixture
def user1_client(client, user1):
    """Flask client authenticated as regular user."""
    login(client, user1)
    yield client
    logout(client)


@pytest.fixture
def user3_client(client, user3):
    """Flask client authenticated as regular user."""
    login(client, user3)
    yield client
    logout(client)


@pytest.fixture
def leader_client(client, leader_user):
    """Flask client authenticated as regular user."""
    login(client, leader_user)
    yield client
    logout(client)


@pytest.fixture
def youth_client(client, youth_user):
    """Flask client authenticated as youth user."""
    login(client, youth_user)
    yield client
    logout(client)


@pytest.fixture
def client_with_valid_benevole_badge(client, user_with_valid_benevole_badge):
    """Flask client authenticated as user with a valid badge."""
    login(client, user_with_valid_benevole_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_expired_benevole_badge(client, user_with_expired_benevole_badge):
    """Flask client authenticated as user with an expired badge."""
    login(client, user_with_expired_benevole_badge)
    yield client
    logout(client)


# User Clients related to late unregistrations
@pytest.fixture
def client_with_valid_first_warning_badge(client, user_with_valid_first_warning_badge):
    """Flask client authenticated as user with a valid first warning badge."""
    login(client, user_with_valid_first_warning_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_expired_first_warning_badge(
    client, user_with_expired_first_warning_badge
):
    """Flask client authenticated as user with an expired first warning badge."""
    login(client, user_with_expired_first_warning_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_valid_second_warning_badge(
    client, user_with_valid_second_warning_badge
):
    """Flask client authenticated as user with a valid second warning badge."""
    login(client, user_with_valid_second_warning_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_expired_second_warning_badge(
    client, user_with_expired_second_warning_badge
):
    """Flask client authenticated as user with an expired second warning badge."""
    login(client, user_with_expired_second_warning_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_valid_banned_badge(client, user_with_valid_banned_badge):
    """Flask client authenticated as user with a valid banned badge."""
    login(client, user_with_valid_banned_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_expired_banned_badge(client, user_with_expired_banned_badge):
    """Flask client authenticated as user with an expired banned badge."""
    login(client, user_with_expired_banned_badge)
    yield client
    logout(client)


@pytest.fixture
def client_with_no_warning_badge(client, user_with_no_warning_badge):
    """Flask client authenticated as user with no late unregistration-related warning badge."""
    login(client, user_with_no_warning_badge)
    yield client
    logout(client)
