"""Module to check the Loxya integration stays invisible where it is not enabled.

This code base is shared between several clubs, most of which do not use Loxya.
With ``LOXYA_ENABLED`` off — the default — none of it may show: no log line, no
scheduled job, no column, no button, no configuration item, no route. Each test
checks one entry point, off then on.
"""

import logging

import pytest

from collectives.utils import loxya
from collectives.utils.scheduled_tasks import init_scheduler
from tests.mock.loxya import set_loxya_connection

# pylint: disable=unused-argument,redefined-outer-name


@pytest.fixture
def loxya_off(app):
    """A deployment that does not enable Loxya, as every other club."""
    app.config["LOXYA_ENABLED"] = False
    set_loxya_connection()
    return app


@pytest.fixture
def loxya_on(app):
    """A deployment that enables Loxya and has entered its credentials, as Annecy."""
    app.config["LOXYA_ENABLED"] = True
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


def test_no_log_at_startup_when_off(loxya_off, caplog):
    """Not using Loxya is the normal state: nothing to say about it."""
    with caplog.at_level(logging.DEBUG):
        loxya.LoxyaApi().init_app(loxya_off)

    assert not [r for r in caplog.records if "loxya" in r.getMessage().lower()]


def test_missing_credentials_are_pointed_out(app, admin_client):
    """Switched on, credentials not entered yet: technicians are told where."""
    app.config["LOXYA_ENABLED"] = True
    set_loxya_connection(LOXYA_API_PASSWORD="")

    page = admin_client.get("/technician/actions")

    assert "Connexion à Loxya à renseigner" in page.text
    assert "LOXYA_API_PASSWORD" in page.text
    assert "Mode en vigueur : <strong>éteint</strong>" in page.text


def test_no_scheduled_job_when_off(loxya_off):
    """Other clubs get no nightly Loxya job at all."""
    assert "loxya_sync" not in scheduled_jobs(loxya_off)


def test_scheduled_job_when_on(loxya_on):
    """The job is armed once enabled; it reads the live mode at each run."""
    assert "loxya_sync" in scheduled_jobs(loxya_on)


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


def test_configuration_folder_hidden_when_off(loxya_off, admin_client):
    """The Loxya settings do not appear in the configuration pages."""
    index = admin_client.get("/technician/configuration")
    folder = admin_client.get("/technician/configuration/Loxya")

    assert "/technician/configuration/Loxya" not in index.text
    assert "LOXYA_SYNC_ACTIVE" not in folder.text


def test_configuration_folder_shown_when_on(loxya_on, admin_client):
    """Once enabled, technicians find and edit the live switches."""
    index = admin_client.get("/technician/configuration")
    folder = admin_client.get("/technician/configuration/Loxya")

    assert "/technician/configuration/Loxya" in index.text
    for name in (
        "LOXYA_URL",
        "LOXYA_API_USERNAME",
        "LOXYA_API_PASSWORD",
        "LOXYA_SYNC_ACTIVE",
        "LOXYA_AUTO_CREATE",
    ):
        assert name in folder.text


def test_password_is_masked_in_the_configuration(loxya_on, admin_client):
    """Like the extranet and SMTP passwords, the Loxya one is never displayed."""
    folder = admin_client.get("/technician/configuration/Loxya")

    assert "secret" not in folder.text
    assert "*****" in folder.text


def test_hidden_setting_cannot_be_edited_when_off(loxya_off, admin_client):
    """Hidden also means refused, not merely out of sight."""
    response = admin_client.post(
        "/technician/configuration/Loxya",
        data={"name": "LOXYA_SYNC_ACTIVE", "content": "y"},
    )

    assert response.status_code == 403


def test_other_folders_keep_their_order(loxya_on, admin_client, app):
    """Filtering must not reorder the configuration menu of the other clubs."""
    app.config["LOXYA_ENABLED"] = False
    off = admin_client.get("/technician/configuration").text
    app.config["LOXYA_ENABLED"] = True
    on = admin_client.get("/technician/configuration").text

    def folder_links(html):
        return [
            part.split('"')[0]
            for part in html.split('href="/technician/configuration/')[1:]
        ]

    assert folder_links(off) == [f for f in folder_links(on) if f != "Loxya"]


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
