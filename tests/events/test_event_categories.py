"""Tests for the 2026-2027 event types and tags, and their deprecated predecessors."""

# pylint: disable=unused-argument

from bs4 import BeautifulSoup

from collectives.models import EventTag, EventType, db
from tests import utils

COURS_TAG = 14
"""Tag "Cours", excluded from retex by default."""


def _options(html: str, select_name: str) -> dict:
    """:returns: the options of a select of the event form, as {value: label}"""
    soup = BeautifulSoup(html, features="lxml")
    select = soup.select_one(f'#form_edit_event select[name="{select_name}"]')
    return {option["value"]: option.text for option in select.find_all("option")}


def test_deprecated_types_are_synced(app):
    """Deprecated event types stay in base, flagged, and new ones are created"""
    youth = EventType.query.filter_by(short="jeune").one()
    assert youth.deprecated
    assert not EventType.query.filter_by(short="collective").one().deprecated
    assert EventType.query.filter_by(short="soiree_manifestation").one()

    active = EventType.get_all_types()
    assert youth not in active
    assert youth in EventType.get_all_types(include_deprecated=True)


def test_new_event_offers_active_types_only(leader_client):
    """A new event cannot use a deprecated type or tag"""
    response = leader_client.get("/collectives/add")
    assert response.status_code == 200

    types = _options(response.text, "event_type_id").values()
    assert "Soirée & manifestation" in types
    assert "Jeunes" not in types

    tags = _options(response.text, "tag_list").values()
    assert "Cours" in tags
    assert "Handicaf" not in tags


def test_edit_event_keeps_deprecated_type(leader_client, youth_event):
    """An event of a deprecated type can still be edited without changing its type"""
    response = leader_client.get(f"/collectives/{youth_event.id}/edit")
    assert response.status_code == 200
    assert "Jeunes" in _options(response.text, "event_type_id").values()

    data = utils.load_data_from_form(response.text, "form_edit_event")
    data["description"] = "Nouvelle description"
    response = leader_client.post(
        f"/collectives/{youth_event.id}/edit", data=data, follow_redirects=True
    )
    assert response.status_code == 200
    assert f"collectives/{youth_event.id}-" in response.request.path

    db.session.refresh(youth_event)
    assert youth_event.event_type.short == "jeune"
    assert youth_event.description == "Nouvelle description"


def test_edit_event_keeps_deprecated_tag(leader_client, tagged_event):
    """A deprecated tag remains on the events which hold it"""
    response = leader_client.get(f"/collectives/{tagged_event.id}/edit")
    assert "Handicaf" in _options(response.text, "tag_list").values()

    data = utils.load_data_from_form(response.text, "form_edit_event")
    response = leader_client.post(
        f"/collectives/{tagged_event.id}/edit", data=data, follow_redirects=True
    )
    assert f"collectives/{tagged_event.id}-" in response.request.path

    db.session.refresh(tagged_event)
    assert [tag.name for tag in tagged_event.tag_refs] == ["Handicaf"]


def test_tag_choices(app):
    """Deprecated tags are only offered when kept explicitly"""
    assert (6, "Handicaf") not in EventTag.choices()
    assert (6, "Handicaf") in EventTag.choices([6])
    assert (14, "Cours") in EventTag.choices()


def test_tag_csv_codes(app):
    """CSV imports accept the tag name and its former name"""
    assert EventTag.get_type_from_csv_code("CPM") == 2
    assert (
        EventTag.get_type_from_csv_code(
            "connaissance et protection du milieu montagnard"
        )
        == 2
    )
    assert EventTag.get_type_from_csv_code("Entrainement regulier") == 16
    assert EventTag.get_type_from_csv_code("Rando Cool") == 10


def test_retex_excluded_for_courses(leader_client, past_event):
    """Courses, open access sessions and trainings do not get a retex"""
    assert past_event.is_retex_applicable()
    assert past_event.needs_retex()
    assert leader_client.user.pending_retex_count() == 1

    past_event.tag_refs.append(EventTag(COURS_TAG))
    db.session.commit()

    assert not past_event.is_retex_applicable()
    assert not past_event.needs_retex()
    assert leader_client.user.pending_retex_count() == 0

    response = leader_client.get(f"/retex/event/{past_event.id}/edit")
    assert response.status_code == 302

    response = leader_client.get("/api/retex/mine")
    assert response.status_code == 200
    assert response.json["data"] == []
