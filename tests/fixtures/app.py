"""Creation of fixture app"""

import os
import tempfile
import logging

import pytest

import collectives
from collectives.utils import init
from collectives.models import db, Configuration

# pylint: disable=redefined-outer-name


@pytest.fixture
def db_file():
    """Generate a file path for a db file, and delete it after use"""
    path = tempfile.mkstemp(suffix="collective")[1]

    yield path

    try:
        os.unlink(path)
    except PermissionError:
        logging.warning("Unable to delete temporary database %s", path)


@pytest.fixture
def app(db_file):
    """Session-wide test `Flask` application."""
    extra_config = {
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "SERVER_NAME": "localhost",
    }
    fixture_app = collectives.create_app(
        "../tests/assets/config.test.py", extra_config=extra_config
    )

    with fixture_app.app_context():
        db.create_all()

        init.populate_db(fixture_app)
        path = "tests/assets/configuration.test.yaml"
        init.init_config(app=fixture_app, force=True, path=path, clean=False)

        yield fixture_app

        db.session.remove()
        db.session.close()


@pytest.fixture
def enable_sanctions():
    """Enable sanctions in configuration"""
    Configuration.get_item("ENABLE_SANCTIONS").content = True
    Configuration.uncache("ENABLE_SANCTIONS")
