"""Module to describe the type of event.
"""
from flask import escape

from .globals import db


class EventType(db.Model):
    """Class for the type of event.

    An event type can be a group activity, training, collective buying, etc.
    See the EVENT_TYPES config  variable.
    Persistence is done with SQLAlchemy and in the table ``event_types``
    """

    __tablename__ = "event_types"

    id = db.Column(db.Integer, primary_key=True)
    """ Primary key

    :type: int
    """

    name = db.Column(db.String(256), nullable=False)
    """ Event type name.

    :type: string
    """

    short = db.Column(db.String(256), nullable=False)
    """ Event type short name.

    It is especially used for icon CSS classes.

    :type: string
    """

    requires_activity = db.Column(db.Boolean(), nullable=False)
    """ Whether events of this type need to be associated with at least one activity.

    :type: bool
    """

    license_types = db.Column(db.String(64), nullable=True)
    """ Comma-separated list of license types required to register
    to an event of this type.

    For instance, events of type "Collective Jeune" require youth license types

    :type: string
    """

    terms_title = db.Column(db.String(256), nullable=True)
    """ Title of the terms that must be accepted for registering to
    and événement of this type.

    :type: string
    """

    terms_file = db.Column(db.String(256), nullable=True)
    """ Name of the file containings the terms that must be accepted for registering to
    and événement of this type

    :type: string
    """

    def has_valid_license(self, user):
        """Check whether an user has a valic license for this type of event

        :param user: The user whose license should be checked
        :param user: :py:class:`collectives.models.user.User`
        :return: True if no license types are defined or if the user license category is included in those types
        :rtype: bool"""
        if not self.license_types:
            return True
        license_types = self.license_types.split()
        return len(license_types) == 0 or user.license_category in license_types

    @classmethod
    def get_all_types(cls):
        """List all event_types in database

        :return: list of types
        :rtype: list(:py:class:`EventType`)"""
        return cls.query.order_by("id", "name").all()

    @classmethod
    def js_values(cls):
        """Class method to get all event type as js dict

        :return: types as js Dictionnary
        :rtype: String
        """
        types = cls.get_all_types()
        items = [f"{type.id}:'{escape(type.name)}'" for type in types]
        return "{" + ",".join(items) + "}"
