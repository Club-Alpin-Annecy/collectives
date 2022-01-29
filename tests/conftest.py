import os
import pytest
import tempfile

from alembic.command import upgrade
from alembic.config import Config

from collectives import create_app
from collectives.utils import init
from collectives.models import db


TESTDB_FD, TESTDB_PATH = tempfile.mkstemp(suffix="collective")
TEST_DATABASE_URI = "sqlite:///{}".format(TESTDB_PATH)


@pytest.fixture(scope="module")
def app():
    """Session-wide test `Flask` application."""
    settings_override = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URI,
        "WTF_CSRF_ENABLED": False,
        "BCRYPT_LOG_ROUNDS": 4,
    }
    app = create_app()
    app.config.update(settings_override)

    with app.app_context():
        db.init_app(app)
        db.create_all()
        init.init_admin(app)

        yield app

        db.session.remove()
        db.session.close()
        os.unlink(TESTDB_PATH)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, mail="admin", password="test"):
        response = self._client.post(
            "/auth/login", data={"mail": "admin", "password": "foobar2"}
        )
        return response.headers["Location"]

    def logout(self):
        response = self._client.get("/auth/logout")
        return response.headers["Location"]


@pytest.fixture
def dbauth(client):
    return AuthActions(client)
