"""Module for event tag classes.
"""
from flask import current_app

from collectives.models.globals import db


class EventTag(db.Model):
    """Class of an event tag.

    An event tag is related to a single event and is defined by a type.
    """

    __tablename__ = "event_tags"

    id = db.Column(db.Integer, primary_key=True)
    """Event tag unique id.

    ID is used as DB primary key

    :type: int
    """

    type = db.Column(db.Integer, nullable=False)
    """Type of the tag.

    Possible values are keys of config EVENT_TAGS.

    :type: :py:class:`collectives.models.event_tag.EventTagTypes`"""

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    """ Primary key of the event which holds this tag (see  
    :py:class:`collectives.models.event.Event`)

    :type: int"""

    def __init__(self, tag_id):
        """Constructor for EventTag

        :param int tag_id: id of the :py:class:`EventTagTypes` for this tag"""
        self.type = tag_id

    @property
    def name(self):
        """Name of the tag type

        :type: string"""
        return self.full["name"]

    @property
    def short(self):
        """Short name of the tag type, used as css class

        :type: string"""
        return self.full["short"]

    @property
    def csv_code(self):
        """Short name of the tag type, used as css class

        :type: string"""
        if "csv_code" in self.full:
            return self.full["csv_code"]
        return self.full["name"]

    @property
    def full(self):
        """All information about the tag type.

        :type: dict"""
        tag = self.all(True)[self.type]
        tag["id"] = self.type
        return tag

    @classmethod
    def choices(cls):
        """Returns all tag types formatted for a wtform multiple selection field.

        :type: array"""
        return [(tag[0], tag[1]["name"]) for tag in cls.all().items()]

    @classmethod
    def all(cls, include_deprecated=False):
        """Returns tag dictionnary as defined by EVENT_TAGS in config.

        :param include_deprecated: Whether to include deprecated activity types
        :type include_deprecated: bool

        :type: dict"""

        tags = current_app.config["EVENT_TAGS"]
        if include_deprecated:
            return tags

        return {id: tag for id, tag in tags.items() if not tag.get("deprecated", False)}

    @classmethod
    def get_type_from_short(cls, short):
        """

        :param string short: Shortname of the searched tag
        :returns: Tag id
        :rtype: int"""
        for i, tag in cls.all(True).items():
            if tag["short"] == short:
                return i
        return None
