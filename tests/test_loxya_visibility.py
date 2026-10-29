"""Module to check the Loxya integration stays invisible where it is not enabled.

This code base is shared between several clubs, most of which do not use Loxya.
With ``LOXYA_ENABLED`` off — the default — nothing of it may show outside its
configuration folder: no log line, no column, no button, no route. Since the
switch is hot, the nightly job is armed everywhere, but does nothing while it is
off. Each test checks one entry point, off then on.
"""

import logging

import pytest

from collectives.utils.loxya_sync import sync_all_users
from collectives.utils.scheduled_tasks import init_scheduler
from tests.mock.loxya import set_loxya_connection, set_loxya_enabled, set_loxya_mode

# pylint: disable=unused-argument,redefined-outer-name


@pytest.fixture
def loxya_off(app):
    """A deployment that does not enable Loxya, as every other club."""
    set_loxya_enabled(False)
    set_loxya_connection()
    return app


@pytest.fixture
def loxya_on(app):
    """A deployment that enables Loxya and has entered its credentials, as Annecy."""
    set_loxya_enabled()
    set_loxya_connection()
    return app


def looks_unknown(client, response) -> bool:
    """Checks a response is the one the site gives for a URL that does not exist.

    The site answers an unknown URL with a redirection to the home page and a
    "Page inconnue" message, rather than a bare 404.
    """
    reference = client.post("/this/route/does/not/exist")
    return (
        response.status_code == reference.status_code
        and response.location == reference.location
    )


def scheduled_jobs(app) -> list:
    """Starts the real scheduler, lists its jobs, and stops it."""
    app.config.update(TESTING=False, SCHEDULER_ENABLED=True)
    scheduler = init_scheduler(app)
    try:
        return [job.id for job in scheduler.get_jobs()]
    finally:
        scheduler.shutdown(wait=False)
        app.config["TESTING"] = True


# -- Startup -------------------------------------------------------------------


def test_missing_credentials_are_pointed_out(app, admin_client):
    """Switched on, credentials not entered yet: technicians are told where."""
    set_loxya_enabled()
    set_loxya_connection(LOXYA_API_PASSWORD="")

    page = admin_client.get("/technician/actions")

    assert "Connexion à Loxya à renseigner" in page.text
    assert "LOXYA_API_PASSWORD" in page.text
    assert "Mode en vigueur : <strong>éteint</strong>" in page.text


def test_scheduled_job_is_armed(app):
    """The switch being hot, the job is armed everywhere and reads it at each run."""
    assert "loxya_sync" in scheduled_jobs(app)


def test_nightly_run_does_nothing_when_off(loxya_off, caplog):
    """Off, the nightly run does nothing and logs nothing, even with the
    synchronization itself left active."""
    set_loxya_mode(active=True, auto_create=True)

    with caplog.at_level(logging.DEBUG, logger=loxya_off.logger.name):
        report = sync_all_users()

    assert not report
    assert not caplog.records


# -- Administration --------------------------------------------------------------


def test_admin_list_has_no_loxya_when_off(loxya_off, admin_client):
    """No column, no button, and no field in the JSON feeding the list."""
    page = admin_client.get("/administration/")
    data = admin_client.get("/api/users/?page=1&size=50").json["data"]

    assert "window.loxyaEnabled = false" in page.text
    assert not [key for row in data for key in row if key.startswith("loxya")]


def test_admin_list_shows_loxya_when_on(loxya_on, admin_client):
    """Once enabled, the list gets its Loxya column and fields."""
    page = admin_client.get("/administration/")
    data = admin_client.get("/api/users/?page=1&size=50").json["data"]

    assert "window.loxyaEnabled = true" in page.text
    assert "loxya_active" in data[0]


def test_sync_route_looks_unknown_when_off(loxya_off, admin_client):
    """The route does not exist, as far as other clubs can tell."""
    response = admin_client.post("/administration/user/1/loxya/sync")

    assert looks_unknown(admin_client, response)


# -- Technician pages ------------------------------------------------------------


def test_switch_is_in_the_configuration_when_off(loxya_off, admin_client):
    """The switch is how a club turns Loxya on: it is listed even when off."""
    folder = admin_client.get("/technician/configuration/Loxya")

    assert "LOXYA_ENABLED" in folder.text


def test_actions_page_has_no_loxya_when_off(loxya_off, admin_client):
    """The maintenance actions page shows nothing about Loxya."""
    page = admin_client.get("/technician/actions")
    response = admin_client.post("/technician/actions/loxya_sync")

    assert "Loxya" not in page.text
    assert looks_unknown(admin_client, response)


def test_actions_page_shows_the_simulation_when_on(loxya_on, admin_client):
    """Once enabled, technicians see the mode and what a run would do."""
    page = admin_client.get("/technician/actions")

    assert "Synchronisation des comptes avec Loxya" in page.text
    assert "éteint" in page.text
