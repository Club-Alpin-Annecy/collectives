"""Unit tests for EventTag class"""

from collectives.models import EventTag, db
from collectives.models.event_tag import UNKNOWN_TAG_SHORT


def test_unknown_tag_type(app, event1):
    """An event holding a tag absent from EVENT_TAGS must still be displayable"""
    unknown_type = max(app.config["EVENT_TAGS"].keys()) + 1
    event1.tag_refs.append(EventTag(unknown_type))
    db.session.commit()

    tag = event1.tags[-1]
    assert tag["id"] == unknown_type
    assert tag["short"] == UNKNOWN_TAG_SHORT
    assert str(unknown_type) in tag["name"]


def test_full_does_not_mutate_config(app):
    """Getting a tag description must not alter the EVENT_TAGS configuration"""
    tag_type = next(iter(app.config["EVENT_TAGS"]))
    assert EventTag(tag_type).full["id"] == tag_type
    assert "id" not in app.config["EVENT_TAGS"][tag_type]
