"""Module to describe the type of event.
"""

from typing import Dict, Any
from markupsafe import escape
from flask import current_app
from collectives.models.globals import db
from collectives.models import Configuration
from collectives.utils.misc import to_ascii


class EventType(db.Model):
    """Class for the type of event.

    An event type can be a group activity, training, collective buying, etc.
    See the EVENT_TYPES config  variable.
    Persistence is done with SQLAlchemy and in the table ``event_types``
    """

    TERMS_CONFIGURATIONS = [
        "GUIDE_FILE",
        "GUIDE_TITLE",
        "GUIDE_TRAVEL_FILE",
        "GUIDE_TRAVEL_TITLE",
    ]
    """ List of configuration keys that can be used to format the terms_file
    or terms_title.

    It should never be a secret configuration.  

    :type: list"""

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
    an avent of this type.

    It is recommended to use
    :py:meth:`collectives.models.event.event_type.EventType.get_terms_title()`
    to access it in order to have formatted with hot configuration.

    :type: string
    """

    terms_file = db.Column(db.String(256), nullable=True)
    """ Name of the file containings the terms that must be accepted for registering to
    an event of this type.

    It is recommended to use
    :py:meth:`collectives.models.event.event_type.EventType.get_terms_file()`
    to access it in order to have formatted with hot configuration.

    :type: string
    """

    def has_valid_license(self, user):
        """Check whether an user has a valid license for this type of event

        :param user: The user whose license should be checked
        :param user: :py:class:`collectives.models.user.User`
        :return: True if no license types are defined or if the user license category is included
                 in those types
        :rtype: bool"""
        if not self.license_types:
            return True
        license_types = self.license_types.split(",")
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

    def get_terms_file(self) -> str:
        """Returns :py:attr:`collectives.models.event.event_type.EventType.terms_file`

        It will format the output using hot configuration as defined in
        :py:attr:`collectives.models.event.event_type.EventType.TERMS_CONFIGURATIONS`
        """
        if self.terms_file is None:
            return None

        confs = {key: Configuration[key] for key in self.TERMS_CONFIGURATIONS}
        return self.terms_file.format(**confs)

    def get_terms_title(self) -> str:
        """Returns :py:attr:`collectives.models.event.event_type.EventType.terms_title`.

        It will format the output using hot configuration as defined in
        :py:attr:`collectives.models.event.event_type.EventType.TERMS_CONFIGURATIONS`
        """
        if self.terms_title is None:
            return None

        confs = {key: Configuration[key] for key in self.TERMS_CONFIGURATIONS}
        return self.terms_title.format(**confs)

    @classmethod
    def all(cls, include_deprecated=False) -> Dict[int, Dict[str, Any]]:
        """Returns type dictionnary as defined by EVENT_TYPES in config.

        :param include_deprecated: Whether to include deprecated activity types
        :type include_deprecated: bool

        :type: dict"""

        types = current_app.config["EVENT_TYPES"]
        if include_deprecated:
            return types

        return {
            id: event_type
            for id, event_type in types.items()
            if not event_type.get("deprecated", False)
        }

    @classmethod
    def get_type_from_csv_code(cls, csv_code: str) -> int:
        """
        :param string short: CSV code of the searched type
        :returns: Type id
        """

        # Match without accents, lowercase
        csv_code = to_ascii(csv_code.strip().lower())
        for i, event_type in cls.all(include_deprecated=True).items():
            event_type_csv_code = to_ascii(
                event_type.get("csv_code", event_type["name"])
            ).lower()
            if csv_code == event_type_csv_code:
                return i

        return None
