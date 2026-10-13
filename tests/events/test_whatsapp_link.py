"""Tests of the WhatsApp group invite link of an event"""

from datetime import datetime

import pytest

from collectives.forms import EventForm
from collectives.models import Registration, RegistrationLevels, RegistrationStatus, db

# pylint: disable=unused-argument

LINK = "https://chat.whatsapp.com/AbCdEf123456"


def _register(event, user, status):
    """Registers ``user`` to ``event`` with the given status"""
    event.registrations.append(
        Registration(
            user_id=user.id,
            status=status,
            level=RegistrationLevels.Normal,
            is_self=True,
        )
    )
    db.session.add(event)
    db.session.commit()


def _set_link(event):
    """Sets the WhatsApp invite link of ``event``"""
    event.whatsapp_invite_link = LINK
    db.session.add(event)
    db.session.commit()


def test_leader_sets_and_removes_link(leader_client, event):
    """A leader saves a valid link, then removes it"""
    response = leader_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200
    page = response.text
    assert "Groupe WhatsApp" in page
    assert event.whatsapp_group_name() in page

    response = leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": f"  {LINK} ", "submit": "1"},
    )
    assert response.status_code == 302
    assert event.whatsapp_invite_link == LINK

    response = leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": LINK, "remove": "1"},
    )
    assert response.status_code == 302
    assert event.whatsapp_invite_link is None


@pytest.mark.parametrize(
    "link",
    [
        "https://example.com/AbCdEf123456",
        "http://chat.whatsapp.com/AbCdEf123456",
        "https://chat.whatsapp.com.evil.example/AbCdEf123456",
        "https://chat.whatsapp.com/AbC def",
        "https://chat.whatsapp.com/" + "a" * 201,
        "javascript:alert(1)",
    ],
)
def test_invalid_link_is_rejected(leader_client, event, link):
    """Only WhatsApp invite links are accepted"""
    response = leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": link, "submit": "1"},
    )
    assert response.status_code == 302
    assert event.whatsapp_invite_link is None


@pytest.mark.parametrize(
    "link",
    [
        f"{LINK}?mode=ems_copy_t",
        f"{LINK}/",
        "https://chat.whatsapp.com/invite/AbCdEf123456",
    ],
)
def test_link_is_normalized(leader_client, event, link):
    """Links copied from WhatsApp are stored in their canonical form"""
    leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": link, "submit": "1"},
    )
    assert event.whatsapp_invite_link == LINK


def test_model_rejects_invalid_link(event):
    """The model refuses any value which is not a WhatsApp invite link"""
    with pytest.raises(ValueError):
        event.whatsapp_invite_link = "javascript:alert(1)"
    event.whatsapp_invite_link = ""
    assert event.whatsapp_invite_link is None


def test_event_form_does_not_expose_link():
    """The event edition form cannot write the link, bypassing its own form"""
    assert hasattr(EventForm, "title")
    assert not hasattr(EventForm, "whatsapp_invite_link")


def test_remove_ignores_invalid_field(leader_client, event):
    """Removing the link works whatever is typed in the field"""
    _set_link(event)
    response = leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": "not a link", "remove": "1"},
    )
    assert response.status_code == 302
    assert event.whatsapp_invite_link is None


def test_saving_empty_field_without_link(leader_client, event):
    """Saving an empty field when there is no link does not claim a removal"""
    response = leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": "", "submit": "1"},
        follow_redirects=True,
    )
    assert "Aucun lien de groupe WhatsApp à enregistrer." in response.text
    assert "a été retiré" not in response.text
    assert event.whatsapp_invite_link is None


def test_non_leader_cannot_set_link(user1_client, event):
    """A user without edit rights cannot set the link"""
    _register(event, user1_client.user, RegistrationStatus.Active)
    response = user1_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": LINK, "submit": "1"},
    )
    assert response.status_code == 302
    assert event.whatsapp_invite_link is None


@pytest.mark.parametrize(
    "status,visible",
    [
        (RegistrationStatus.Active, True),
        (RegistrationStatus.Present, True),
        (RegistrationStatus.Waiting, False),
        (RegistrationStatus.PaymentPending, False),
        (RegistrationStatus.Rejected, False),
        (RegistrationStatus.SelfUnregistered, False),
        (RegistrationStatus.JustifiedAbsentee, False),
        (RegistrationStatus.UnJustifiedAbsentee, False),
    ],
)
def test_link_visibility_by_status(user1_client, event, status, visible):
    """Only participants with a valid registration see the link"""
    _set_link(event)
    _register(event, user1_client.user, status)

    assert event.can_see_whatsapp_link(user1_client.user) == visible
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert (LINK in response.text) == visible
    assert ("Rejoindre le groupe" in response.text) == visible


def test_link_hidden_from_non_registered(user1_client, event):
    """A user who is not registered does not see the link"""
    _set_link(event)
    assert not event.can_see_whatsapp_link(user1_client.user)
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert LINK not in response.text


def test_leader_sees_link(leader_client, event):
    """The leader sees the link in the set-up block"""
    _set_link(event)
    response = leader_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert LINK in response.text
    assert "Retirer le lien" in response.text


def test_disabled_feature(disable_whatsapp_groups, leader_client, user1, event):
    """When the feature is disabled, nothing is displayed nor accepted"""
    _set_link(event)
    _register(event, user1, RegistrationStatus.Active)

    response = leader_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert "Groupe WhatsApp" not in response.text
    assert LINK not in response.text

    response = leader_client.post(
        f"/collectives/{event.id}/whatsapp_link",
        data={"whatsapp_invite_link": "", "remove": "1"},
    )
    assert response.status_code == 302
    assert event.whatsapp_invite_link == LINK


def test_link_not_in_api(user1_client, event):
    """The link is never exposed by the events API"""
    _set_link(event)
    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    assert LINK not in response.text


def test_whatsapp_group_name(event):
    """The group name is made of the title and short date, truncated if needed"""
    event.title = "Dent du Cruet"
    event.start = datetime(2026, 10, 17, 8, 0)
    assert event.whatsapp_group_name() == "Dent du Cruet - sam. 17 oct."

    event.title = "Traversée " * 20
    name = event.whatsapp_group_name()
    assert len(name) == 100
    assert name.endswith("… - sam. 17 oct.")


def test_whatsapp_group_description(event):
    """The group description is the event URL followed by its plain text description"""
    url = "https://example.org/collectives/1"
    event.description = (
        "# Programme\n\n**Départ** à 7h\nRetour à _18h_\n\n- crampons\n- piolet"
    )
    event.set_rendered_description(event.description)
    assert event.whatsapp_group_description(url) == (
        f"{url}\n\nProgramme\n\nDépart à 7h\nRetour à 18h\n\ncrampons\npiolet"
    )

    event.description = ""
    event.set_rendered_description(event.description)
    assert event.whatsapp_group_description(url) == url

    event.description = "x" * 3000
    event.set_rendered_description(event.description)
    description = event.whatsapp_group_description(url)
    assert len(description) == 2048
    assert description.startswith(url)
    assert description.endswith("…")


def test_leader_page_shows_description(leader_client, event):
    """The set-up block offers the event description to copy"""
    response = leader_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert "Lorem ipsum" in response.text
    assert f"/collectives/{event.id}" in response.text
