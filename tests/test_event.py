from datetime import datetime
import pytest
from bs4 import BeautifulSoup
from collectives.models import Event, ActivityType, EventType, db
from collectives.utils import init


@pytest.fixture()
def event_types(app):
    if EventType.query.count() == 0:
        init.event_types(app)
    return EventType.query.all()


@pytest.fixture()
def activity_types(app):
    if ActivityType.query.count() == 0:
        init.activity_types(app)
    return ActivityType.query.all()


@pytest.fixture()
def event(activity_types, event_types):

    event = Event()
    event.title = "New collective"
    event.start = datetime(2022, 10, 20, 0, 0, 0)
    event.end = datetime(2022, 10, 20, 0, 0, 0)
    event.description = """**Lorem ipsum** dolor sit amet, consectetur 
    adipiscing elit. Quisque mollis vitae diam at hendrerit. 
    _Aenean cursus sem vitae condimentum imperdiet._ Sed nec ligula lectus. 
    Vivamus vehicula varius turpis, eget accumsan libero. Integer eleifend 
    aliquet leo, in malesuada risus tempus id. Suspendisse pharetra iaculis 
    nunc vitae sollicitudin. Donec eu accumsan ipsum. Pellentesque 
    habitant morbi tristique senectus et netus et malesuada fames ac 
    turpis egestas. Morbi ut urna eget eros pellentesque molestie. Donec 
    auctor sapien id erat congue, vel molestie sapien varius. Fusce vitae 
    iaculis tellus, nec mollis turpis."""
    event.set_rendered_description(event.description)

    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    event.activity_types.append(alpinisme)

    type = EventType.query.filter_by(name="Collective").first()
    event.event_type = type

    db.session.add(event)
    db.session.commit()

    return event


def test_event_access(dbauth, client, event):
    """Test regular acces to event description"""
    dbauth.login(client)
    response = client.get(f"/collectives/{event.id}")
    assert response.status_code == 302
    assert response.headers["Location"] == "/collectives/1-new-collective"

    response = client.get(response.headers["Location"])
    assert response.status_code == 200


def test_unauthenticated(dbauth, client, event):
    """Test acces to event description by an unauthenticated client"""
    dbauth.logout()
    response = client.get(f"/collectives/{event.id}")
    assert response.status_code == 302
    print(response.headers["Location"])
    assert (
        response.headers["Location"] == f"/auth/login?next=%2Fcollectives%2F{event.id}"
    )


def test_crawler(dbauth, client, event):
    """Test acces to event description by an unauthenticated crawler"""
    headers = {
        "User-Agent": "facebookexternalhit/1.0 (+http://www.facebook.com/externalhit_uatext.php)"
    }

    dbauth.logout()
    response = client.get(f"/collectives/{event.id}", headers=headers)
    assert response.status_code == 302
    print(response.headers["Location"])
    assert response.headers["Location"] == f"/collectives/{event.id}/preview"

    response_preview = client.get(response.headers["Location"], headers=headers)
    assert response_preview.status_code == 200
    soup = BeautifulSoup(response_preview.text, features="lxml")
    assert (
        soup.select_one('meta[property="og:title"]')["content"]
        == "Collectives: New collective"
    )
    assert (
        soup.select_one('meta[property="og:url"]')["content"]
        == f"/collectives/{event.id}-new-collective"
    )
    assert (
        soup.select_one('meta[property="og:image"]')["content"]
        == "http://localhost/static/caf/logo-caf-annecy.svg"
    )

    description = soup.select_one('meta[property="og:description"]')["content"]

    assert (
        description
        == "Collective Alpinisme - jeudi 20 octobre 2022 - 10 places - Par - Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque mollis vitae diam at hendrerit...."
    )

    # Test an event with a photo
    event.photo = "test.jpg"
    response = client.get(response.headers["Location"], headers=headers)
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, features="lxml")
    assert (
        soup.select_one('meta[property="og:image"]')["content"]
        == "http://localhost/static/test.jpg"
    )
