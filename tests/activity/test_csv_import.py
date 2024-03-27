""" Module to test the CSV import functions. """

from datetime import datetime
from io import BytesIO

from collectives.models import Event

# pylint: disable=unused-argument


def test_csv_import_form(supervisor_client):
    """Test display of CSV import form.

    See :py:func:`collectives.routes.activity_supervision.csv_import`
    """
    response = supervisor_client.get("/activity_supervision/import")
    assert response.status_code == 200


def test_csv_import(supervisor_client, user1):
    """Test upload of a valid csv file."""
    csv = (
        "nom_encadrant,id_encadrant,debut,fin,titre,secteur,"
        "carte_IGN,altitude,denivele,cotation,distance,observations,"
        "places,places_internet,debut_internet,fin_internet,places_liste_attente,parent,tag\n"
        "Jan Johnston,990000000001,26/11/2021 7:00,26/11/2021 7:00,Aiguille des Calvaires,"
        "Aravis,d,2322,1200,F,120,d ,8,4,19/11/2021 7:00,25/11/2021 12:00,3,,\n"
        "Jan Johnston,990000000001,26/11/2021 7:00,26/11/2021 7:00,Mont Sulens,Aravis,"
        "d,2322,1200,F,120,d ,8,4,19/11/2021 7:00,25/11/2021 12:00,3,,cycle decouverte,,"
    )
    file = BytesIO(csv.encode("utf8"))
    activity = supervisor_client.user.get_supervised_activities()[0]

    data = {
        "csv_file": (file, "import.csv"),
        "description": "{altitude}m-{denivele}m-{cotation}",
        "type": activity.id,
    }

    response = supervisor_client.post("/activity_supervision/import", data=data)
    assert response.status_code == 200

    events = Event.query.all()

    assert len(events) == 2
    event = events[0]

    assert event.title == "Aiguille des Calvaires"
    assert event.num_slots == 8
    assert event.num_online_slots == 4
    assert event.num_waiting_list == 3
    assert event.registration_open_time == datetime(2021, 11, 19, 7, 0, 0)
    assert event.registration_close_time == datetime(2021, 11, 25, 12, 0, 0)
    assert "2322m-1200m-F" in event.rendered_description
    assert event.leaders[0].license == "990000000001"
    assert event.leaders[0] == user1

    assert len(events[1].tag_refs) == 1
    assert events[1].tag_refs[0].short == "tag_decouverte"


def test_csv_import_unknown_leader(supervisor_client, user1):
    """Test upload of an invalid csv with an unkown leader."""
    csv = (
        ",,,,,,,,,,,,,,,,\n"
        "Evan Walsh,990000000002,26/11/2021 7:00,26/11/2021 7:00,Aiguille des Calvaires,"
        "Aravis,d,2322,1200,F,120,d ,8,4,19/11/2021 7:00,25/11/2021 12:00,,\n"
    )
    file = BytesIO(csv.encode("utf8"))
    activity = supervisor_client.user.get_supervised_activities()[0]

    data = {
        "csv_file": (file, "import.csv"),
        "description": "{altitude}m-{denivele}m-{cotation}",
        "type": activity.id,
    }

    response = supervisor_client.post("/activity_supervision/import", data=data)
    assert response.status_code == 200

    assert (
        "[Exception] L&#39;encadrant Evan Walsh (numéro de licence 990000000002)"
        " n&#39;a pas encore créé de compte" in response.text
    )

    events = Event.query.all()
    assert len(events) == 0
