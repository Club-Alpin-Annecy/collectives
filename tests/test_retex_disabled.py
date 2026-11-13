"""Module to test the retex (Ptirex) module when the feature is disabled."""

# pylint: disable=unused-argument

from collectives.models import Retex, RetexStatus, db


def test_disabled_feature(disable_retex, leader_client, past_event):
    """When the feature is disabled, nothing is displayed nor accepted"""
    db.session.add(
        Retex(
            event_id=past_event.id,
            author_id=leader_client.user.id,
            status=RetexStatus.GoodPractice,
            description="Retex masqué",
            rendered_description="Retex masqué",
        )
    )
    db.session.commit()

    response = leader_client.get(f"/collectives/{past_event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert "Retex masqué" not in response.text
    assert "/retex/" not in response.text

    response = leader_client.get(f"/retex/event/{past_event.id}/edit")
    assert response.status_code == 302

    response = leader_client.get("/retex/mine")
    assert response.status_code == 302

    response = leader_client.get("/api/retex/mine")
    assert response.status_code == 403
