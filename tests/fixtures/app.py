""" Creation of fixture app"""

import os
import tempfile
import logging

import pytest

import collectives
from collectives.utils import init
from collectives.models import db

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
    fixture_app = collectives.create_app("../tests/assets/config.test.py")
    fixture_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"

    with fixture_app.app_context():
        db.init_app(fixture_app)
        db.create_all()

        init.populate_db(fixture_app)
        init.init_config(True, "tests/assets/configuration.test.yaml")

        yield fixture_app

        db.session.remove()
        db.session.close()
